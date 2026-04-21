import json

from openai import OpenAI

from app.config import get_openai_api_key
from app.entity_parser import extract_entities_locally
from app.models import EntityExtraction, IntentDecision


class LLMClient:
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        api_key = get_openai_api_key()

        self.model = model
        self.client = OpenAI(api_key=api_key)

    def classify_intent(self, user_message: str) -> IntentDecision:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an intent classifier for customer support. "
                    "Classify into exactly one intent: order_status, change_booking, fallback. "
                    "Return strict JSON with key 'intent' only."
                ),
            },
            {
                "role": "user",
                "content": "Where is my order AB-123?",
            },
            {
                "role": "assistant",
                "content": '{"intent":"order_status"}',
            },
            {
                "role": "user",
                "content": "Please move my delivery to next Tuesday, order 8921.",
            },
            {
                "role": "assistant",
                "content": '{"intent":"change_booking"}',
            },
            {
                "role": "user",
                "content": "I want to talk about your privacy policy.",
            },
            {
                "role": "assistant",
                "content": '{"intent":"fallback"}',
            },
            {
                "role": "user",
                "content": f"Message: {user_message}",
            },
        ]

        raw_json = self._chat_json(messages)
        return IntentDecision.model_validate(raw_json)

    def extract_entities(self, user_message: str) -> EntityExtraction:
        local_entities = extract_entities_locally(user_message)
        if local_entities.order_id and local_entities.date:
            return local_entities

        messages = [
            {
                "role": "system",
                "content": (
                    "Extract entities from the user message. "
                    "Return strict JSON with keys: order_id, date. "
                    "If missing, use null. Keep date as the exact text or normalized ISO date when explicit."
                ),
            },
            {
                "role": "user",
                "content": f"Message: {user_message}",
            },
        ]

        raw_json = self._chat_json(messages)
        llm_entities = EntityExtraction.model_validate(raw_json)
        return EntityExtraction(
            order_id=local_entities.order_id or llm_entities.order_id,
            date=local_entities.date or llm_entities.date,
        )

    def _chat_json(self, messages: list[dict]) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        return json.loads(content)
