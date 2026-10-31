"""Deterministic provider for local development and automated tests.

Everything it returns is labelled `provider="mock"`, `is_mock=true` end to end so it can never be mistaken
for a real model answer. It does not look at the image content.
"""
from __future__ import annotations

import difflib

from app.schemas.assistant import AssistantAnswer, ChatMessage
from app.schemas.cards import CardRequest, VisualCard
from app.schemas.explore import AskAnswer, CulturalAnalysis, CulturalContext, NepaliPhrase
from app.schemas.practice import Evaluation, EvaluateRequest, PracticeItem, PracticeRequest, PracticeSet
from app.schemas.trips import Itinerary, ItineraryDay, Stop, TripRequest
from app.services.ai.base import AIProvider

_STOPS_PER_DAY = {"relaxed": 2, "balanced": 3, "packed": 5}
_SLOTS = ["morning", "afternoon", "evening", "morning", "afternoon"]
_BANK = [
    PracticeItem(prompt_en="Hello / greetings", expected_nepali="नमस्ते", romanization="Namaste", hint="Used any time of day."),
    PracticeItem(prompt_en="Thank you", expected_nepali="धन्यवाद", romanization="Dhanyabad", hint="Polite thanks."),
    PracticeItem(prompt_en="How much is this?", expected_nepali="यो कति हो?", romanization="Yo kati ho?", hint="Point at the item."),
    PracticeItem(prompt_en="Where is the toilet?", expected_nepali="शौचालय कहाँ छ?", romanization="Shauchalaya kahan cha?", hint="Useful everywhere."),
    PracticeItem(prompt_en="Water, please", expected_nepali="पानी दिनुहोस्", romanization="Pani dinuhos", hint="'Dinuhos' is the polite 'please give'."),
]


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

    async def generate_itinerary(self, req: TripRequest, known_places: list[str]) -> Itinerary:
        per_day = _STOPS_PER_DAY[req.pace]
        pool = known_places or [f"{req.destination} town centre"]
        days = []
        for d in range(req.days):
            stops = []
            for i in range(per_day):
                name = pool[(d * per_day + i) % len(pool)]
                stops.append(Stop(name=name, slot=_SLOTS[i % len(_SLOTS)], description="(mock) Placeholder stop; not a real recommendation.", category="sightseeing", tip="Dress modestly at religious sites."))
            days.append(ItineraryDay(day_number=d + 1, title=f"Day {d + 1} in {req.destination}", stops=stops))
        return Itinerary(
            title=f"{req.days}-day {req.destination} (mock plan)",
            summary="Demo itinerary from the mock provider. Set AI_PROVIDER=meta for a real plan.",
            days=days,
            tips=["Carry some cash in small notes.", "Ask before photographing people or inside shrines."],
        )

    async def generate_language_practice(self, req: PracticeRequest) -> PracticeSet:
        return PracticeSet(items=_BANK[: req.count])

    async def evaluate_language_response(self, req: EvaluateRequest) -> Evaluation:
        ratio = difflib.SequenceMatcher(None, req.user_answer.strip().lower(), req.expected_nepali.strip().lower()).ratio()
        score = round(ratio * 100)
        ok = score >= 70
        return Evaluation(
            correct=ok, score=score,
            feedback="(mock) Close enough." if ok else "(mock) Not quite. Compare with the expected answer.",
            corrected="" if ok else req.expected_nepali,
        )

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
