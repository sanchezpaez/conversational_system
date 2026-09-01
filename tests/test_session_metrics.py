from datetime import date, timedelta

from app.agent import SupportAgent
from app.models import EntityExtraction, IntentDecision


def test_session_metrics_direct_resolution(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="order_status")
    mock_llm_client.extract_entities = lambda _: EntityExtraction(order_id="AB-123", date=None)

    result = agent.process("Where is my order AB-123?", session_id="metrics-1")

    assert result.metrics is not None
    assert result.metrics.turns_to_resolution == 1
    assert result.metrics.clarification_rate == 0.0
    assert result.metrics.success_rate == 1.0


def test_session_metrics_clarification_then_success(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)
    future_date = (date.today() + timedelta(days=20)).isoformat()

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="change_booking")

    def extract_entities(message: str) -> EntityExtraction:
        order_id = "7821" if "7821" in message else None
        date = future_date if future_date in message else None
        return EntityExtraction(order_id=order_id, date=date)

    mock_llm_client.extract_entities = extract_entities

    first = agent.process("Please change my booking", session_id="metrics-2")
    assert first.metrics is not None
    assert first.metrics.turns_to_resolution is None
    assert first.metrics.clarification_rate == 1.0
    assert first.metrics.success_rate == 0.0

    second = agent.process(f"Order 7821 and {future_date}", session_id="metrics-2")
    assert second.metrics is not None
    assert second.metrics.turns_to_resolution == 2
    assert second.metrics.clarification_rate == 0.5
    assert second.metrics.success_rate == 0.5


def test_session_metrics_fallback_does_not_count_as_resolution(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)

    def classify_intent(message: str) -> IntentDecision:
        if "where" in message.lower() and "order" in message.lower():
            return IntentDecision(intent="order_status")
        return IntentDecision(intent="fallback")

    def extract_entities(message: str) -> EntityExtraction:
        if "AB-123" in message:
            return EntityExtraction(order_id="AB-123", date=None)
        return EntityExtraction(order_id=None, date=None)

    mock_llm_client.classify_intent = classify_intent
    mock_llm_client.extract_entities = extract_entities

    first = agent.process("I need help with the website", session_id="metrics-3")
    assert first.metrics is not None
    assert first.metrics.turns_to_resolution is None
    assert first.metrics.success_rate == 0.0

    second = agent.process("Where is my order AB-123?", session_id="metrics-3")
    assert second.metrics is not None
    assert second.metrics.turns_to_resolution == 2
    assert second.metrics.success_rate == 0.5
