import json

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


def test_chat_endpoint_exists(client):
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code in (401, 503)


def test_chat_with_valid_message_returns_chat_response(client, mock_llm_client):
    """Test /chat endpoint with mock LLM backend."""
    with patch("main.LLMClient") as MockLLM, patch("main.get_chat_api_key", return_value="test-key"):
        MockLLM.return_value = mock_llm_client

        response = client.post(
            "/chat",
            json={"message": "Where is my order AB-123?"},
            headers={"X-API-Key": "test-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "intent" in data
        assert "entities" in data
        assert "backend_result" in data
        assert "reply" in data
        assert "language" in data


def test_chat_accepts_session_id(client, mock_llm_client):
    with patch("main.LLMClient") as MockLLM, patch("main.get_chat_api_key", return_value="test-key"):
        MockLLM.return_value = mock_llm_client

        response = client.post(
            "/chat",
            json={"message": "Where is my order AB-123?", "session_id": "session-1"},
            headers={"X-API-Key": "test-key"},
        )

        assert response.status_code == 200


def test_chat_records_multiple_turns_in_one_session_file(client, mock_llm_client, tmp_path):
    session_id = "session-with-two-turns"
    with (
        patch("main.LLMClient") as MockLLM,
        patch("main.get_chat_api_key", return_value="test-key"),
        patch("main.SESSION_DIR", str(tmp_path)),
    ):
        MockLLM.return_value = mock_llm_client

        for message in ("Where is my order AB-123?", "Thank you"):
            response = client.post(
                "/chat",
                json={"message": message, "session_id": session_id},
                headers={"X-API-Key": "test-key"},
            )
            assert response.status_code == 200

    payload = json.loads((tmp_path / f"{session_id}.json").read_text())
    assert payload["metrics"]["total_turns"] == 2
    assert [turn["user_message"] for turn in payload["turns"]] == [
        "Where is my order AB-123?",
        "Thank you",
    ]


def test_chat_endpoint_validates_input(client):
    """Test /chat endpoint rejects empty messages."""
    with patch("main.get_chat_api_key", return_value="test-key"):
        response = client.post(
            "/chat",
            json={"message": ""},
            headers={"X-API-Key": "test-key"},
        )
    assert response.status_code == 422  # Validation error


def test_chat_rejects_empty_session_id(client):
    """Test /chat endpoint rejects empty session identifiers."""
    with patch("main.get_chat_api_key", return_value="test-key"):
        response = client.post(
            "/chat",
            json={"message": "Hello", "session_id": ""},
            headers={"X-API-Key": "test-key"},
        )

    assert response.status_code == 422


def test_chat_endpoint_handles_configuration_error(client):
    """Test /chat endpoint returns 503 when OPENAI_API_KEY is missing."""
    from app.exceptions import ConfigurationError

    with patch("main.build_agent") as mock_build, patch("main.get_chat_api_key", return_value="test-key"):
        mock_build.side_effect = ConfigurationError("OPENAI_API_KEY is not set")

        response = client.post(
            "/chat",
            json={"message": "Hello"},
            headers={"X-API-Key": "test-key"},
        )

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]


def test_chat_rejects_invalid_api_key(client):
    with patch("main.get_chat_api_key", return_value="test-key"):
        response = client.post(
            "/chat",
            json={"message": "Hello"},
            headers={"X-API-Key": "wrong-key"},
        )

        assert response.status_code == 401


def test_chat_rejects_missing_api_key_even_when_configured(client):
    with patch("main.get_chat_api_key", return_value="test-key"):
        response = client.post("/chat", json={"message": "Hello"})

        assert response.status_code == 401


def test_ui_endpoint_serves_html(client):
    response = client.get("/ui")

    assert response.status_code == 200
    assert "Support Agent" in response.text


def test_ui_endpoint_returns_404_when_file_is_missing(client):
    missing_ui_file = Mock()
    missing_ui_file.exists.return_value = False

    with patch("main.UI_FILE_PATH", missing_ui_file):
        response = client.get("/ui")

    assert response.status_code == 404
    assert response.json()["detail"] == "UI not found."
