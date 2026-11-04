import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.core.config import Settings
from app.core.security import verify_token
from tests.conftest import make_settings

SECRET = "x" * 40


def token(secret=SECRET, **claims):
    payload = {"sub": "user-123", "aud": "authenticated", "exp": int(time.time()) + 600, **claims}
    return jwt.encode({k: v for k, v in payload.items() if v is not None}, secret, algorithm="HS256")


S = lambda **kw: make_settings(auth_mode="supabase", supabase_jwt_secret=SECRET, **kw)  # noqa: E731


def test_valid_supabase_token():
    assert verify_token(token(), S()).id == "user-123"


@pytest.mark.parametrize("bad", [
    token(secret="y" * 40),                 # wrong signature
    token(exp=int(time.time()) - 5),         # expired
    token(aud="anon"),                       # wrong audience
    token(sub=None),                         # missing sub
    "not-a-jwt",
])
def test_rejected_tokens(bad):
    with pytest.raises(HTTPException) as e:
        verify_token(bad, S())
    assert e.value.status_code == 401


def test_alg_none_is_rejected():
    forged = jwt.encode({"sub": "u", "aud": "authenticated", "exp": int(time.time()) + 60}, key=None, algorithm="none")
    with pytest.raises(HTTPException):
        verify_token(forged, S())


def test_missing_secret_is_401_not_500():
    with pytest.raises(HTTPException) as e:
        verify_token(token(), make_settings(auth_mode="supabase", supabase_jwt_secret=""))
    assert e.value.status_code == 401


def test_asymmetric_token_via_jwks(monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    tok = jwt.encode({"sub": "u9", "aud": "authenticated", "exp": int(time.time()) + 60}, key, algorithm="ES256", headers={"kid": "k1"})

    class FakeClient:
        def __init__(self, *a, **k): pass
        def get_signing_key_from_jwt(self, _):
            return type("K", (), {"key": key.public_key()})()

    monkeypatch.setattr(jwt, "PyJWKClient", FakeClient)
    s = make_settings(auth_mode="supabase", supabase_url="https://x.supabase.co")
    assert verify_token(tok, s).id == "u9"


def test_dev_mode_and_production_guard():
    assert verify_token("dev-kk", make_settings()).is_dev
    with pytest.raises(HTTPException):
        verify_token("kk", make_settings())
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_env="production", auth_mode="dev")


def test_header_handling_via_api(make_client):
    c = make_client(S())
    # Guests are allowed on analyze; a present-but-invalid token is rejected rather than treated as guest.
    r = c.post("/api/v1/explore/ask", json={"question": "hi there"}, headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401 and r.json()["error"]["code"] == 401
    r = c.post("/api/v1/explore/ask", json={"question": "hi there"}, headers={"Authorization": "Basic abc"})
    assert r.status_code == 401
    r = c.post("/api/v1/explore/ask", json={"question": "hi there"}, headers={"Authorization": f"Bearer {token()}"})
    assert r.status_code == 200
