from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_dockerfile_contains_expected_runtime_configuration() -> None:
    dockerfile_path = PROJECT_ROOT / "Dockerfile"

    assert dockerfile_path.exists()

    dockerfile = dockerfile_path.read_text(encoding="utf-8")
    assert "FROM python:3.13-slim" in dockerfile
    assert "WORKDIR /app" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert "uvicorn" in dockerfile
    assert "--host" in dockerfile
    assert "0.0.0.0" in dockerfile


def test_docker_compose_configures_app_service() -> None:
    compose_path = PROJECT_ROOT / "docker-compose.yml"

    assert compose_path.exists()

    compose_content = compose_path.read_text(encoding="utf-8")
    assert "services:" in compose_content
    assert "app:" in compose_content
    assert '"8000:8000"' in compose_content
    assert "env_file:" in compose_content
    assert "- .env" in compose_content


def test_dockerignore_excludes_local_environment_and_secrets() -> None:
    dockerignore_path = PROJECT_ROOT / ".dockerignore"

    assert dockerignore_path.exists()

    dockerignore_content = dockerignore_path.read_text(encoding="utf-8")
    assert ".venv" in dockerignore_content
    assert ".env" in dockerignore_content
    assert "__pycache__" in dockerignore_content
