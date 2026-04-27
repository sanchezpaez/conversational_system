from app.agent import SupportAgent
from app.models import EntityExtraction, IntentDecision


def test_agent_returns_spanish_clarification_for_spanish_message(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="order_status")
    mock_llm_client.extract_entities = lambda _: EntityExtraction(order_id=None, date=None)

    result = agent.process("¿Dónde está mi pedido?", session_id="reply-es-1")

    assert result.language == "es"
    assert "ID de tu pedido" in result.reply


def test_agent_returns_spanish_success_reply_for_spanish_message(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="order_status")
    mock_llm_client.extract_entities = lambda _: EntityExtraction(order_id="AB-123", date=None)

    result = agent.process("¿Dónde está mi pedido AB-123?", session_id="reply-es-2")

    assert result.language == "es"
    assert "Estado actual" in result.reply


def test_agent_returns_english_reply_for_english_message(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="order_status")
    mock_llm_client.extract_entities = lambda _: EntityExtraction(order_id="AB-123", date=None)

    result = agent.process("Where is my order AB-123?", session_id="reply-en-1")

    assert result.language == "en"
    assert "Current status" in result.reply


def test_agent_keeps_spanish_reply_on_ambiguous_follow_up(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="change_booking")

    def extract_entities(message: str) -> EntityExtraction:
        if "AB-123" in message:
            return EntityExtraction(order_id="AB-123", date=None)
        return EntityExtraction(order_id=None, date=None)

    mock_llm_client.extract_entities = extract_entities

    first = agent.process("Quiero cambiar mi reserva", session_id="reply-es-3")
    assert first.language == "es"
    assert "ID de tu pedido" in first.reply

    second = agent.process("AB-123", session_id="reply-es-3")
    assert second.language == "es"
    assert "qué nueva fecha quieres" in second.reply.lower()
