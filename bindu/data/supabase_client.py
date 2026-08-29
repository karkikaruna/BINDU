
from __future__ import annotations

import os

from supabase import Client, create_client

_client: Client | None = None


def get_client() -> Client:
    """Lazily creates and caches the Supabase client for this process."""
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set (see .env.example / "
                ".streamlit/secrets.toml.example)."
            )
        _client = create_client(url, key)
    return _client


def load_env_from_streamlit_secrets() -> None:
    """Copies Streamlit secrets into os.environ, if a secrets.toml is present.

    Call this once at app startup, before get_client(). Safe to call even
    when no secrets file exists (e.g. local dev using a plain .env file).
    """
    try:
        import streamlit as st
        for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
            if key in st.secrets and key not in os.environ:
                os.environ[key] = st.secrets[key]
    except Exception:
        # No secrets.toml, or not running inside Streamlit — fall back to
        # whatever's already in the environment (e.g. a loaded .env file).
        pass
