import pytest

from app.dialogue_policy import build_clarification_reply, build_error_reply, get_missing_fields
from app.models import EntityExtraction


@pytest.mark.parametrize(
    "intent,entities,expected_missing",
    [
        ("order_status", EntityExtraction(order_id="AB-123", date=None), []),
        ("order_status", EntityExtraction(order_id=None, date=None), ["order_id"]),
        ("order_status", EntityExtraction(order_id="", date=None), ["order_id"]),
        ("change_booking", EntityExtraction(order_id="AB-123", date="2026-05-01"), []),
        ("change_booking", EntityExtraction(order_id=None, date="2026-05-01"), ["order_id"]),
        ("change_booking", EntityExtraction(order_id="AB-123", date=None), ["date"]),
        ("change_booking", EntityExtraction(order_id=None, date=None), ["order_id", "date"]),
        ("change_booking", EntityExtraction(order_id="", date="2026-05-01"), ["order_id"]),
        ("change_booking", EntityExtraction(order_id="AB-123", date=""), ["date"]),
        ("fallback", EntityExtraction(order_id=None, date=None), []),
        ("fallback", EntityExtraction(order_id="AB-123", date="2026-05-01"), []),
        ("order_status", EntityExtraction(order_id="7821", date="2026-05-01"), []),
        ("order_status", EntityExtraction(order_id=None, date="2026-05-01"), ["order_id"]),
        ("change_booking", EntityExtraction(order_id="7821", date="2026-04-12"), []),
        ("change_booking", EntityExtraction(order_id="7821", date=None), ["date"]),
        ("change_booking", EntityExtraction(order_id=None, date="2026-04-12"), ["order_id"]),
        ("order_status", EntityExtraction(order_id="XYZ-999", date=None), []),
        ("order_status", EntityExtraction(order_id="   ", date=None), []),
        ("change_booking", EntityExtraction(order_id="XYZ-999", date="2026-09-30"), []),
        ("change_booking", EntityExtraction(order_id="XYZ-999", date="invalid"), []),
        ("fallback", EntityExtraction(order_id="", date=""), []),
        ("fallback", EntityExtraction(order_id="   ", date="   "), []),
        ("order_status", EntityExtraction(order_id="A", date=None), []),
        ("change_booking", EntityExtraction(order_id="A", date="2026-01-01"), []),
        ("change_booking", EntityExtraction(order_id=None, date=""), ["order_id", "date"]),
    ],
)
def test_get_missing_fields_contract(intent, entities, expected_missing):
    assert get_missing_fields(intent, entities) == expected_missing


@pytest.mark.parametrize(
    "intent,missing_fields,expected_substring",
    [
        ("order_status", ["order_id"], "order ID"),
        ("change_booking", ["order_id"], "order ID"),
        ("change_booking", ["date"], "YYYY-MM-DD"),
        ("change_booking", ["order_id", "date"], "order ID and the new date"),
        ("fallback", [], "enough information"),
    ],
)
def test_build_clarification_reply(intent, missing_fields, expected_substring):
    reply = build_clarification_reply(intent, missing_fields)
    assert expected_substring in reply


@pytest.mark.parametrize(
    "code,expected_substring",
    [
        ("missing_order_id", "order ID"),
        ("fallback", "specialist"),
        ("unknown_code", "went wrong"),
        ("", "went wrong"),
    ],
)
def test_build_error_reply(code, expected_substring):
    reply = build_error_reply(code)
    assert expected_substring in reply
