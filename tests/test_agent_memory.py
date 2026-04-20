from app.agent import SupportAgent
from app.models import EntityExtraction, IntentDecision


def test_memory_completes_change_booking_across_three_turns(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="change_booking")

    def extract_turn_1(_: str) -> EntityExtraction:
        return EntityExtraction(order_id=None, date=None)

    def extract_turn_2(_: str) -> EntityExtraction:
        return EntityExtraction(order_id="7821", date=None)

    def extract_turn_3(_: str) -> EntityExtraction:
        return EntityExtraction(order_id=None, date="2026-05-10")

    mock_llm_client.extract_entities = extract_turn_1
    first = agent.process("I need to change my booking", session_id="s1")
    assert first.backend_result["code"] == "need_clarification"
    assert first.backend_result["missing_fields"] == ["order_id", "date"]

    mock_llm_client.extract_entities = extract_turn_2
    second = agent.process("It is order 7821", session_id="s1")
    assert second.backend_result["code"] == "need_clarification"
    assert second.backend_result["missing_fields"] == ["date"]

    mock_llm_client.extract_entities = extract_turn_3
    third = agent.process("2026-05-10", session_id="s1")
    assert third.backend_result["ok"] is True
    assert third.backend_result["code"] == "booking_changed"
    assert third.backend_result["order_id"] == "7821"
    assert third.backend_result["new_date"] == "2026-05-10"


def test_memory_isolated_between_sessions(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="change_booking")

    def extract_entities(message: str) -> EntityExtraction:
        if "1111" in message:
            return EntityExtraction(order_id="1111", date=None)
        if "2222" in message:
            return EntityExtraction(order_id="2222", date=None)
        if "2026-06-01" in message:
            return EntityExtraction(order_id=None, date="2026-06-01")
        if "2026-06-02" in message:
            return EntityExtraction(order_id=None, date="2026-06-02")
        return EntityExtraction(order_id=None, date=None)

    mock_llm_client.extract_entities = extract_entities

    agent.process("Change my booking", session_id="a")
    agent.process("Change my booking", session_id="b")

    agent.process("Order 1111", session_id="a")
    agent.process("Order 2222", session_id="b")

    result_a = agent.process("2026-06-01", session_id="a")
    result_b = agent.process("2026-06-02", session_id="b")

    assert result_a.backend_result["order_id"] == "1111"
    assert result_b.backend_result["order_id"] == "2222"


def test_pending_clarification_clears_after_success(mock_llm_client):
    agent = SupportAgent(llm_client=mock_llm_client)
    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="change_booking")

    def extract_entities(message: str) -> EntityExtraction:
        if "AB-123" in message:
            return EntityExtraction(order_id="AB-123", date=None)
        if "2026-05-09" in message:
            return EntityExtraction(order_id=None, date="2026-05-09")
        return EntityExtraction(order_id=None, date=None)

    mock_llm_client.extract_entities = extract_entities

    first = agent.process("Change my booking", session_id="clear-1")
    assert first.backend_result["code"] == "need_clarification"

    agent.process("Order AB-123", session_id="clear-1")
    success = agent.process("2026-05-09", session_id="clear-1")
    assert success.backend_result["ok"] is True

    state = agent.memory.get("clear-1")
    assert state.pending_clarification == []
