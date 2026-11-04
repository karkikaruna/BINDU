from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class TTSRequest(BaseModel):
    text: str
    quality: Literal["fast", "best"] | None = None  # default comes from SWAR_QUALITY

    @field_validator("text")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("text is empty")
        return v
