"""
SonarFT API Error Handling
"""
import logging

from fastapi import Request
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


async def bot_not_found_handler(_request: Request, exc: BotNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def bot_limit_handler(_request: Request, exc: BotLimitExceededError) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": str(exc)})


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from .context import request_id_var
    _logger.exception(
        "Unhandled exception [%s %s] request_id=%s: %s",
        request.method,
        request.url.path,
        request_id_var.get("-"),
        exc,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
