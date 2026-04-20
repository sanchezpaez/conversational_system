from dataclasses import dataclass, field

from app.models import EntityExtraction, IntentName


@dataclass
class ConversationState:
    last_intent: IntentName | None = None
    last_entities: EntityExtraction = field(default_factory=EntityExtraction)
    pending_clarification: list[str] = field(default_factory=list)


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
