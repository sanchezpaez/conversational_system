import logging

from app import backend
from app.llm import LLMClient
from app.models import ChatResponse

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
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def process(self, message: str) -> ChatResponse:
        intent_decision = self.llm_client.classify_intent(message)
        entities = self.llm_client.extract_entities(message)

        logger.info("intent=%s", intent_decision.intent)
        logger.info("entities=%s", entities.model_dump())

        if intent_decision.intent == "order_status":
            backend_result = backend.get_order_status(entities.order_id)
        elif intent_decision.intent == "change_booking":
            backend_result = backend.change_booking(entities.order_id, entities.date)
        else:
            backend_result = backend.fallback_support()

        logger.info("backend_result=%s", backend_result)

        reply = self._render_reply(intent_decision.intent, backend_result)
        logger.info("final_reply=%s", reply)

        return ChatResponse(
            intent=intent_decision.intent,
            entities=entities,
            backend_result=backend_result,
            reply=reply,
        )

    def _render_reply(self, intent: str, backend_result: dict) -> str:
        if not backend_result.get("ok", False):
            return backend_result.get("message", "I could not process your request.")

        template = RESPONSE_TEMPLATES[intent]
        return template.format(**backend_result)
