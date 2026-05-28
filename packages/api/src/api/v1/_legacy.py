"""
Shared helpers for legacy (deprecated) API routes.
Centralises the sunset date and deprecation header injection so both
bots.py and config.py reference a single source of truth.
"""
from __future__ import annotations

from fastapi.responses import Response

# Update this date when the legacy routes are scheduled for removal.
LEGACY_SUNSET_DATE: str = "Sun, 01 Jan 2026 00:00:00 GMT"


def add_deprecation_headers(response: Response) -> None:
    """Inject Deprecation and Sunset headers on every legacy response."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = LEGACY_SUNSET_DATE
