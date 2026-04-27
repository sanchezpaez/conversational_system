from app.agent import SupportAgent
from app.language import detect_language
from app.models import EntityExtraction, IntentDecision


def test_detect_language_spanish_message():
    assert detect_language("¿Dónde está mi pedido?") == "es"


def test_detect_language_english_message():
    assert detect_language("Where is my order AB-123?") == "en"


def test_detect_language_uses_default_on_tie():
    assert detect_language("AB-123", default_language="es") == "es"


def test_agent_persists_language_across_ambiguous_turns(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="order_status")

    def extract_entities(message: str) -> EntityExtraction:
        if "AB-123" in message:
            return EntityExtraction(order_id="AB-123", date=None)
        return EntityExtraction(order_id=None, date=None)

    mock_llm_client.extract_entities = extract_entities

    first = agent.process("¿Dónde está mi pedido AB-123?", session_id="lang-1")
    assert first.language == "es"

    second = agent.process("AB-123", session_id="lang-1")
    assert second.language == "es"

    state = agent.memory.get("lang-1")
    assert state.language == "es"
