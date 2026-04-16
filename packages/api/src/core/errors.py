"""
SonarFT API Error Handling
"""
from fastapi import Request
from fastapi.responses import JSONResponse


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


async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
