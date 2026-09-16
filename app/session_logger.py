import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = str(PROJECT_ROOT / "data" / "sessions")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_session_id(base_dir: str | None = None) -> str:
    root = Path(base_dir) if base_dir else Path(SESSION_DIR)
    root = root if root.is_absolute() else (PROJECT_ROOT / root)
    root.mkdir(parents=True, exist_ok=True)
    date_prefix = datetime.now(timezone.utc).strftime("%d%m%y")
    existing_ids = {path.stem for path in root.glob(f"{date_prefix}*.json")}

    for number in range(1, 100):
        session_id = f"{date_prefix}{number}"
        if session_id not in existing_ids:
            return session_id

    suffix_index = 0
    while True:
        suffix = chr(ord("a") + suffix_index)
        session_id = f"{date_prefix}99{suffix}"
        if session_id not in existing_ids:
            return session_id
        suffix_index += 1


def _session_path(session_id: str, base_dir: str | None = None) -> Path:
    candidate = Path(base_dir) if base_dir else Path(SESSION_DIR)
    root = candidate if candidate.is_absolute() else (PROJECT_ROOT / candidate)
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{session_id}.json"


def create_session(
    session_id: str,
    scenario: str,
    language: str,
    base_dir: str | None = None,
) -> dict[str, Any]:
    session = {
        "session_id": session_id,
        "scenario": scenario,
        "status": "open",
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "language": language,
        "turns": [],
        "events": [],
        "metrics": {
            "total_turns": 0,
            "clarification_turns": 0,
            "successful_turns": 0,
            "first_success_turn": None,
        },
    }
    path = _session_path(session_id, base_dir)
    if path.exists():
        return json.loads(path.read_text())
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2))
    return session


def _load_session(session_id: str, base_dir: str | None = None) -> dict[str, Any]:
    path = _session_path(session_id, base_dir)
    if not path.exists():
        raise FileNotFoundError(f"Session {session_id} not found at {path}")
    return json.loads(path.read_text())


def _save_session(session: dict[str, Any], session_id: str, base_dir: str | None = None) -> None:
    path = _session_path(session_id, base_dir)
    session["updated_at"] = _utc_now()
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2))


def record_turn(
    session_id: str,
    user_message: str,
    detected_intent: str,
    entities: dict[str, str | None],
    pending_fields: list[str] | None = None,
    clarification_requested: bool = False,
    backend_code: str | None = None,
    ok: bool = False,
    bot_reply: str = "",
    base_dir: str | None = None,
    *,
    missing_fields: list[str] | None = None,
) -> dict[str, Any]:
    resolved_pending_fields = pending_fields or missing_fields or []
    normalized_entities = dict(entities)

    if "date" in normalized_entities and "booking_date" not in normalized_entities:
        normalized_entities["booking_date"] = normalized_entities.pop("date")

    session = _load_session(session_id, base_dir)
    turn_number = len(session["turns"]) + 1
    timestamp = _utc_now()

    turn = {
        "turn": turn_number,
        "timestamp": timestamp,
        "user_message": user_message,
        "detected_intent": detected_intent,
        "entities": normalized_entities,
        "pending_fields": resolved_pending_fields,
        "clarification_requested": clarification_requested,
        "backend_code": backend_code,
        "ok": ok,
        "bot_reply": bot_reply,
    }
    session["turns"].append(turn)

    session["metrics"]["total_turns"] = turn_number
    if clarification_requested:
        session["metrics"]["clarification_turns"] = session["metrics"].get("clarification_turns", 0) + 1
    if ok and backend_code not in {"need_clarification", "fallback"}:
        session["metrics"]["successful_turns"] = session["metrics"].get("successful_turns", 0) + 1
        if session["metrics"]["first_success_turn"] is None:
            session["metrics"]["first_success_turn"] = turn_number

    session["events"].append({
        "event": "turn_recorded",
        "timestamp": timestamp,
        "turn": turn_number,
        "intent": detected_intent,
        "backend_code": backend_code,
        "ok": ok,
        "pending_fields": resolved_pending_fields,
    })

    _save_session(session, session_id, base_dir)
    return session


def mark_resolution_check(session_id: str, base_dir: str | None = None) -> dict[str, Any]:
    session = _load_session(session_id, base_dir)
    timestamp = _utc_now()
    session["events"].append({
        "event": "resolution_check",
        "timestamp": timestamp,
        "prompt": "¿Te ha resuelto esto?",
    })
    _save_session(session, session_id, base_dir)
    return session


def mark_satisfaction(session_id: str, user_answer: str, satisfied: bool, base_dir: str | None = None) -> dict[str, Any]:
    session = _load_session(session_id, base_dir)
    timestamp = _utc_now()
    session["events"].append({
        "event": "satisfaction_check",
        "timestamp": timestamp,
        "user_answer": user_answer,
        "satisfied": satisfied,
    })
    session["satisfied"] = satisfied
    if satisfied:
        session["status"] = "closed"
    else:
        session["status"] = "open_follow_up"
    _save_session(session, session_id, base_dir)
    return session


def close_session(session_id: str, base_dir: str | None = None) -> dict[str, Any]:
    session = _load_session(session_id, base_dir)
    timestamp = _utc_now()
    session["status"] = "closed"
    session["closed_at"] = timestamp
    session["events"].append({
        "event": "session_closed",
        "timestamp": timestamp,
    })
    _save_session(session, session_id, base_dir)
    return session
