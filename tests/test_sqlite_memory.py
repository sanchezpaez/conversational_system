from app.conversation_memory import ConversationState
from app.sqlite_memory import SQLiteConversationMemory


def test_sqlite_memory_persists_state_between_instances(tmp_path):
    """Critical guarantee: state is persisted on disk, not tied to one Python object."""
    db_path = tmp_path / "sessions.db"

    store_one = SQLiteConversationMemory(db_path=str(db_path))
    store_one.upsert(
        "s1",
        ConversationState(
            last_intent="change_booking",
            order_id="7821",
            booking_date="2026-06-01",
            pending_fields=["date"],
            language="es",
            total_turns=3,
            clarification_turns=1,
            successful_turns=1,
            first_success_turn=2,
        ),
    )

    store_two = SQLiteConversationMemory(db_path=str(db_path))
    state = store_two.get("s1")

    assert state.last_intent == "change_booking"
    assert state.order_id == "7821"
    assert state.booking_date == "2026-06-01"
    assert state.pending_fields == ["date"]
    assert state.language == "es"
    assert state.total_turns == 3
    assert state.clarification_turns == 1
    assert state.successful_turns == 1
    assert state.first_success_turn == 2


def test_sqlite_memory_clear_pending(tmp_path):
    """Critical guarantee: pending clarification can be reset without losing session state."""
    db_path = tmp_path / "sessions.db"
    store = SQLiteConversationMemory(db_path=str(db_path))

    store.upsert(
        "s2",
        ConversationState(
            last_intent="order_status",
            order_id="AB-123",
            pending_fields=["order_id"],
        ),
    )

    store.clear_pending("s2")
    state = store.get("s2")

    assert state.pending_fields == []


def test_sqlite_memory_isolates_sessions(tmp_path):
    """Critical guarantee: one session_id must never leak state into another."""
    db_path = tmp_path / "sessions.db"
    store = SQLiteConversationMemory(db_path=str(db_path))

    store.upsert(
        "a",
        ConversationState(
            last_intent="order_status",
            order_id="1111",
            language="en",
        ),
    )
    store.upsert(
        "b",
        ConversationState(
            last_intent="order_status",
            order_id="2222",
            language="es",
        ),
    )

    state_a = store.get("a")
    state_b = store.get("b")

    assert state_a.order_id == "1111"
    assert state_a.language == "en"
    assert state_b.order_id == "2222"
    assert state_b.language == "es"
