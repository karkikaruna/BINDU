"""Meta Model API provider.

Verified against the official docs (https://dev.meta.ai/docs):
- Chat Completions: POST {base}/chat/completions, `Authorization: Bearer <key>`, base https://api.meta.ai/v1
- Images go in `user` messages as `{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}`
- `developer` role carries system instructions; `max_completion_tokens` caps output
- Structured output: `response_format={"type":"json_schema","json_schema":{"name":..., "schema":...}}`
- Model ids come from config (default `muse-spark-1.3`); nothing here is hard-wired to a model.

NOT verified live: this repo has no API key, so the request/response handling is covered by tests against a
mocked HTTP transport only.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.schemas.assistant import AssistantAnswer, ChatMessage
from app.schemas.cards import CardRequest, VisualCard
from app.schemas.explore import AskAnswer, CulturalAnalysis
from app.schemas.practice import Evaluation, EvaluateRequest, PracticeRequest, PracticeSet
from app.schemas.trips import Itinerary, TripRequest
from app.services.ai import prompts
from app.services.ai.base import (
    AIError, AINotConfiguredError, AIProvider, AIRateLimitedError, AIResponseError, AITimeoutError, AIUnavailableError,
)

log = logging.getLogger("bindu.ai.meta")
T = TypeVar("T", bound=BaseModel)
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
MAX_OUTPUT_TOKENS = 2000


def inline_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Pydantic JSON schema with $defs inlined (the API rejects recursive schemas; ours has none)."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(defs[node["$ref"].rsplit("/", 1)[-1]])
            return {k: resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schema)


class MetaProvider(AIProvider):
    name = "meta"

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not settings.meta_api_key:
            raise AINotConfiguredError("META_API_KEY is not set")
        self._s = settings
        self._transport = transport
        self.model = settings.meta_model_name

    async def _chat(self, messages: list[dict[str, Any]], schema_name: str, schema_model: type[BaseModel]) -> str:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "max_completion_tokens": MAX_OUTPUT_TOKENS}
        if self._s.meta_structured_output:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "schema": inline_schema(schema_model)},
            }
        url = f"{self._s.meta_api_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self._s.meta_api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self._s.ai_request_timeout_seconds, transport=self._transport) as client:
                resp = await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise AITimeoutError("Meta API timed out") from exc
        except httpx.TransportError as exc:
            raise AIUnavailableError(f"Meta API unreachable: {type(exc).__name__}") from exc

        # Never log request bodies (they contain user photos) or the API key.
        if resp.status_code == 429:
            raise AIRateLimitedError("Meta API rate limit")
        if resp.status_code in (401, 403):
            raise AINotConfiguredError("Meta API rejected the credentials")
        if resp.status_code == 504:
            raise AITimeoutError("Meta API gateway timeout")
        if resp.status_code >= 500:
            raise AIUnavailableError(f"Meta API error {resp.status_code}")
        if resp.status_code >= 400:
            log.warning("Meta API rejected request: status=%s", resp.status_code)
            raise AIResponseError(f"Meta API rejected the request ({resp.status_code})")

        try:
            choice = resp.json()["choices"][0]
            content = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIResponseError("Unexpected Meta API response shape") from exc
        if choice.get("finish_reason") == "length":
            raise AIResponseError("Model output was truncated")
        if not isinstance(content, str) or not content.strip():
            raise AIResponseError("Empty model output")
        return content

    @staticmethod
    def _parse(content: str, model: type[T]) -> T:
        try:
            return model.model_validate(json.loads(_FENCE.sub("", content.strip())))
        except (ValueError, ValidationError) as exc:
            raise AIResponseError("Model output did not match the expected schema") from exc

    async def analyze_image(self, image_jpeg: bytes, question: str | None, source_notes: str | None) -> CulturalAnalysis:
        data_url = "data:image/jpeg;base64," + base64.b64encode(image_jpeg).decode("ascii")
        messages = [
            {"role": "developer", "content": prompts.EXPLORER_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompts.explorer_user_text(question, source_notes)},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ]
        return self._parse(await self._chat(messages, "CulturalAnalysis", CulturalAnalysis), CulturalAnalysis)

    async def answer_question(self, question: str, context_title: str, context_summary: str) -> AskAnswer:
        context = f"Earlier analysis — {context_title}: {context_summary}".strip() if (context_title or context_summary) else "No earlier analysis."
        messages = [
            {"role": "developer", "content": prompts.ASK_SYSTEM},
            {"role": "user", "content": f"{context}\n\nFollow-up question: {question}"},
        ]
        return self._parse(await self._chat(messages, "AskAnswer", AskAnswer), AskAnswer)


    async def _text_call(self, system: str, user: str, name: str, model: type[T]) -> T:
        messages = [{"role": "developer", "content": system}, {"role": "user", "content": user}]
        return self._parse(await self._chat(messages, name, model), model)

    async def generate_itinerary(self, req: TripRequest, known_places: list[str]) -> Itinerary:
        user = prompts.itinerary_user_text(req, known_places)
        result = await self._text_call(prompts.ITINERARY_SYSTEM, user, "Itinerary", Itinerary)
        if len(result.days) != req.days:
            raise AIResponseError("Itinerary day count did not match the request")
        return result

    async def generate_language_practice(self, req: PracticeRequest) -> PracticeSet:
        user = f"Topic: {req.topic}\nLearner level: {req.level}\nNumber of items: {req.count}"
        result = await self._text_call(prompts.PRACTICE_SYSTEM, user, "PracticeSet", PracticeSet)
        return PracticeSet(items=result.items[: req.count])

    async def evaluate_language_response(self, req: EvaluateRequest) -> Evaluation:
        user = f"English prompt: {req.prompt_en}\nExpected Nepali: {req.expected_nepali}\nLearner answer: {req.user_answer}"
        return await self._text_call(prompts.EVALUATE_SYSTEM, user, "Evaluation", Evaluation)

    async def chat(self, messages: list[ChatMessage]) -> AssistantAnswer:
        convo = [{"role": "developer", "content": prompts.ASSISTANT_SYSTEM}]
        convo += [{"role": m.role, "content": m.content} for m in messages]
        return self._parse(await self._chat(convo, "AssistantAnswer", AssistantAnswer), AssistantAnswer)

    async def generate_visual_content(self, req: CardRequest) -> VisualCard:
        user = f"Card kind: {req.kind}\nTitle: {req.title}\nDetails: {req.body}\nNepali: {req.nepali}\nEnglish: {req.english}"
        return await self._text_call(prompts.CARD_SYSTEM, user, "VisualCard", VisualCard)


__all__ = ["MetaProvider", "inline_schema", "AIError"]
