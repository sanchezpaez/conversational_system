import json
import logging
from datetime import date, datetime, timezone

from app import backend
from app.backend import BackendClient
from app.conversation_memory import ConversationMemoryStore, ConversationState, InMemoryConversationMemory
from app.dialogue_policy import build_clarification_reply, build_error_reply, get_missing_fields
from app.entity_parser import references_previous_date, references_previous_order
from app.language import detect_language
from app.llm import LLMClient
from app.models import ChatResponse, EntityExtraction, LanguageCode, SessionMetrics

logger = logging.getLogger(__name__)

RESPONSE_TEMPLATES = {
    "en": {
        "order_status": "Good news — I found order {order_id}. Current status: {status}.",
        "change_booking": "All done! I've updated order {order_id} to the new date: {new_date}.",
        "help": "I can help with that. I found order {order_id}. Current status: {status}.",
        "fallback": "I'm sorry I wasn't able to handle this automatically. {message}",
    },
    "es": {
        "order_status": "Buenas noticias: encontré el pedido {order_id}. Estado actual: {status}.",
        "change_booking": "Listo. He actualizado el pedido {order_id} a la nueva fecha: {new_date}.",
        "help": "Puedo ayudarte con eso. He encontrado el pedido {order_id}. Estado actual: {status}.",
        "fallback": "Lo siento, no he podido gestionar esto automáticamente. {message}",
    },
}

STATUS_LABELS = {
    "en": {
        "processing": "processing",
        "shipped": "shipped",
        "delivered": "delivered",
    },
    "es": {
        "processing": "en preparación",
        "shipped": "enviado",
        "delivered": "entregado",
    },
}

FALLBACK_MESSAGES = {
    "en": "A support specialist will review your request.",
    "es": "Un especialista de soporte revisará tu solicitud.",
}


class SupportAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        memory: ConversationMemoryStore | None = None,
        backend_client: BackendClient | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.memory = memory or InMemoryConversationMemory()
        self.backend = backend_client or backend

    def process(self, message: str, session_id: str | None = None) -> ChatResponse:
        prior_state = self.memory.get(session_id) if session_id else ConversationState()
        default_language: LanguageCode = prior_state.language or "en"
        detected_language = detect_language(message, default_language=default_language)

        intent_decision = self.llm_client.classify_intent(message)
        intent_name = intent_decision.intent

        if (
            prior_state.pending_fields
            and prior_state.last_intent is not None
            and intent_name == "fallback"
        ):
            intent_name = prior_state.last_intent

        self._log_event(
            event="intent_detected",
            session_id=session_id,
            intent=intent_name,
            language=detected_language,
        )

        if (
            prior_state.pending_fields
            and prior_state.last_intent is not None
            and intent_name != prior_state.last_intent
            and intent_name != "fallback"
        ):
            self._log_event(
                event="intent_changed",
                session_id=session_id,
                intent=intent_name,
                language=detected_language,
                extra={"previous_intent": prior_state.last_intent},
            )
            prior_state = self._reset_context_preserving_metrics(prior_state)
            prior_state.language = detected_language
            if session_id:
                self.memory.upsert(session_id, prior_state)

        previous_entities = EntityExtraction(
            order_id=prior_state.order_id,
            date=prior_state.booking_date,
        )

        if prior_state.pending_fields and prior_state.last_intent is not None:
            fresh_entities = self.llm_client.extract_entities(message)
            entities = self._merge_entities(previous_entities, fresh_entities)
        else:
            entities = self.llm_client.extract_entities(message)

        entities = self._resolve_anaphora_entities(message, entities, previous_entities)
        self._log_event(
            event="entities_extracted",
            session_id=session_id,
            intent=intent_name,
            language=detected_language,
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
                language=detected_language,
                entities=entities,
                missing_fields=missing_fields,
                backend_result=backend_result,
            )
            reply = build_clarification_reply(intent_name, missing_fields, detected_language)
            updated_state = self._build_updated_state(
                prior_state=prior_state,
                intent_name=intent_name,
                entities=entities,
                pending_fields=missing_fields,
                backend_result=backend_result,
                language=detected_language,
            )
            metrics = self._metrics_from_state(updated_state)

            if session_id:
                self.memory.upsert(session_id, updated_state)

            self._log_event(
                event="reply_generated",
                session_id=session_id,
                intent=intent_name,
                language=detected_language,
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
                language=detected_language,
            )

        if intent_name in {"order_status", "help"}:
            backend_result = self.backend.get_order_status(entities.order_id)
        elif intent_name == "change_booking":
            if self._is_past_iso_date(entities.date):
                backend_result = {
                    "ok": False,
                    "code": "date_in_past",
                }
            else:
                backend_result = self.backend.change_booking(entities.order_id, entities.date)
        else:
            backend_result = self.backend.fallback_support()

        updated_state = self._build_updated_state(
            prior_state=prior_state,
            intent_name=intent_name,
            entities=entities,
            pending_fields=[],
            backend_result=backend_result,
            language=detected_language,
        )
        metrics = self._metrics_from_state(updated_state)

        if session_id:
            self.memory.upsert(session_id, updated_state)

        self._log_event(
            event="backend_result",
            session_id=session_id,
            intent=intent_name,
            language=detected_language,
            entities=entities,
            backend_result=backend_result,
        )

        reply = self._render_reply(intent_name, backend_result, detected_language)
        self._log_event(
            event="reply_generated",
            session_id=session_id,
            intent=intent_name,
            language=detected_language,
            entities=entities,
            backend_result=backend_result,
        )

        return ChatResponse(
            intent=intent_name,
            entities=entities,
            backend_result=backend_result,
            reply=reply,
            metrics=metrics,
            language=detected_language,
        )

    def _merge_entities(self, previous: EntityExtraction, current: EntityExtraction) -> EntityExtraction:
        return EntityExtraction(
            order_id=current.order_id or previous.order_id,
            date=current.date or previous.date,
        )

    def _render_reply(self, intent: str, backend_result: dict, language: LanguageCode) -> str:
        if not backend_result.get("ok", False):
            return build_error_reply(backend_result.get("code", ""), language)

        template = RESPONSE_TEMPLATES[language][intent]
        payload = dict(backend_result)

        if intent == "order_status":
            status = backend_result.get("status", "")
            payload["status"] = STATUS_LABELS[language].get(status, status)

        if intent == "fallback":
            payload["message"] = FALLBACK_MESSAGES[language]

        return template.format(**payload)

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
        pending_fields: list[str],
        backend_result: dict,
        language: LanguageCode,
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
            order_id=entities.order_id,
            booking_date=entities.date,
            pending_fields=pending_fields,
            language=language,
            total_turns=total_turns,
            clarification_turns=clarification_turns,
            successful_turns=successful_turns,
            first_success_turn=first_success_turn,
            updated_at=datetime.now(timezone.utc).isoformat(),
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
            last_intent=state.last_intent,
            order_id=state.order_id,
            booking_date=state.booking_date,
            pending_fields=state.pending_fields,
            language=state.language,
            total_turns=state.total_turns,
            clarification_turns=state.clarification_turns,
            successful_turns=state.successful_turns,
            first_success_turn=state.first_success_turn,
            updated_at=state.updated_at,
        )

    def _log_event(
        self,
        event: str,
        session_id: str | None,
        intent: str,
        language: LanguageCode,
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
            "language": language,
            "entities": entities.model_dump() if entities else None,
            "missing_fields": missing_fields or [],
            "backend_code": backend_result.get("code") if backend_result else None,
            "ok": backend_result.get("ok") if backend_result else None,
        }
        if extra:
            payload.update(extra)

        logger.info(json.dumps(payload, ensure_ascii=False))
