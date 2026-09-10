from dataclasses import dataclass, field
from typing import Protocol

from app.models import IntentName, LanguageCode


@dataclass
class ConversationState:
    last_intent: IntentName | None = None
    order_id: str | None = None
    booking_date: str | None = None
    pending_fields: list[str] = field(default_factory=list)
    language: LanguageCode | None = None
    total_turns: int = 0
    clarification_turns: int = 0
    successful_turns: int = 0
    first_success_turn: int | None = None
    updated_at: str | None = None

    def __init__(
        self,
        last_intent: IntentName | None = None,
        order_id: str | None = None,
        booking_date: str | None = None,
        pending_fields: list[str] | None = None,
        language: LanguageCode | None = None,
        total_turns: int = 0,
        clarification_turns: int = 0,
        successful_turns: int = 0,
        first_success_turn: int | None = None,
        updated_at: str | None = None,
    ) -> None:
        self.last_intent = last_intent
        self.order_id = order_id
        self.booking_date = booking_date
        self.pending_fields = pending_fields or []
        self.language = language
        self.total_turns = total_turns
        self.clarification_turns = clarification_turns
        self.successful_turns = successful_turns
        self.first_success_turn = first_success_turn
        self.updated_at = updated_at


class ConversationMemoryStore(Protocol):
    # Contract-only API shared by memory backends (in-memory, SQLite, future PostgreSQL).
    # Ellipsis marks declarations; concrete implementations provide the behavior.
    def get(self, session_id: str) -> ConversationState:
        ...

    def upsert(self, session_id: str, state: ConversationState) -> None:
        ...

    def clear_pending(self, session_id: str) -> None:
        ...


class InMemoryConversationMemory:
    def __init__(self) -> None:
        self._store: dict[str, ConversationState] = {}

    def get(self, session_id: str) -> ConversationState:
        return self._store.get(session_id, ConversationState())

    def upsert(self, session_id: str, state: ConversationState) -> None:
        self._store[session_id] = state

    def clear_pending(self, session_id: str) -> None:
        state = self._store.get(session_id)
        if not state:
            return
        state.pending_fields = []
        self._store[session_id] = state
