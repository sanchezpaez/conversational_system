import json
import sqlite3
from pathlib import Path

from app.conversation_memory import ConversationState


class SQLiteConversationMemory:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_parent_dir()
        self._init_db()

    def _ensure_parent_dir(self) -> None:
        path = Path(self.db_path)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_state (
                    session_id TEXT PRIMARY KEY,
                    last_intent TEXT,
                    order_id TEXT,
                    booking_date TEXT,
                    pending_json TEXT NOT NULL,
                    language TEXT,
                    total_turns INTEGER NOT NULL,
                    clarification_turns INTEGER NOT NULL,
                    successful_turns INTEGER NOT NULL,
                    first_success_turn INTEGER,
                    updated_at TEXT
                )
                """
            )

    def get(self, session_id: str) -> ConversationState:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    last_intent,
                    order_id,
                    booking_date,
                    pending_json,
                    language,
                    total_turns,
                    clarification_turns,
                    successful_turns,
                    first_success_turn,
                    updated_at
                FROM conversation_state
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

        if not row:
            return ConversationState()

        pending = json.loads(row[3])

        return ConversationState(
            last_intent=row[0],
            order_id=row[1],
            booking_date=row[2],
            pending_fields=pending,
            language=row[4],
            total_turns=row[5],
            clarification_turns=row[6],
            successful_turns=row[7],
            first_success_turn=row[8],
            updated_at=row[9],
        )

    def upsert(self, session_id: str, state: ConversationState) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_state (
                    session_id,
                    last_intent,
                    order_id,
                    booking_date,
                    pending_json,
                    language,
                    total_turns,
                    clarification_turns,
                    successful_turns,
                    first_success_turn,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    last_intent = excluded.last_intent,
                    order_id = excluded.order_id,
                    booking_date = excluded.booking_date,
                    pending_json = excluded.pending_json,
                    language = excluded.language,
                    total_turns = excluded.total_turns,
                    clarification_turns = excluded.clarification_turns,
                    successful_turns = excluded.successful_turns,
                    first_success_turn = excluded.first_success_turn,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    state.last_intent,
                    state.order_id,
                    state.booking_date,
                    json.dumps(state.pending_fields),
                    state.language,
                    state.total_turns,
                    state.clarification_turns,
                    state.successful_turns,
                    state.first_success_turn,
                    state.updated_at,
                ),
            )

    def clear_pending(self, session_id: str) -> None:
        state = self.get(session_id)
        state.pending_fields = []
        self.upsert(session_id, state)
