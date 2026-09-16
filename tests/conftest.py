import json
from unittest.mock import MagicMock

import pytest

from app.models import EntityExtraction, IntentDecision


@pytest.fixture
def mock_llm_client():
    """Fixture providing a mock LLM client for testing without calling OpenAI."""
    client = MagicMock()

    def mock_classify_intent(message: str) -> IntentDecision:
        if "order" in message.lower() and "where" in message.lower():
            return IntentDecision(intent="order_status")
        elif "move" in message.lower() or "change" in message.lower():
            return IntentDecision(intent="change_booking")
        else:
            return IntentDecision(intent="fallback")

    def mock_extract_entities(message: str) -> EntityExtraction:
        order_id = None
        date = None

        import re

        # Extract order ID: support both explicit "order AB-123" and bare follow-up values like "AB-123".
        order_pattern = r"order\s+([\w-]+)"
        order_match = re.search(order_pattern, message, re.IGNORECASE)
        if order_match:
            order_id = order_match.group(1)
        else:
            bare_match = re.search(r"\b([A-Za-z]+-\d+|\d+)\b", message)
            if bare_match:
                order_id = bare_match.group(1)

        # Extract date: look for ISO format YYYY-MM-DD
        date_pattern = r"(\d{4}-\d{2}-\d{2})"
        date_match = re.search(date_pattern, message)
        if date_match:
            date = date_match.group(1)

        return EntityExtraction(order_id=order_id, date=date)

    client.classify_intent = mock_classify_intent
    client.extract_entities = mock_extract_entities

    return client
