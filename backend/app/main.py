from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import account, assistant, cards, explore, lessons, places, practice, trips, tts
from app.core.config import get_settings
from app.services.ai.base import AIError

log = logging.getLogger("bindu")


def _error(status_code: int, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"error": {"code": status_code, "message": message}}, status_code=status_code, headers=headers)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=f"{settings.app_name} API", version="0.1.0", docs_url="/docs", openapi_url="/openapi.json")

    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def reject_oversized(request: Request, call_next):  # noqa: ANN001
        declared = request.headers.get("content-length")
        # Small allowance over the file cap for multipart framing and form fields.
        if declared and declared.isdigit() and int(declared) > get_settings().max_upload_bytes + 1024 * 1024:
            return _error(413, "Request is too large.")
        return await call_next(request)

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):  # noqa: ANN202
        return _error(exc.status_code, str(exc.detail), dict(exc.headers) if exc.headers else None)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):  # noqa: ANN202
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        return _error(422, f"Invalid request{': ' + loc if loc else ''}.")

    @app.exception_handler(AIError)
    async def ai_error(_: Request, exc: AIError):  # noqa: ANN202
        # Internal detail goes to logs only; users get the safe public message.
        log.warning("AI error %s: %s", type(exc).__name__, exc)
        return _error(exc.status_code, exc.public_message)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name, "env": settings.app_env, "ai_provider": settings.ai_provider}

    app.include_router(explore.router, prefix=settings.api_v1_prefix)
    app.include_router(lessons.router, prefix=settings.api_v1_prefix)
    for r in (trips.router, places.router, practice.router, assistant.router, cards.router, account.router, tts.router):
        app.include_router(r, prefix=settings.api_v1_prefix)
    return app


app = create_app()
