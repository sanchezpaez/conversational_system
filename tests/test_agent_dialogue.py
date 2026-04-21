from app.agent import SupportAgent
from app.models import EntityExtraction, IntentDecision


def test_agent_asks_for_order_id_before_order_status_backend(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="order_status")
    mock_llm_client.extract_entities = lambda _: EntityExtraction(order_id=None, date=None)

    result = agent.process("Where is my order?")

    assert result.backend_result["code"] == "need_clarification"
    assert result.backend_result["missing_fields"] == ["order_id"]
    assert "order ID" in result.reply


def test_agent_asks_for_date_before_change_booking_backend(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="change_booking")
    mock_llm_client.extract_entities = lambda _: EntityExtraction(order_id="AB-123", date=None)

    result = agent.process("Change my booking for order AB-123")

    assert result.backend_result["code"] == "need_clarification"
    assert result.backend_result["missing_fields"] == ["date"]
    assert "YYYY-MM-DD" in result.reply


def test_agent_rejects_past_date_for_change_booking(mock_llm_client, monkeypatch):
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="change_booking")
    mock_llm_client.extract_entities = lambda _: EntityExtraction(order_id="AB-123", date="2000-01-01")

    def fail_change_booking(*_args, **_kwargs):
        raise AssertionError("backend.change_booking should not be called for past dates")

    monkeypatch.setattr("app.agent.backend.change_booking", fail_change_booking)

    result = agent.process("Change booking for order AB-123 to 2000-01-01")

    assert result.backend_result["ok"] is False
    assert result.backend_result["code"] == "date_in_past"
    assert "future date" in result.reply
