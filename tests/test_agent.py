import pytest

from app.agent import SupportAgent


def test_agent_classifies_order_status_intent(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)
    result = agent.process("Where is my order AB-123?")

    assert result.intent == "order_status"
    assert result.entities.order_id == "AB-123"


def test_agent_classifies_change_booking_intent(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)
    result = agent.process("Can you move booking for order 7821 to 2026-04-02?")

    assert result.intent == "change_booking"
    assert result.entities.order_id == "7821"
    assert result.entities.date == "2026-04-02"


def test_agent_classifies_fallback_intent(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)
    result = agent.process("I want to talk about your privacy policy.")

    assert result.intent == "fallback"


def test_agent_backend_call_for_order_status(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)
    result = agent.process("Where is my order AB-123?")

    assert result.backend_result["ok"] is True
    assert result.backend_result["code"] == "order_status"
    assert "status" in result.backend_result


def test_agent_handles_missing_order_id(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)
    from app.models import EntityExtraction
    mock_llm_client.extract_entities = lambda msg: EntityExtraction(order_id=None, date=None)
    result = agent.process("Where is my order?")

    assert result.intent == "order_status"
    assert result.backend_result["ok"] is False
    assert result.backend_result["code"] == "need_clarification"
    assert result.backend_result["missing_fields"] == ["order_id"]
    assert "order ID" in result.reply


def test_agent_generates_reply(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)
    result = agent.process("Where is my order AB-123?")

    assert isinstance(result.reply, str)
    assert len(result.reply) > 0
