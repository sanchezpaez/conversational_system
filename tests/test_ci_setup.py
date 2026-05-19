from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_ci_workflow_exists() -> None:
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"

    assert workflow_path.exists()

    workflow_content = workflow_path.read_text(encoding="utf-8")
    assert "name: CI" in workflow_content
    assert "pull_request:" in workflow_content
    assert "actions/checkout@v4" in workflow_content
    assert "actions/setup-python@v5" in workflow_content
    assert "uv sync --frozen --extra dev" in workflow_content
    assert "uv run pytest -q" in workflow_content
    assert "docker compose config --quiet" in workflow_content


def test_ci_workflow_sets_safe_env_for_tests() -> None:
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"

    workflow_content = workflow_path.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY: sk-fake-key-for-ci" in workflow_content
    assert "CHAT_API_KEY: test-key" in workflow_content
    assert "BACKEND_MODE: mock" in workflow_content
    assert "MEMORY_BACKEND: memory" in workflow_content