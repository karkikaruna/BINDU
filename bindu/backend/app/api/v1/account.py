from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.security import AuthUser, require_user
from app.services import account_service

router = APIRouter(prefix="/account", tags=["account"])


class DeleteResponse(BaseModel):
    deleted: bool = True


@router.delete("", response_model=DeleteResponse)
async def delete_my_account(
    user: Annotated[AuthUser, Depends(require_user)], settings: Annotated[Settings, Depends(get_settings)]
) -> DeleteResponse:
    """Permanently delete the signed-in user's account and all synced data. The user id comes from the verified token."""
    await account_service.delete_account(user, settings)
    return DeleteResponse()
