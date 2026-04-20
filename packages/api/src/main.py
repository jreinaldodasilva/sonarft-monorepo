"""
SonarFT API — FastAPI application factory.
"""
from __future__ import annotations
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .core.config import get_settings
from .core.errors import (
    BotNotFoundError, BotLimitExceededError,
    bot_not_found_handler, bot_limit_handler, generic_error_handler,
)
from .core.limiter import limiter
from .core.context import request_id_var as _request_id_var
from .api.v1.endpoints.health import router as health_router
from .api.v1.endpoints.bots import router as bots_router
from .api.v1.endpoints.config import router as config_router
from .websocket.manager import WebSocketManager
from .core.security import verify_token

# _request_id_var is imported from core.context above


class RequestIdFilter(logging.Filter):
    """Injects the current request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get("-")
        return True


logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(request_id)s] %(name)s — %(message)s",
)
# Attach the filter to the root handler so all loggers inherit it
for _h in logging.root.handlers:
    _h.addFilter(RequestIdFilter())


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Generates or propagates an X-Request-ID header for every HTTP request.
    Sets the ContextVar so all log lines within the request include the ID.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every HTTP response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        return response


# Module-level limiter is defined in core/limiter.py to avoid circular imports


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """
    FastAPI lifespan handler.
    Initialises BotService and ConfigService once at startup so:
    - The bot package import happens before the server accepts requests
    - Import errors surface immediately with a clear message
    - Services are stored on app.state (no lru_cache singleton)
    """
    _logger = logging.getLogger(__name__)
    from .services.bot_service import BotService
    from .services.config_service import ConfigService
    try:
        app.state.bot_service = BotService()
        _logger.info("BotService initialised")
    except Exception as exc:
        _logger.error("Failed to initialise BotService: %s", exc)
        app.state.bot_service = None

    try:
        app.state.config_service = ConfigService()
        _logger.info("ConfigService initialised")
    except Exception as exc:
        _logger.error("Failed to initialise ConfigService: %s", exc)
        app.state.config_service = None

    yield
    # Shutdown: nothing to clean up for now
    _logger.info("API shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=_lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Security headers (outermost — applied to all responses)
    app.add_middleware(SecurityHeadersMiddleware)

    # Request ID — generates/propagates X-Request-ID and sets ContextVar
    app.add_middleware(RequestIdMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Error handlers
    app.add_exception_handler(BotNotFoundError, bot_not_found_handler)
    app.add_exception_handler(BotLimitExceededError, bot_limit_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    # Routers
    prefix = settings.api_prefix
    app.include_router(health_router, prefix=prefix)
    app.include_router(bots_router, prefix=prefix)
    app.include_router(config_router, prefix=prefix)

    # WebSocket
    ws_manager = WebSocketManager()

    @app.websocket(f"{prefix}/ws/{{client_id}}")
    async def websocket_endpoint(
        websocket: WebSocket,
        client_id: str,
        token: Optional[str] = None,
    ) -> None:
        bot_service = app.state.bot_service
        if bot_service is None:
            await websocket.close(code=1011)  # Internal error
            return
        await ws_manager.handle_connection(
            websocket, client_id, token, bot_service._manager
        )

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
