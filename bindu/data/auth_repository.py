#independed user

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from bindu.data.local_cache import LocalCache

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    error: str | None = None
    username: str | None = None
    display_name: str | None = None


class AuthRepository:
    def __init__(self, cache: LocalCache):
        self.cache = cache

    def sign_up(self, username: str, password: str, display_name: str = "") -> AuthResult:
        username = username.strip()
        display_name = display_name.strip() or username

        if not USERNAME_RE.match(username):
            return AuthResult(False, error=(
                "Username must be 3-32 characters: letters, numbers, '.', '_' or '-'."
            ))
        if len(password) < 4:
            return AuthResult(False, error="Password must be at least 4 characters.")
        if self.cache.get_user(username) is not None:
            return AuthResult(False, error="That username is already taken.")

        salt = os.urandom(16).hex()
        password_hash = _hash_password(password, salt)
        self.cache.create_user(
            username=username,
            password_hash=password_hash,
            salt=salt,
            display_name=display_name,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return AuthResult(True, username=username, display_name=display_name)

    def log_in(self, username: str, password: str) -> AuthResult:
        username = username.strip()
        row = self.cache.get_user(username)
        if row is None:
            return AuthResult(False, error="No account with that username — sign up first.")
        if _hash_password(password, row["salt"]) != row["password_hash"]:
            return AuthResult(False, error="Incorrect password.")
        return AuthResult(True, username=username, display_name=row["display_name"] or username)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
