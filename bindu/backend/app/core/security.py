"""Authentication.

The mobile app signs in with Supabase Auth and sends the access token as `Authorization: Bearer <jwt>`.
The user id is ALWAYS taken from verified token claims, never from a request body.

`AUTH_MODE=dev` (refused in production) accepts `Bearer dev-<name>` so the app can be exercised without a
Supabase project. Guests (no header) are allowed only on endpoints that use `optional_user`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class AuthUser:
    id: str
    is_dev: bool = False


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def _signing_key(token: str, settings: Settings):
    """HS256 uses the project JWT secret; asymmetric keys are fetched from the project's JWKS endpoint."""
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise _unauthorized("Server auth is not configured")
        return settings.supabase_jwt_secret, ["HS256"]
    if alg in ("ES256", "RS256") and settings.supabase_url:
        client = jwt.PyJWKClient(f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json", cache_keys=True)
        return client.get_signing_key_from_jwt(token).key, [alg]
    raise _unauthorized("Unsupported token")


def verify_token(token: str, settings: Settings) -> AuthUser:
    if settings.auth_mode == "dev":
        if token.startswith("dev-") and len(token) > 4:
            return AuthUser(id=token, is_dev=True)
        raise _unauthorized("Invalid development token")
    try:
        key, algs = _signing_key(token, settings)
        claims = jwt.decode(token, key, algorithms=algs, audience="authenticated", options={"require": ["exp", "sub"]})
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expired") from None
    except jwt.PyJWTError:
        raise _unauthorized("Invalid token") from None
    return AuthUser(id=str(claims["sub"]))


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized("Malformed Authorization header")
    return token.strip()


def optional_user(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> AuthUser | None:
    token = _extract_bearer(authorization)
    return verify_token(token, settings) if token else None


def require_user(user: AuthUser | None = Depends(optional_user)) -> AuthUser:
    if user is None:
        raise _unauthorized("Sign in required")
    return user
