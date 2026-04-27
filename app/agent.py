import json
import logging
from datetime import date, datetime, timezone

from app import backend
from app.conversation_memory import ConversationState, InMemoryConversationMemory
from app.dialogue_policy import build_clarification_reply, build_error_reply, get_missing_fields
from app.entity_parser import references_previous_date, references_previous_order
from app.llm import LLMClient
from app.models import ChatResponse, EntityExtraction, SessionMetrics

logger = logging.getLogger(__name__)

RESPONSE_TEMPLATES = {
    "order_status": (
        "Good news — I found order {order_id}. Current status: {status}."
    ),
    "change_booking": (
        "All done! I've updated order {order_id} to the new date: {new_date}."
    ),
    "fallback": (
        "I'm sorry I wasn't able to handle this automatically. {message}"
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
        self._log_event(
            event="intent_detected",
            session_id=session_id,
            intent=intent_name,
        )

        if (
            prior_state.pending_clarification
            and prior_state.last_intent is not None
            and intent_name != prior_state.last_intent
        ):
            self._log_event(
                event="intent_changed",
                session_id=session_id,
                intent=intent_name,
                extra={"previous_intent": prior_state.last_intent},
            )
            prior_state = self._reset_context_preserving_metrics(prior_state)
            if session_id:
                self.memory.upsert(session_id, prior_state)

        if prior_state.pending_clarification and prior_state.last_intent is not None:
            fresh_entities = self.llm_client.extract_entities(message)
            entities = self._merge_entities(prior_state.last_entities, fresh_entities)
        else:
            entities = self.llm_client.extract_entities(message)

        entities = self._resolve_anaphora_entities(message, entities, prior_state.last_entities)
        self._log_event(
            event="entities_extracted",
            session_id=session_id,
            intent=intent_name,
            entities=entities,
        )

        missing_fields = get_missing_fields(intent_name, entities)
        if missing_fields:
            backend_result = {
                "ok": False,
                "code": "need_clarification",
                "missing_fields": missing_fields,
            }
            self._log_event(
                event="clarification_requested",
                session_id=session_id,
                intent=intent_name,
                entities=entities,
                missing_fields=missing_fields,
                backend_result=backend_result,
            )
            reply = build_clarification_reply(intent_name, missing_fields)
            updated_state = self._build_updated_state(
                prior_state=prior_state,
                intent_name=intent_name,
                entities=entities,
                pending_clarification=missing_fields,
                backend_result=backend_result,
            )
            metrics = self._metrics_from_state(updated_state)

            if session_id:
                self.memory.upsert(session_id, updated_state)

            self._log_event(
                event="reply_generated",
                session_id=session_id,
                intent=intent_name,
                entities=entities,
                missing_fields=missing_fields,
                backend_result=backend_result,
            )
            return ChatResponse(
                intent=intent_name,
                entities=entities,
                backend_result=backend_result,
                reply=reply,
                metrics=metrics,
            )

        if intent_name == "order_status":
            backend_result = backend.get_order_status(entities.order_id)
        elif intent_name == "change_booking":
            if self._is_past_iso_date(entities.date):
                backend_result = {
                    "ok": False,
                    "code": "date_in_past",
                }
            else:
                backend_result = backend.change_booking(entities.order_id, entities.date)
        else:
            backend_result = backend.fallback_support()

        updated_state = self._build_updated_state(
            prior_state=prior_state,
            intent_name=intent_name,
            entities=entities,
            pending_clarification=[],
            backend_result=backend_result,
        )
        metrics = self._metrics_from_state(updated_state)

        if session_id:
            self.memory.upsert(session_id, updated_state)

        self._log_event(
            event="backend_result",
            session_id=session_id,
            intent=intent_name,
            entities=entities,
            backend_result=backend_result,
        )

        reply = self._render_reply(intent_name, backend_result)
        self._log_event(
            event="reply_generated",
            session_id=session_id,
            intent=intent_name,
            entities=entities,
            backend_result=backend_result,
        )

        return ChatResponse(
            intent=intent_name,
            entities=entities,
            backend_result=backend_result,
            reply=reply,
            metrics=metrics,
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

    def _is_past_iso_date(self, raw_date: str | None) -> bool:
        if not raw_date:
            return False

        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError:
            return False

        return parsed_date < date.today()

    def _resolve_anaphora_entities(
        self,
        message: str,
        current_entities: EntityExtraction,
        previous_entities: EntityExtraction,
    ) -> EntityExtraction:
        resolved_order_id = current_entities.order_id
        resolved_date = current_entities.date

        if not resolved_order_id and previous_entities.order_id and references_previous_order(message):
            resolved_order_id = previous_entities.order_id

        if not resolved_date and previous_entities.date and references_previous_date(message):
            resolved_date = previous_entities.date

        return EntityExtraction(order_id=resolved_order_id, date=resolved_date)

    def _build_updated_state(
        self,
        prior_state: ConversationState,
        intent_name: str,
        entities: EntityExtraction,
        pending_clarification: list[str],
        backend_result: dict,
    ) -> ConversationState:
        total_turns = prior_state.total_turns + 1
        clarification_turns = prior_state.clarification_turns
        successful_turns = prior_state.successful_turns
        first_success_turn = prior_state.first_success_turn

        if backend_result.get("code") == "need_clarification":
            clarification_turns += 1

        if self._is_resolution_success(backend_result):
            successful_turns += 1
            if first_success_turn is None:
                first_success_turn = total_turns

        return ConversationState(
            last_intent=intent_name,
            last_entities=entities,
            pending_clarification=pending_clarification,
            total_turns=total_turns,
            clarification_turns=clarification_turns,
            successful_turns=successful_turns,
            first_success_turn=first_success_turn,
        )

    def _metrics_from_state(self, state: ConversationState) -> SessionMetrics:
        if state.total_turns == 0:
            return SessionMetrics(
                turns_to_resolution=state.first_success_turn,
                clarification_rate=0.0,
                success_rate=0.0,
            )

        return SessionMetrics(
            turns_to_resolution=state.first_success_turn,
            clarification_rate=state.clarification_turns / state.total_turns,
            success_rate=state.successful_turns / state.total_turns,
        )

    def _is_resolution_success(self, backend_result: dict) -> bool:
        if not backend_result.get("ok", False):
            return False
        return backend_result.get("code") != "fallback"

    def _reset_context_preserving_metrics(self, state: ConversationState) -> ConversationState:
        return ConversationState(
            total_turns=state.total_turns,
            clarification_turns=state.clarification_turns,
            successful_turns=state.successful_turns,
            first_success_turn=state.first_success_turn,
        )

    def _log_event(
        self,
        event: str,
        session_id: str | None,
        intent: str,
        entities: EntityExtraction | None = None,
        missing_fields: list[str] | None = None,
        backend_result: dict | None = None,
        extra: dict | None = None,
    ) -> None:
        payload: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "session_id": session_id,
            "intent": intent,
            "entities": entities.model_dump() if entities else None,
            "missing_fields": missing_fields or [],
            "backend_code": backend_result.get("code") if backend_result else None,
            "ok": backend_result.get("ok") if backend_result else None,
        }
        if extra:
            payload.update(extra)

        logger.info(json.dumps(payload, ensure_ascii=False))
