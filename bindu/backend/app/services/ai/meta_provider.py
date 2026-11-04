"""Meta Model API provider (Muse Spark). This is BINDU's only real AI provider.

Powers every AI feature: Explore with AI (photo analysis + follow-ups), Ask BINDU (chat) and postcard captions.

Verified against the official docs (https://dev.meta.ai/docs):
- Chat Completions: POST {base}/chat/completions, `Authorization: Bearer <key>`, base https://api.meta.ai/v1
- Images go in `user` messages as `{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}`
- `developer` role carries system instructions; `max_completion_tokens` caps output
- Muse Spark always reasons; reasoning tokens count against the output cap, so the cap is generous
  (`META_MAX_OUTPUT_TOKENS`) and `reasoning_effort` defaults to "low" (`META_REASONING_EFFORT`)
- Structured output: `response_format={"type":"json_schema","json_schema":{"name":..., "schema":...}}`
- Model ids come from config (default `muse-spark-1.3`, Standard mode); nothing here is hard-wired to a model.

Not exercised against the live API from this repo (no key available there): request/response handling is covered by
tests against a mocked HTTP transport only. Run `python scripts/check_meta.py` (see README) with your key to verify.
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
from app.services.ai import prompts
from app.services.ai.base import (
    AIError, AINotConfiguredError, AIOutputError, AIProvider, AIRateLimitedError, AIResponseError, AITimeoutError,
    AIUnavailableError,
)

log = logging.getLogger("bindu.ai.meta")
T = TypeVar("T", bound=BaseModel)
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


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


def _clamp(value: Any, schema: dict[str, Any]) -> Any:
    """Trim model output to the schema's length limits instead of rejecting the whole answer.

    LLMs often return 9 observations when the limit is 8, or a slightly long paragraph. That is harmless, so we cut
    it down (strings to maxLength, lists to maxItems). Wrong types, missing fields and bad enums still fail validation.
    """
    if "anyOf" in schema:
        branches = [b for b in schema["anyOf"] if b.get("type") != "null"]
        return _clamp(value, branches[0]) if branches and value is not None else value
    if isinstance(value, str) and schema.get("type") == "string":
        limit = schema.get("maxLength")
        return value.strip()[:limit].rstrip() if limit else value.strip()
    if isinstance(value, list) and schema.get("type") == "array":
        items = schema.get("items", {})
        limit = schema.get("maxItems")
        return [_clamp(v, items) for v in (value[:limit] if limit else value)]
    if isinstance(value, dict) and schema.get("type") == "object":
        props = schema.get("properties", {})
        return {k: _clamp(v, props[k]) if k in props else v for k, v in value.items()}
    return value


class MetaProvider(AIProvider):
    name = "meta"

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not settings.meta_api_key:
            raise AINotConfiguredError("META_API_KEY is not set")
        self._s = settings
        self._transport = transport
        self.model = settings.meta_model_name

    # ------------------------------------------------------------------ transport

    def _body(self, messages: list[dict[str, Any]], schema_name: str, schema_model: type[BaseModel], structured: bool) -> dict[str, Any]:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "max_completion_tokens": self._s.meta_max_output_tokens}
        if self._s.meta_reasoning_effort:
            body["reasoning_effort"] = self._s.meta_reasoning_effort
        if structured:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "schema": inline_schema(schema_model)},
            }
        return body

    async def _post(self, body: dict[str, Any]) -> httpx.Response:
        url = f"{self._s.meta_api_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self._s.meta_api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self._s.ai_request_timeout_seconds, transport=self._transport) as client:
                return await client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise AITimeoutError("Meta API timed out") from exc
        except httpx.TransportError as exc:
            raise AIUnavailableError(f"Meta API unreachable: {type(exc).__name__}") from exc

    @staticmethod
    def _error_text(resp: httpx.Response) -> str:
        """Meta's own error message (describes what it disliked; never echoes our request body)."""
        try:
            err = resp.json().get("error", {})
            return str(err.get("message") if isinstance(err, dict) else err)[:300]
        except (ValueError, AttributeError):
            return resp.text[:200]

    async def _chat(self, messages: list[dict[str, Any]], schema_name: str, schema_model: type[BaseModel]) -> str:
        structured = self._s.meta_structured_output
        resp = await self._post(self._body(messages, schema_name, schema_model, structured))
        if resp.status_code == 400 and structured:
            # Some model versions/tiers may not accept json_schema. The system prompts already demand JSON and the result
            # is validated by pydantic either way, so degrade gracefully instead of failing the user's request.
            log.warning("Meta API rejected structured output (400: %s); retrying with prompt-only JSON", self._error_text(resp))
            resp = await self._post(self._body(messages, schema_name, schema_model, False))

        # Never log request bodies (they contain user photos) or the API key.
        if resp.status_code == 429:
            raise AIRateLimitedError("Meta API rate limit")
        if resp.status_code in (401, 403):
            log.warning("Meta API auth/permission error %s: %s", resp.status_code, self._error_text(resp))
            raise AINotConfiguredError("Meta API rejected the credentials")
        if resp.status_code == 504:
            raise AITimeoutError("Meta API gateway timeout")
        if resp.status_code >= 500:
            log.warning("Meta API server error %s: %s", resp.status_code, self._error_text(resp))
            raise AIUnavailableError(f"Meta API error {resp.status_code}")
        if resp.status_code >= 400:
            log.warning("Meta API rejected request: status=%s detail=%s", resp.status_code, self._error_text(resp))
            raise AIResponseError(f"Meta API rejected the request ({resp.status_code})")

        try:
            choice = resp.json()["choices"][0]
            content = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIResponseError("Unexpected Meta API response shape") from exc
        if choice.get("finish_reason") == "length":
            # Reasoning ate the budget (content is usually null here). Raise META_MAX_OUTPUT_TOKENS or lower the effort.
            raise AIResponseError("Model output was truncated (increase META_MAX_OUTPUT_TOKENS)")
        if not isinstance(content, str) or not content.strip():
            raise AIOutputError("Empty model output")
        return content

    # ------------------------------------------------------------------ parsing

    @staticmethod
    def _parse(content: str, model: type[T]) -> T:
        try:
            data = json.loads(_FENCE.sub("", content.strip()))
        except ValueError as exc:
            log.warning("Meta output was not JSON (first 80 chars: %r)", content.strip()[:80])
            raise AIOutputError("Model output was not valid JSON") from exc
        if isinstance(data, dict):
            data = _clamp(data, inline_schema(model))
        try:
            return model.model_validate(data)
        except ValidationError as exc:
            # Optional extras (e.g. the Nepali phrase card) must never sink an otherwise good answer: drop them and retry.
            bad = {str(e["loc"][0]) for e in exc.errors() if e["loc"]}
            optional = {f for f in bad if f in model.model_fields and not model.model_fields[f].is_required()}
            if optional and isinstance(data, dict):
                log.warning("Meta output: dropping invalid optional field(s) %s", sorted(optional))
                try:
                    return model.model_validate({k: v for k, v in data.items() if k not in optional})
                except ValidationError as exc2:
                    exc = exc2
            # Field paths and error types only: never the content, which can describe a user's photo.
            log.warning("Meta output failed validation: %s", [(".".join(map(str, e["loc"])), e["type"]) for e in exc.errors()])
            raise AIOutputError("Model output did not match the expected schema") from exc

    async def _complete(self, messages: list[dict[str, Any]], name: str, model: type[T]) -> T:
        """One model call, parsed and validated. A malformed/empty answer gets exactly one retry, then a clean 502."""
        try:
            return self._parse(await self._chat(messages, name, model), model)
        except AIOutputError as exc:
            log.warning("Meta output unusable (%s); retrying once", exc)
            return self._parse(await self._chat(messages, name, model), model)

    # ------------------------------------------------------------------ features

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
        return await self._complete(messages, "CulturalAnalysis", CulturalAnalysis)

    async def answer_question(self, question: str, context_title: str, context_summary: str) -> AskAnswer:
        context = f"Earlier analysis — {context_title}: {context_summary}".strip() if (context_title or context_summary) else "No earlier analysis."
        messages = [
            {"role": "developer", "content": prompts.ASK_SYSTEM},
            {"role": "user", "content": f"{context}\n\nFollow-up question: {question}"},
        ]
        return await self._complete(messages, "AskAnswer", AskAnswer)

    async def chat(self, messages: list[ChatMessage]) -> AssistantAnswer:
        convo: list[dict[str, Any]] = [{"role": "developer", "content": prompts.ASSISTANT_SYSTEM}]
        convo += [{"role": m.role, "content": m.content} for m in messages]
        return await self._complete(convo, "AssistantAnswer", AssistantAnswer)

    async def generate_visual_content(self, req: CardRequest) -> VisualCard:
        user = f"Card kind: {req.kind}\nTitle: {req.title}\nDetails: {req.body}\nNepali: {req.nepali}\nEnglish: {req.english}"
        messages = [{"role": "developer", "content": prompts.CARD_SYSTEM}, {"role": "user", "content": user}]
        return await self._complete(messages, "VisualCard", VisualCard)


__all__ = ["MetaProvider", "inline_schema", "AIError"]
