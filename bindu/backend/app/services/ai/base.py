"""Provider-agnostic AI interface (README section 9).

The mobile app only ever talks to the BINDU API, so the model behind this layer can change freely.
Operations a provider does not implement raise AIUnsupportedError; they never fall back silently.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.assistant import AssistantAnswer, ChatMessage
from app.schemas.cards import CardRequest, VisualCard
from app.schemas.explore import AskAnswer, CulturalAnalysis


class AIError(Exception):
    """Base error. `public_message` is safe to show to end users."""

    status_code = 502
    public_message = "The AI service had a problem. Please try again."


class AIUnavailableError(AIError):
    status_code = 503
    public_message = "The AI service is unavailable right now. Please try again shortly."


class AITimeoutError(AIError):
    status_code = 504
    public_message = "The AI service took too long to respond. Please try again."


class AIRateLimitedError(AIError):
    status_code = 429
    public_message = "The AI service is busy. Please wait a moment and try again."


class AINotConfiguredError(AIError):
    status_code = 503
    public_message = "AI is not configured on this server."


class AIResponseError(AIError):
    status_code = 502
    public_message = "The AI returned an answer we could not use. Please try again."


class AIOutputError(AIResponseError):
    """The model answered, but with empty or schema-invalid output. Worth one retry; never shown to the user."""


class AIUnsupportedError(AIError):
    status_code = 501
    public_message = "This AI feature is not implemented yet."


class AIProvider(ABC):
    name: str
    model: str
    is_mock: bool = False

    @abstractmethod
    async def analyze_image(
        self, image_jpeg: bytes, question: str | None, source_notes: str | None
    ) -> CulturalAnalysis: ...

    @abstractmethod
    async def answer_question(self, question: str, context_title: str, context_summary: str) -> AskAnswer: ...

    @abstractmethod
    async def chat(self, messages: list[ChatMessage]) -> AssistantAnswer: ...

    @abstractmethod
    async def generate_visual_content(self, req: CardRequest) -> VisualCard: ...
