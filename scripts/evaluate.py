"""Evaluation runner for the support agent.

This module is intentionally self-contained for quick evaluation runs.
The local functions named ``classify_intent`` and ``extract_entities`` are
mock behavior used only in deterministic mode; they are not production logic.

Two modes:
    - Deterministic (default): runs labelled test cases with a mock LLM,
        no API key needed. Used in CI and tests.
    - Real API: add ``--real`` to run against the live OpenAI API.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from unittest.mock import MagicMock

sys.path.insert(0, __file__.rsplit("/scripts", 1)[0])

from app.agent import SupportAgent
from app.models import EntityExtraction, IntentDecision


@dataclass
class EvalCase:
    """One labelled test case for the agent evaluator."""

    # Human-readable label for reporting
    label: str
    # Message sent to the agent
    message: str
    # Expected intent classification
    expected_intent: str
    # Whether the backend call should succeed (True) or ask for clarification (False)
    expected_ok: bool
    # Optional: backend result code to check (e.g. "order_status", "need_clarification")
    expected_code: str | None = None


def _future_iso_date(days_ahead: int) -> str:
    return (date.today() + timedelta(days=days_ahead)).isoformat()


# Labelled cases covering the main intent/entity combinations
EVAL_CASES: list[EvalCase] = [
    EvalCase(
        label="order_status with explicit order ID",
        message="Where is my order AB-123?",
        expected_intent="order_status",
        expected_ok=True,
        expected_code="order_status",
    ),
    EvalCase(
        label="change_booking with full entities",
        message=f"Can you move booking for order 7821 to {_future_iso_date(20)}?",
        expected_intent="change_booking",
        expected_ok=True,
        expected_code="booking_changed",
    ),
    EvalCase(
        label="fallback intent",
        message="I have a complaint about your website experience.",
        expected_intent="fallback",
        expected_ok=True,
        expected_code="fallback",
    ),
    EvalCase(
        label="order_status missing order ID triggers clarification",
        message="Where is my order?",
        expected_intent="order_status",
        expected_ok=False,
        expected_code="need_clarification",
    ),
    EvalCase(
        label="change_booking missing date triggers clarification",
        message="Please change booking for order 7821.",
        expected_intent="change_booking",
        expected_ok=False,
        expected_code="need_clarification",
    ),
    EvalCase(
        label="change_booking past date rejected",
        message="Move order 7821 to 2000-01-01.",
        expected_intent="change_booking",
        expected_ok=False,
        expected_code="date_in_past",
    ),
]


def _build_eval_mock_llm_client() -> MagicMock:
    """Build a rule-based mock LLM client that covers all EVAL_CASES deterministically."""
    import re

    client = MagicMock()

    def _mock_classify_intent(message: str) -> IntentDecision:
        msg = message.lower()
        if "where is" in msg or ("where" in msg and "order" in msg):
            return IntentDecision(intent="order_status")
        if "move" in msg or "change" in msg or "booking" in msg:
            return IntentDecision(intent="change_booking")
        return IntentDecision(intent="fallback")

    def _mock_extract_entities(message: str) -> EntityExtraction:
        order_id = None
        date = None
        order_match = re.search(r"order\s+([\w-]+)", message, re.IGNORECASE)
        if order_match:
            order_id = order_match.group(1)
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", message)
        if date_match:
            date = date_match.group(0)
        return EntityExtraction(order_id=order_id, date=date)

    client.classify_intent = _mock_classify_intent
    client.extract_entities = _mock_extract_entities
    return client


@dataclass
class EvalResult:
    case: EvalCase
    passed: bool
    actual_intent: str
    actual_ok: bool
    actual_code: str | None
    failure_reason: str | None = None


def evaluate(cases: list[EvalCase] | None = None, verbose: bool = True) -> list[EvalResult]:
    """Run all labelled cases against the agent with a mock LLM.

    Returns a list of EvalResult, one per case.
    """
    cases = cases or EVAL_CASES
    agent = SupportAgent(llm_client=_build_eval_mock_llm_client())
    results: list[EvalResult] = []

    for case in cases:
        result = agent.process(case.message)
        actual_code = result.backend_result.get("code")
        actual_ok = result.backend_result.get("ok", False)

        failures: list[str] = []
        if result.intent != case.expected_intent:
            failures.append(f"intent: got {result.intent!r}, expected {case.expected_intent!r}")
        if actual_ok != case.expected_ok:
            failures.append(f"ok: got {actual_ok}, expected {case.expected_ok}")
        if case.expected_code and actual_code != case.expected_code:
            failures.append(f"code: got {actual_code!r}, expected {case.expected_code!r}")

        passed = len(failures) == 0
        eval_result = EvalResult(
            case=case,
            passed=passed,
            actual_intent=result.intent,
            actual_ok=actual_ok,
            actual_code=actual_code,
            failure_reason="; ".join(failures) if failures else None,
        )
        results.append(eval_result)

        if verbose:
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {case.label}")
            if not passed:
                print(f"       reason: {eval_result.failure_reason}")

    passed_count = sum(1 for r in results if r.passed)
    if verbose:
        print(f"\nResult: {passed_count}/{len(results)} passed ({100 * passed_count // len(results)}%)")

    return results


def run_real_api() -> None:
    """Run evaluation against the live OpenAI API. Requires OPENAI_API_KEY in .env."""
    from app.config import load_environment
    from app.llm import LLMClient

    load_environment()
    agent = SupportAgent(llm_client=LLMClient())

    for case in EVAL_CASES:
        result = agent.process(case.message)
        print("\nQUERY:", case.message)
        print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    if "--real" in sys.argv:
        run_real_api()
    else:
        evaluate()
