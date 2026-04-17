import logging

from fastapi import FastAPI, HTTPException

from app.agent import SupportAgent
from app.config import load_environment
from app.exceptions import ConfigurationError
from app.llm import LLMClient
from app.models import ChatRequest, ChatResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
load_environment()

app = FastAPI(title="Customer Support AI Agent Prototype")


def build_agent() -> SupportAgent:
    llm_client = LLMClient()
    return SupportAgent(llm_client=llm_client)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        agent = build_agent()
        return agent.process(request.message)
    except ConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail="Service not configured: OPENAI_API_KEY is missing in .env.",
        ) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Internal processing error.") from error
