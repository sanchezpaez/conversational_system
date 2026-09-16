import pytest

from app.entity_parser import extract_entities_locally
from app.llm import LLMClient


@pytest.mark.parametrize(
    "message,expected_order_id,expected_date",
    [
        ("Where is my order AB-123?", "AB-123", None),
        ("AB-123", "AB-123", None),
        ("Move order 7821 to 2026/04/02", "7821", "2026-04-02"),
        ("Please update order ZX-9 to April 2, 2026", "ZX-9", "2026-04-02"),
        ("No explicit entities here", None, None),
    ],
)
def test_extract_entities_locally(message, expected_order_id, expected_date):
    entities = extract_entities_locally(message)

    assert entities.order_id == expected_order_id
    assert entities.date == expected_date


def test_extract_entities_uses_local_values_without_llm_when_complete():
    client = object.__new__(LLMClient)

    def fail_if_called(_: list[dict]) -> dict:
        raise AssertionError("LLM should not be called when local extraction is complete")

    client._chat_json = fail_if_called

    entities = client.extract_entities("Move order 7821 to 2026/04/02")

    assert entities.order_id == "7821"
    assert entities.date == "2026-04-02"


def test_extract_entities_merges_local_and_llm_values():
    client = object.__new__(LLMClient)
    client._chat_json = lambda _: {"order_id": None, "date": "2026-04-03"}

    entities = client.extract_entities("Please check order AB-123")

    assert entities.order_id == "AB-123"
    assert entities.date == "2026-04-03"
