"""Authlib OAuth2 client registry for the three Baseline social providers.

Each provider's client_id/client_secret comes from env vars
(`{PROVIDER}_OAUTH_CLIENT_ID` / `_CLIENT_SECRET`) -- never hardcoded.
Registration is lazy (module import doesn't require all three to be
configured) so local dev can run with only the providers actually
being tested.
"""

from __future__ import annotations

import os

from authlib.integrations.starlette_client import OAuth

oauth = OAuth()

_PROVIDER_CONFIG = {
    "google": {
        "server_metadata_url": (
            "https://accounts.google.com/.well-known/openid-configuration"
        ),
        "client_kwargs": {"scope": "openid email profile"},
    },
    "facebook": {
        "access_token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
        "authorize_url": "https://www.facebook.com/v18.0/dialog/oauth",
        "api_base_url": "https://graph.facebook.com/v18.0/",
        "client_kwargs": {"scope": "email public_profile"},
    },
    "linkedin": {
        "access_token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "authorize_url": "https://www.linkedin.com/oauth/v2/authorization",
        "api_base_url": "https://api.linkedin.com/v2/",
        "client_kwargs": {"scope": "openid email profile"},
    },
}


def register_configured_providers() -> None:
    """Registers only the providers with both env vars present. Called
    once at app startup, not at import time, so tests can run without
    any OAuth env vars set at all."""
    for provider, config in _PROVIDER_CONFIG.items():
        client_id = os.environ.get(f"{provider.upper()}_OAUTH_CLIENT_ID")
        client_secret = os.environ.get(f"{provider.upper()}_OAUTH_CLIENT_SECRET")
        if not client_id or not client_secret:
            continue
        oauth.register(
            name=provider,
            client_id=client_id,
            client_secret=client_secret,
            **config,
        )


def is_provider_configured(provider: str) -> bool:
    return provider in oauth._clients  # noqa: SLF001 -- Authlib has no public check
