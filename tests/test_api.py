import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


def test_chat_endpoint_exists(client):
    response = client.post("/chat", json={"message": "Hello"})
    # Might fail with ConfigurationError if OPENAI_API_KEY is missing, but endpoint exists.
    assert response.status_code in (200, 503)


def test_chat_with_valid_message_returns_chat_response(client, mock_llm_client):
    """Test /chat endpoint with mock LLM backend."""
    with patch("main.LLMClient") as MockLLM:
        MockLLM.return_value = mock_llm_client

        response = client.post("/chat", json={"message": "Where is my order AB-123?"})

        assert response.status_code == 200
        data = response.json()
        assert "intent" in data
        assert "entities" in data
        assert "backend_result" in data
        assert "reply" in data


def test_chat_accepts_session_id(client, mock_llm_client):
    with patch("main.LLMClient") as MockLLM:
        MockLLM.return_value = mock_llm_client

        response = client.post(
            "/chat",
            json={"message": "Where is my order AB-123?", "session_id": "session-1"},
        )

        assert response.status_code == 200


def test_chat_endpoint_validates_input(client):
    """Test /chat endpoint rejects empty messages."""
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422  # Validation error


def test_chat_endpoint_handles_configuration_error(client):
    """Test /chat endpoint returns 503 when OPENAI_API_KEY is missing."""
    from app.exceptions import ConfigurationError

    with patch("main.build_agent") as mock_build:
        mock_build.side_effect = ConfigurationError("OPENAI_API_KEY is not set")

        response = client.post("/chat", json={"message": "Hello"})

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]
