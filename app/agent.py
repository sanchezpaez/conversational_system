import logging

from app import backend
from app.conversation_memory import ConversationState, InMemoryConversationMemory
from app.dialogue_policy import build_clarification_reply, build_error_reply, get_missing_fields
from app.llm import LLMClient
from app.models import ChatResponse, EntityExtraction

logger = logging.getLogger(__name__)

RESPONSE_TEMPLATES = {
    "order_status": (
        "I checked order {order_id}. Current status: {status}."
    ),
    "change_booking": (
        "Booking updated for order {order_id}. New date: {new_date}."
    ),
    "fallback": (
        "I could not complete this automatically. {message}"
    ),
}


class SupportAgent:
    def __init__(self, llm_client: LLMClient, memory: InMemoryConversationMemory | None = None) -> None:
        self.llm_client = llm_client
        self.memory = memory or InMemoryConversationMemory()

    def process(self, message: str, session_id: str | None = None) -> ChatResponse:
        prior_state = self.memory.get(session_id) if session_id else ConversationState()

        intent_decision = self.llm_client.classify_intent(message)
        intent_name = intent_decision.intent

        if (
            prior_state.pending_clarification
            and prior_state.last_intent is not None
            and intent_name != prior_state.last_intent
        ):
            logger.info(
                "intent_changed from=%s to=%s — resetting state",
                prior_state.last_intent,
                intent_name,
            )
            prior_state = ConversationState()
            if session_id:
                self.memory.upsert(session_id, ConversationState())

        if prior_state.pending_clarification and prior_state.last_intent is not None:
            fresh_entities = self.llm_client.extract_entities(message)
            entities = self._merge_entities(prior_state.last_entities, fresh_entities)
        else:
            entities = self.llm_client.extract_entities(message)

        logger.info("intent=%s", intent_name)
        logger.info("entities=%s", entities.model_dump())

        missing_fields = get_missing_fields(intent_name, entities)
        if missing_fields:
            logger.info("missing_fields=%s", missing_fields)
            backend_result = {
                "ok": False,
                "code": "need_clarification",
                "missing_fields": missing_fields,
            }
            reply = build_clarification_reply(intent_name, missing_fields)

            if session_id:
                self.memory.upsert(
                    session_id,
                    ConversationState(
                        last_intent=intent_name,
                        last_entities=entities,
                        pending_clarification=missing_fields,
                    ),
                )

            logger.info("final_reply=%s", reply)
            return ChatResponse(
                intent=intent_name,
                entities=entities,
                backend_result=backend_result,
                reply=reply,
            )

        if intent_name == "order_status":
            backend_result = backend.get_order_status(entities.order_id)
        elif intent_name == "change_booking":
            backend_result = backend.change_booking(entities.order_id, entities.date)
        else:
            backend_result = backend.fallback_support()

        if session_id:
            self.memory.upsert(
                session_id,
                ConversationState(
                    last_intent=intent_name,
                    last_entities=entities,
                    pending_clarification=[],
                ),
            )

        logger.info("backend_result=%s", backend_result)

        reply = self._render_reply(intent_name, backend_result)
        logger.info("final_reply=%s", reply)

        return ChatResponse(
            intent=intent_name,
            entities=entities,
            backend_result=backend_result,
            reply=reply,
        )

    def _merge_entities(self, previous: EntityExtraction, current: EntityExtraction) -> EntityExtraction:
        return EntityExtraction(
            order_id=current.order_id or previous.order_id,
            date=current.date or previous.date,
        )

    def _render_reply(self, intent: str, backend_result: dict) -> str:
        if not backend_result.get("ok", False):
            return build_error_reply(backend_result.get("code", ""))

        template = RESPONSE_TEMPLATES[intent]
        return template.format(**backend_result)
