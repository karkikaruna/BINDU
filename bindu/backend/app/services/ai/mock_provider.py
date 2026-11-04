"""Deterministic provider for local development and automated tests.

Everything it returns is labelled `provider="mock"`, `is_mock=true` end to end so it can never be mistaken
for a real model answer. It does not look at the image content.
"""
from __future__ import annotations

from app.schemas.assistant import AssistantAnswer, ChatMessage
from app.schemas.cards import CardRequest, VisualCard
from app.schemas.explore import AskAnswer, CulturalAnalysis, CulturalContext, NepaliPhrase
from app.services.ai.base import AIProvider


class MockProvider(AIProvider):
    name = "mock"
    model = "mock-explorer-1"
    is_mock = True

    async def analyze_image(self, image_jpeg: bytes, question: str | None, source_notes: str | None) -> CulturalAnalysis:
        return CulturalAnalysis(
            title="Demo result (mock AI)",
            observations=[
                "This is a placeholder response; the image was not analyzed.",
                f"Received an image of {len(image_jpeg)} bytes after validation.",
            ],
            identified_place=None,
            identification_confidence="low",
            cultural_context=CulturalContext(
                text="Mock mode is on. Set AI_PROVIDER=meta and META_API_KEY to get real analysis."
                + (f" Curated notes were available: {source_notes[:200]}" if source_notes else ""),
                confidence="low",
                needs_verification=True,
            ),
            related_places=["Patan Durbar Square"],
            suggested_activities=["Walk the square slowly and look up at the window carvings."],
            phrase=NepaliPhrase(
                nepali="यो के हो?", romanization="Yo ke ho?", english="What is this?",
                usage="Point at an object or carving and ask this politely.",
            ),
        )

    async def answer_question(self, question: str, context_title: str, context_summary: str) -> AskAnswer:
        return AskAnswer(answer=f"(mock) You asked: {question}", confidence="low", needs_verification=True)

    async def chat(self, messages: list[ChatMessage]) -> AssistantAnswer:
        last = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return AssistantAnswer(
            answer=f"(mock) You asked: {last}", confidence="low", needs_verification=True,
            followups=["What should I wear at a temple?", "How do I say thank you in Nepali?"],
        )

    async def generate_visual_content(self, req: CardRequest) -> VisualCard:
        return VisualCard(
            headline=req.title[:80], caption=(req.body or "A moment from Nepal.")[:250] if req.body else "A moment from Nepal. (mock caption)",
            nepali=req.nepali, english=req.english, romanization="", theme="forest",
        )
