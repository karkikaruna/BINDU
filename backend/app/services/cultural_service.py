"""Cultural Explorer service: validates uploads, looks up curated notes, and calls the AI provider."""
from __future__ import annotations

import io
import json
import re
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.schemas.explore import AnalyzeResponse, AskRequest, AskResponse, SourceRef
from app.services.ai.base import AIProvider

DATA = Path(__file__).resolve().parent.parent / "data"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
PIL_FORMAT_TO_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
MAX_SIDE_PX = 1568  # enough detail for carvings; keeps payload small
MAX_PIXELS = 40_000_000  # decompression-bomb guard
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


@lru_cache
def curated_places() -> list[dict]:
    return json.loads((DATA / "curated_places.json").read_text(encoding="utf-8"))["places"]


def find_curated(*texts: str | None) -> dict | None:
    """Match a curated place by name/alias mentioned in the user's hint or question (whole-word, case-insensitive)."""
    haystack = " ".join(t for t in texts if t).lower()
    if not haystack:
        return None
    for place in curated_places():
        for needle in [place["name"], *place["aliases"]]:
            if re.search(rf"(?<!\w){re.escape(needle.lower())}(?!\w)", haystack):
                return place
    return None


def prepare_image(raw: bytes, declared_type: str | None, max_bytes: int) -> bytes:
    """Validate by decoding (extension and header are not trusted), then normalise to a bounded JPEG.

    Re-encoding also strips EXIF metadata such as GPS coordinates before anything leaves our server.
    """
    if declared_type not in ALLOWED_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only JPEG, PNG or WebP images are supported.")
    if len(raw) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The image is empty.")
    if len(raw) > max_bytes:
        raise HTTPException(413, f"Image is larger than {max_bytes // (1024 * 1024)} MB.")
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            actual = PIL_FORMAT_TO_MIME.get(probe.format or "")
            probe.verify()
        if actual is None or actual != declared_type:
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File content does not match its declared image type.")
        with Image.open(io.BytesIO(raw)) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
            if img.mode not in ("RGB",):
                img = img.convert("RGB")
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=85)
            return out.getvalue()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError, ValueError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That file could not be read as an image.") from None


class CulturalService:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    async def analyze(self, image_jpeg: bytes, question: str | None, place_hint: str | None) -> AnalyzeResponse:
        curated = find_curated(place_hint, question)
        analysis = await self.provider.analyze_image(image_jpeg, question, curated["notes"] if curated else None)
        sources: list[SourceRef] = []
        if curated:
            sources.append(SourceRef(name=curated["source_name"], url=curated["source_url"]))
            # Only claims grounded in curated notes may drop the verification flag; the model is told this,
            # but we enforce the conservative side: no curated match -> always needs verification.
        else:
            analysis.cultural_context.needs_verification = True
        return AnalyzeResponse(
            analysis=analysis, sources=sources, provider=self.provider.name, model=self.provider.model, is_mock=self.provider.is_mock,
        )

    async def ask(self, req: AskRequest) -> AskResponse:
        result = await self.provider.answer_question(req.question, req.context_title, req.context_summary)
        return AskResponse(result=result, provider=self.provider.name, model=self.provider.model, is_mock=self.provider.is_mock)
