import httpx
import pytest
from fastapi import HTTPException

from app.core.security import AuthUser
from app.services import account_service
from tests.conftest import make_settings

API = "/api/v1"
SUPA = dict(auth_mode="dev", supabase_url="https://p.supabase.co", supabase_service_role_key="srv-key")


def test_delete_requires_sign_in(client):
    r = client.delete(f"{API}/account")
    assert r.status_code == 401 and r.json()["error"]["code"] == 401


def test_dev_user_delete_is_a_noop_success(client):
    r = client.delete(f"{API}/account", headers={"Authorization": "Bearer dev-kk"})
    assert r.status_code == 200 and r.json() == {"deleted": True}


@pytest.mark.asyncio
async def test_supabase_admin_delete_uses_token_user_and_service_key():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(method=req.method, url=str(req.url), auth=req.headers["authorization"], apikey=req.headers["apikey"])
        return httpx.Response(200, json={})

    await account_service.delete_account(AuthUser(id="uid-1"), make_settings(**SUPA), httpx.MockTransport(handler))
    assert seen == {"method": "DELETE", "url": "https://p.supabase.co/auth/v1/admin/users/uid-1", "auth": "Bearer srv-key", "apikey": "srv-key"}


@pytest.mark.asyncio
async def test_already_deleted_is_ok_and_failures_are_safe():
    ok = httpx.MockTransport(lambda r: httpx.Response(404, json={}))
    await account_service.delete_account(AuthUser(id="u"), make_settings(**SUPA), ok)
    for status, expected in ((500, 502), (403, 502)):
        with pytest.raises(HTTPException) as e:
            await account_service.delete_account(AuthUser(id="u"), make_settings(**SUPA), httpx.MockTransport(lambda r, s=status: httpx.Response(s, json={"secret": "x"})))
        assert e.value.status_code == expected and "secret" not in e.value.detail


@pytest.mark.asyncio
async def test_unconfigured_and_unreachable():
    with pytest.raises(HTTPException) as e:
        await account_service.delete_account(AuthUser(id="u"), make_settings(auth_mode="dev"))
    assert e.value.status_code == 503

    def boom(req):
        raise httpx.ConnectError("down")

    with pytest.raises(HTTPException) as e:
        await account_service.delete_account(AuthUser(id="u"), make_settings(**SUPA), httpx.MockTransport(boom))
    assert e.value.status_code == 503
