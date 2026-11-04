from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class AssistantRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=12)


class AssistantAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=2500)
    confidence: Confidence = "medium"
    needs_verification: bool = True
    followups: list[str] = Field(default_factory=list, max_length=3)


class AssistantResponse(BaseModel):
    result: AssistantAnswer
    provider: str
    model: str
    is_mock: bool
