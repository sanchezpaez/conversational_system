import logging
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse

from app.agent import SupportAgent
from app.backend import MockBackendClient
from app.backend_real import RealBackendClient
from app.config import (
    get_backend_mode,
    get_chat_api_key,
    get_memory_backend,
    get_real_backend_api_key,
    get_real_backend_base_url,
    get_sqlite_db_path,
    load_environment,
)
from app.conversation_memory import InMemoryConversationMemory
from app.exceptions import ConfigurationError
from app.llm import LLMClient
from app.models import ChatRequest, ChatResponse
from app.sqlite_memory import SQLiteConversationMemory

logging.basicConfig(level=logging.INFO, format="%(message)s")
load_environment()

app = FastAPI(title="Customer Support AI Agent Prototype")
UI_FILE_PATH = Path(__file__).resolve().parent / "ui" / "index.html"


def build_agent() -> SupportAgent:
    llm_client = LLMClient()
    memory_backend = get_memory_backend()
    backend_mode = get_backend_mode()

    # Runtime selection of the session memory backend.
    # If MEMORY_BACKEND=sqlite, agent state is persisted on disk via SQLite.
    if memory_backend == "sqlite":
        memory = SQLiteConversationMemory(db_path=get_sqlite_db_path())
    else:
        # Default backend keeps state only in process memory.
        memory = InMemoryConversationMemory()

    if backend_mode == "real":
        backend_client = RealBackendClient(
            base_url=get_real_backend_base_url(),
            api_key=get_real_backend_api_key(),
        )
    else:
        backend_client = MockBackendClient()

    return SupportAgent(llm_client=llm_client, memory=memory, backend_client=backend_client)


@app.get("/ui", response_class=HTMLResponse)
def ui() -> HTMLResponse:
    html = UI_FILE_PATH.read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> ChatResponse:
    try:
        expected_api_key = get_chat_api_key()
        if x_api_key != expected_api_key:
            raise HTTPException(status_code=401, detail="Unauthorized")

        agent = build_agent()
        return agent.process(request.message, request.session_id)
    except HTTPException as error:
        raise error
    except ConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail="Service not configured: OPENAI_API_KEY is missing in .env.",
        ) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Internal processing error.") from error
