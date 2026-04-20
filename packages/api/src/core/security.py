"""
SonarFT API Security
JWT validation (Netlify Identity), static token fallback, and tenant isolation.
"""
from __future__ import annotations
import hmac
import logging
from typing import Optional

import jwt
from jwt import PyJWKClient, InvalidTokenError
from fastapi import Depends, HTTPException, Query, Request
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


def _decode_jwt(token: str) -> dict:
    """Decode and validate a Netlify JWT. Returns the payload dict."""
    client = _get_jwks_client()
    if not client:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="netlify",
            options={"verify_exp": True},
        )
    except InvalidTokenError as exc:
        _logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Unauthorized") from exc


def _client_ip(request: Optional[Request]) -> str:
    """Extract the client IP from the request for logging."""
    if request is None:
        return "unknown"
    if request.client:
        return request.client.host
    return request.headers.get("X-Forwarded-For", "unknown").split(",")[0].strip()


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

    if _get_jwks_client():
        _decode_jwt(token)
        return

    # Static token — use timing-safe comparison to prevent timing attacks
    if settings.sonarft_api_token:
        if not hmac.compare_digest(
            token.encode("utf-8"),
            settings.sonarft_api_token.encode("utf-8"),
        ):
            raise HTTPException(status_code=401, detail="Unauthorized")


def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> None:
    """FastAPI dependency — validates the Authorization: Bearer header."""
    token = credentials.credentials if credentials else None
    try:
        verify_token(token)
    except HTTPException:
        _logger.warning(
            "Auth failure from %s — missing or invalid token",
            _client_ip(request),
        )
        raise


def get_client_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    client_id: Optional[str] = Query(default=None),
) -> str:
    """
    FastAPI dependency — returns the authenticated client's identity.

    Tenant isolation strategy:
    - Netlify JWT mode: extracts `sub` (or `email`) from the verified JWT payload.
      The `client_id` query parameter is ignored — identity comes from the token.
    - Static token / dev mode: requires `client_id` as a query parameter.
      The caller is trusted to supply their own ID (no identity claim available).

    Raises HTTP 401 if auth is required but token is missing/invalid.
    Raises HTTP 400 if client_id is required but not provided.
    """
    settings = get_settings()
    token = credentials.credentials if credentials else None
    ip = _client_ip(request)

    # Netlify JWT mode — derive client_id from token claims
    if settings.netlify_site_url:
        if not token:
            _logger.warning("Auth failure from %s — missing token (Netlify mode)", ip)
            raise HTTPException(status_code=401, detail="Unauthorized")
        try:
            payload = _decode_jwt(token)
        except HTTPException:
            _logger.warning("Auth failure from %s — invalid JWT", ip)
            raise
        identity = payload.get("sub") or payload.get("email")
        if not identity:
            _logger.warning("Auth failure from %s — token missing identity claim", ip)
            raise HTTPException(status_code=401, detail="Token missing identity claim")
        return identity

    # Static token / dev mode — validate token then use query param
    try:
        verify_token(token)
    except HTTPException:
        _logger.warning("Auth failure from %s — invalid static token", ip)
        raise

    if not client_id:
        raise HTTPException(status_code=400, detail="client_id query parameter is required")
    return client_id
