from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_provider
from app.core.ratelimit import ai_rate_limit
from app.schemas.assistant import AssistantRequest, AssistantResponse
from app.services.ai.base import AIProvider

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantResponse, dependencies=[Depends(ai_rate_limit)])
async def chat(body: AssistantRequest, provider: Annotated[AIProvider, Depends(get_provider)]) -> AssistantResponse:
    """Stateless chat: the app sends the recent messages each time; nothing is stored on the server."""
    if body.messages[-1].role != "user":
        from fastapi import HTTPException
        raise HTTPException(422, "The last message must be from the user.")
    answer = await provider.chat(body.messages)
    return AssistantResponse(result=answer, provider=provider.name, model=provider.model, is_mock=provider.is_mock)
