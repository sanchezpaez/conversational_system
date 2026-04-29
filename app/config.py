import os
from pathlib import Path

from dotenv import load_dotenv

from app.exceptions import ConfigurationError


def load_environment() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=False)


def get_openai_api_key() -> str:
    load_environment()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ConfigurationError("OPENAI_API_KEY is not set. Add it to .env.")
    return api_key


def get_memory_backend() -> str:
    load_environment()
    return os.getenv("MEMORY_BACKEND", "memory").lower()


def get_sqlite_db_path() -> str:
    load_environment()
    return os.getenv("SQLITE_DB_PATH", "data/conversation_state.db")


def get_chat_api_key() -> str:
    load_environment()
    api_key = os.getenv("CHAT_API_KEY")
    if not api_key:
        raise ConfigurationError("CHAT_API_KEY is not set. Add it to .env.")
    return api_key