"""Account deletion (required by the App Store and Google Play for apps that offer sign-up).

Deleting the Supabase auth user cascades to profiles, progress, discoveries and trips
(`on delete cascade` in supabase/migrations/0001_init.sql), so nothing about the person is left behind.
The service-role key stays on the server and is only used for this call.
"""
from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings
from app.core.security import AuthUser

log = logging.getLogger("bindu.account")


async def delete_account(user: AuthUser, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
    if user.is_dev:
        return  # development tokens have no remote account to remove
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Account deletion is not configured on this server.")
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{user.id}"
    headers = {"apikey": settings.supabase_service_role_key, "Authorization": f"Bearer {settings.supabase_service_role_key}"}
    try:
        async with httpx.AsyncClient(timeout=15, transport=transport) as client:
            resp = await client.delete(url, headers=headers)
    except httpx.HTTPError as exc:
        log.warning("Account deletion transport error: %s", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Couldn't reach the account service. Please try again.") from exc
    if resp.status_code == 404:
        return  # already gone: deleting twice is fine
    if resp.status_code >= 400:
        log.warning("Account deletion rejected: status=%s", resp.status_code)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The account could not be deleted. Please try again.")
