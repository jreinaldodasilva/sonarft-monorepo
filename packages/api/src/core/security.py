"""
SonarFT API Security
JWT validation (Netlify Identity) and static token fallback.
"""
from __future__ import annotations
import logging
from typing import Optional

import jwt
from jwt import PyJWKClient, InvalidTokenError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import get_settings

_logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)

# Initialise JWKS client once at import time if Netlify URL is configured.
_jwks_client: Optional[PyJWKClient] = None

def _get_jwks_client() -> Optional[PyJWKClient]:
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        if settings.netlify_site_url:
            url = f"{settings.netlify_site_url.rstrip('/')}/.netlify/identity/keys"
            _jwks_client = PyJWKClient(url)
            _logger.info("Netlify JWT auth enabled — JWKS: %s", url)
    return _jwks_client


def verify_token(token: Optional[str]) -> None:
    """
    Validate a Bearer token.
    Raises HTTPException(401) on failure.
    Auth is disabled if neither NETLIFY_SITE_URL nor SONARFT_API_TOKEN is set.
    """
    settings = get_settings()

    if not settings.netlify_site_url and not settings.sonarft_api_token:
        return  # dev mode — no auth configured

    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    client = _get_jwks_client()
    if client:
        try:
            signing_key = client.get_signing_key_from_jwt(token)
            jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience="netlify",
                options={"verify_exp": True},
            )
            return
        except InvalidTokenError as exc:
            _logger.warning("JWT validation failed: %s", exc)
            raise HTTPException(status_code=401, detail="Unauthorized") from exc

    if settings.sonarft_api_token and token != settings.sonarft_api_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> None:
    """FastAPI dependency — validates the Authorization: Bearer header."""
    verify_token(credentials.credentials if credentials else None)
