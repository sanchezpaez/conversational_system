from scripts.evaluate import EVAL_CASES, evaluate


def test_all_labelled_cases_pass():
    """All labelled evaluation cases must pass with the mock LLM.

    This acts as a regression gate: any change to agent logic that
    breaks a labelled case will fail this test.
    """
    results = evaluate(verbose=False)

    failures = [r for r in results if not r.passed]
    failure_messages = [
        f"{r.case.label}: {r.failure_reason}" for r in failures
    ]
    assert not failures, "Evaluation failures:\n" + "\n".join(failure_messages)


def test_evaluation_covers_all_intents():
    """Labelled cases must cover all supported intents."""
    intents_covered = {case.expected_intent for case in EVAL_CASES}
    assert "order_status" in intents_covered
    assert "change_booking" in intents_covered
    assert "fallback" in intents_covered


def test_evaluation_covers_clarification_and_success_paths():
    """Labelled cases must include both ok=True and ok=False outcomes."""
    outcomes = {case.expected_ok for case in EVAL_CASES}
    assert True in outcomes
    assert False in outcomes
