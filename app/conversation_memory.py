from dataclasses import dataclass, field
from typing import Protocol

from app.models import EntityExtraction, IntentName, LanguageCode


@dataclass
class ConversationState:
    last_intent: IntentName | None = None
    last_entities: EntityExtraction = field(default_factory=EntityExtraction)
    pending_clarification: list[str] = field(default_factory=list)
    language: LanguageCode | None = None
    total_turns: int = 0
    clarification_turns: int = 0
    successful_turns: int = 0
    first_success_turn: int | None = None


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
        state.pending_clarification = []
        self._store[session_id] = state
