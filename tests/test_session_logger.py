import json
from pathlib import Path

from app.session_logger import (
    close_session,
    create_session,
    generate_session_id,
    mark_resolution_check,
    mark_satisfaction,
    record_turn,
)


def test_session_logger_records_turns_and_closes_session(tmp_path):
    session_id = "session_001"
    session_path = tmp_path / f"{session_id}.json"

    create_session(
        session_id=session_id,
        scenario="help_then_status",
        language="es",
        base_dir=str(tmp_path),
    )

    record_turn(
        session_id=session_id,
        user_message="Necesito saber el estado de mi pedido",
        detected_intent="help",
        entities={"order_id": None, "date": None},
        pending_fields=["order_id"],
        clarification_requested=True,
        backend_code="need_clarification",
        ok=False,
        bot_reply="¿Cuál es el identificador del pedido?",
        base_dir=str(tmp_path),
    )

    record_turn(
        session_id=session_id,
        user_message="AB-123",
        detected_intent="help",
        entities={"order_id": "AB-123", "booking_date": None},
        pending_fields=[],
        clarification_requested=False,
        backend_code="order_status",
        ok=True,
        bot_reply="Buenas noticias: encontré el pedido AB-123.",
        base_dir=str(tmp_path),
    )

    mark_resolution_check(
        session_id=session_id,
        base_dir=str(tmp_path),
    )
    mark_satisfaction(
        session_id=session_id,
        user_answer="sí",
        satisfied=True,
        base_dir=str(tmp_path),
    )
    close_session(
        session_id=session_id,
        base_dir=str(tmp_path),
    )

    payload = json.loads(Path(session_path).read_text())
    assert payload["session_id"] == session_id
    assert payload["status"] == "closed"
    assert len(payload["turns"]) == 2
    assert payload["turns"][0]["timestamp"]
    assert payload["turns"][0]["pending_fields"] == ["order_id"]
    assert payload["turns"][1]["entities"]["booking_date"] is None
    assert payload["events"][-1]["event"] == "session_closed"


def test_generate_session_id_uses_numbers_then_letters(tmp_path, monkeypatch):
    class FixedDatetime:
        @classmethod
        def now(cls, timezone):
            from datetime import datetime

            return datetime(2026, 9, 14, tzinfo=timezone)

    monkeypatch.setattr("app.session_logger.datetime", FixedDatetime)
    for number in range(1, 100):
        (tmp_path / f"140926{number}.json").touch()

    assert generate_session_id(str(tmp_path)) == "14092699a"
