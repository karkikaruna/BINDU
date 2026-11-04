"""Client for the Swar Nepali text-to-speech server (see voice.ipynb / Naamche-Labs/swar).

The Swar server exposes `POST /tts {voice_id, text, quality}` -> audio/wav and `GET /voices`.
Everything the app needs goes through TTSService, which adds a disk cache so the same phrase is only
synthesised once (a GPU call is slow and the Colab tunnel is not meant to serve every tap).
"""
from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path

import httpx

from app.core.config import Settings
from app.services.ai.base import AIError, AINotConfiguredError, AITimeoutError, AIUnavailableError

log = logging.getLogger("bindu.tts")


class TTSError(AIError):
    status_code = 502
    public_message = "Speech could not be generated. Please try again."


class SwarClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._base = settings.swar_base_url.rstrip("/")
        self._key = settings.swar_api_key
        self._voice = settings.swar_voice_id
        self._timeout = settings.swar_timeout_seconds
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self._base)

    async def _resolve_voice(self, client: httpx.AsyncClient) -> str:
        """Use SWAR_VOICE_ID if set, otherwise the first preset the server has."""
        if self._voice:
            return self._voice
        r = await client.get(f"{self._base}/voices", headers=self._headers())
        r.raise_for_status()
        presets = r.json().get("presets") or []
        if not presets:
            raise AINotConfiguredError("Swar server has no preset voices; set SWAR_VOICE_ID")
        self._voice = presets[0]
        return self._voice

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._key} if self._key else {}

    async def synthesize(self, text: str, quality: str = "fast") -> bytes:
        if not self.configured:
            raise AINotConfiguredError("SWAR_BASE_URL is not set")
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                voice = await self._resolve_voice(client)
                r = await client.post(f"{self._base}/tts", headers=self._headers(),
                                      json={"voice_id": voice, "text": text, "quality": quality})
        except httpx.TimeoutException as e:
            raise AITimeoutError(f"Swar timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            raise AIUnavailableError(f"Swar /voices returned {e.response.status_code}") from e
        except httpx.HTTPError as e:  # tunnel down, DNS, connection reset...
            raise AIUnavailableError(f"Swar unreachable: {e}") from e
        if r.status_code in (401, 403):
            raise AINotConfiguredError("Swar rejected SWAR_API_KEY")
        if r.status_code >= 400:
            raise TTSError(f"Swar returned {r.status_code}: {r.text[:200]}")
        if not r.content.startswith(b"RIFF"):  # a Cloudflare error page etc. would be HTML
            raise TTSError("Swar did not return WAV audio")
        return r.content


class TTSService:
    def __init__(self, client: SwarClient, settings: Settings) -> None:
        self._client = client
        self._cache = Path(settings.tts_cache_dir)
        self._voice = settings.swar_voice_id or "default"  # stable key, even before the server's preset is resolved

    def _path(self, text: str, quality: str) -> Path:
        key = hashlib.sha1(f"{self._voice}|{quality}|{text}".encode("utf-8")).hexdigest()
        return self._cache / f"{key}.wav"

    async def speak(self, text: str, quality: str = "fast") -> bytes:
        path = self._path(text, quality)
        if path.exists():
            return path.read_bytes()
        audio = await self._client.synthesize(text, quality)
        try:
            self._cache.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self._cache, suffix=".part")
            with os.fdopen(fd, "wb") as f:
                f.write(audio)
            os.replace(tmp, path)  # atomic: a concurrent reader never sees half a file
        except OSError:
            log.warning("could not write TTS cache", exc_info=True)
        return audio
