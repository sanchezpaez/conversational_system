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
    "intent,missing_fields,language,expected_substring",
    [
        ("order_status", ["order_id"], "en", "order ID"),
        ("change_booking", ["order_id"], "en", "order ID"),
        ("change_booking", ["date"], "en", "YYYY-MM-DD"),
        ("change_booking", ["order_id", "date"], "en", "order ID and the new date"),
        ("fallback", [], "en", "enough information"),
        ("order_status", ["order_id"], "es", "ID de tu pedido"),
        ("change_booking", ["date"], "es", "YYYY-MM-DD"),
        ("change_booking", ["order_id", "date"], "es", "ID de tu pedido y la nueva fecha"),
        ("fallback", [], "es", "suficiente información"),
    ],
)
def test_build_clarification_reply(intent, missing_fields, language, expected_substring):
    reply = build_clarification_reply(intent, missing_fields, language)
    assert expected_substring in reply


@pytest.mark.parametrize(
    "code,language,expected_substring",
    [
        ("missing_order_id", "en", "order ID"),
        ("date_in_past", "en", "future date"),
        ("fallback", "en", "specialist"),
        ("unknown_code", "en", "went wrong"),
        ("", "en", "went wrong"),
        ("missing_order_id", "es", "ID de pedido"),
        ("date_in_past", "es", "fecha futura"),
        ("fallback", "es", "especialista"),
        ("unknown_code", "es", "salió mal"),
    ],
)
def test_build_error_reply(code, language, expected_substring):
    reply = build_error_reply(code, language)
    assert expected_substring in reply
