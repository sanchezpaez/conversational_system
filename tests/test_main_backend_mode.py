from app.backend import MockBackendClient
from app.backend_real import RealBackendClient
from main import build_agent


def test_build_agent_uses_mock_backend_by_default(monkeypatch, mock_llm_client):
    monkeypatch.setattr("main.LLMClient", lambda: mock_llm_client)
    monkeypatch.setattr("main.get_memory_backend", lambda: "memory")
    monkeypatch.setattr("main.get_backend_mode", lambda: "mock")

    agent = build_agent()

    assert isinstance(agent.backend, MockBackendClient)


def test_build_agent_uses_real_backend_when_configured(monkeypatch, mock_llm_client):
    monkeypatch.setattr("main.LLMClient", lambda: mock_llm_client)
    monkeypatch.setattr("main.get_memory_backend", lambda: "memory")
    monkeypatch.setattr("main.get_backend_mode", lambda: "real")
    monkeypatch.setattr("main.get_real_backend_base_url", lambda: "https://backend.example")
    monkeypatch.setattr("main.get_real_backend_api_key", lambda: "secret")

    agent = build_agent()

    assert isinstance(agent.backend, RealBackendClient)
