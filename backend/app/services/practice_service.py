from __future__ import annotations

import re
import unicodedata

from app.schemas.practice import EvaluateRequest, EvaluateResponse, Evaluation, PracticeRequest, PracticeResponse
from app.services.ai.base import AIProvider

_PUNCT = re.compile(r"[\s\u0964.,!?;:'\"()\-]+")  # includes the Devanagari danda


def normalize(text: str) -> str:
    """Compare Nepali answers ignoring spacing, punctuation, danda and Unicode composition differences."""
    return _PUNCT.sub("", unicodedata.normalize("NFC", text)).lower()


class PracticeService:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    async def generate(self, req: PracticeRequest) -> PracticeResponse:
        result = await self.provider.generate_language_practice(req)
        return PracticeResponse(result=result, provider=self.provider.name, model=self.provider.model, is_mock=self.provider.is_mock)

    async def evaluate(self, req: EvaluateRequest) -> EvaluateResponse:
        # Exact matches never need a model, which keeps common cases instant, free and deterministic.
        if normalize(req.user_answer) == normalize(req.expected_nepali):
            return EvaluateResponse(
                result=Evaluation(correct=True, score=100, feedback="Exactly right.", corrected=""),
                method="exact", provider="local", model="exact-match", is_mock=False,
            )
        result = await self.provider.evaluate_language_response(req)
        return EvaluateResponse(result=result, method="ai", provider=self.provider.name, model=self.provider.model, is_mock=self.provider.is_mock)
