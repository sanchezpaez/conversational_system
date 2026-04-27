from typing import Literal

from pydantic import BaseModel, Field


IntentName = Literal["order_status", "change_booking", "fallback"]
LanguageCode = Literal["en", "es"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = Field(default=None, min_length=1)


class IntentDecision(BaseModel):
    intent: IntentName


class EntityExtraction(BaseModel):
    order_id: str | None = None
    date: str | None = None


class SessionMetrics(BaseModel):
    turns_to_resolution: int | None = None
    clarification_rate: float
    success_rate: float


class ChatResponse(BaseModel):
    intent: IntentName
    entities: EntityExtraction
    backend_result: dict
    reply: str
    metrics: SessionMetrics | None = None
    language: LanguageCode | None = None
