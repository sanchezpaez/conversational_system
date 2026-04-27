import json
import logging

from app.agent import SupportAgent
from app.models import EntityExtraction, IntentDecision


def _agent_events(caplog) -> list[dict]:
    events: list[dict] = []
    for record in caplog.records:
        if record.name != "app.agent":
            continue
        try:
            events.append(json.loads(record.getMessage()))
        except json.JSONDecodeError:
            continue
    return events


def test_agent_emits_structured_json_events_for_success(mock_llm_client, caplog):
    caplog.set_level(logging.INFO, logger="app.agent")
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="order_status")
    mock_llm_client.extract_entities = lambda _: EntityExtraction(order_id="AB-123", date=None)

    agent.process("Where is my order AB-123?", session_id="log-1")

    events = _agent_events(caplog)
    event_names = {event["event"] for event in events}

    assert "intent_detected" in event_names
    assert "entities_extracted" in event_names
    assert "backend_result" in event_names
    assert "reply_generated" in event_names

    sample = events[0]
    assert "timestamp" in sample
    assert "event" in sample
    assert "session_id" in sample
    assert "intent" in sample
    assert "entities" in sample
    assert "missing_fields" in sample
    assert "backend_code" in sample
    assert "ok" in sample


def test_agent_emits_clarification_event_with_missing_fields(mock_llm_client, caplog):
    caplog.set_level(logging.INFO, logger="app.agent")
    agent = SupportAgent(llm_client=mock_llm_client)

    mock_llm_client.classify_intent = lambda _: IntentDecision(intent="order_status")
    mock_llm_client.extract_entities = lambda _: EntityExtraction(order_id=None, date=None)

    agent.process("Where is my order?", session_id="log-2")

    events = _agent_events(caplog)
    clarification_events = [event for event in events if event.get("event") == "clarification_requested"]

    assert clarification_events
    clarification = clarification_events[0]
    assert clarification["missing_fields"] == ["order_id"]
    assert clarification["backend_code"] == "need_clarification"
    assert clarification["ok"] is False
