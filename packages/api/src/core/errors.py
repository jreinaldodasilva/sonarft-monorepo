"""
SonarFT API Error Handling
"""
import logging

from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

_logger = logging.getLogger(__name__)


class BotNotFoundError(Exception):
    def __init__(self, botid: str):
        self.botid = botid
        super().__init__(f"Bot not found: {botid}")


class BotLimitExceededError(Exception):
    def __init__(self, limit: int):
        self.limit = limit
        super().__init__(f"Bot limit reached: {limit}")


def _error_body(detail: str, request: Request) -> dict:
    """Build a consistent error response body that includes the request ID.

    Including request_id lets clients correlate their error report with
    the corresponding server log entry without inspecting response headers.
    """
    from .context import request_id_var
    return {"detail": detail, "request_id": request_id_var.get("-")}


async def bot_not_found_handler(request: Request, exc: BotNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content=_error_body(str(exc), request))


async def bot_limit_handler(request: Request, exc: BotLimitExceededError) -> JSONResponse:
    return JSONResponse(status_code=429, content=_error_body(str(exc), request))


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Wrap FastAPI's default HTTPException handler to inject request_id."""
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.detail, request),
        headers=getattr(exc, "headers", None) or {},
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from .context import request_id_var
    _logger.exception(
        "Unhandled exception [%s %s] request_id=%s: %s",
        request.method,
        request.url.path,
        request_id_var.get("-"),
        exc,
    )
    return JSONResponse(
        status_code=500,
        content=_error_body("Internal server error", request),
    )
