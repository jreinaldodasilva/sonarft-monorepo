"""
SonarFT API — FastAPI application factory.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .api.v1.endpoints.bots import router as bots_router
from .api.v1.endpoints.clients import router as clients_router
from .api.v1.endpoints.config import router as config_router
from .api.v1.endpoints.health import router as health_router
from .api.v1.endpoints.ws_ticket import router as ws_ticket_router
from .core.config import get_settings
from .core.context import request_id_var as _request_id_var
from .core.errors import (
    BotCreationFailedError,
    BotLimitExceededError,
    BotNotFoundError,
    ConfigNotFoundError,
    ConfigWriteError,
    bot_creation_failed_handler,
    bot_limit_handler,
    bot_not_found_handler,
    config_not_found_handler,
    config_write_error_handler,
    generic_error_handler,
    http_exception_handler,
)
from .core.limiter import limiter
from .websocket.manager import WebSocketManager
from .websocket.tickets import get_ticket_store

# _request_id_var is imported from core.context above


class RequestIdFilter(logging.Filter):
    """Injects the current request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get("-")
        return True


_settings = get_settings()
_log_level = getattr(logging, _settings.log_level.upper(), logging.INFO)
_log_fmt = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s — %(message)s"

logging.basicConfig(level=_log_level, format=_log_fmt)

# Suppress ccxt's verbose HTTP debug output — it logs full response bodies at DEBUG
logging.getLogger("ccxt").setLevel(logging.WARNING)

# Optional rotating file handler — disabled when LOG_FILE is empty
if _settings.log_file:
    _log_path = os.path.join(os.path.dirname(__file__), "..", _settings.log_file)
    _log_path = os.path.normpath(_log_path)
    os.makedirs(os.path.dirname(_log_path), exist_ok=True)
    _file_handler = logging.handlers.RotatingFileHandler(
        _log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB per file
        backupCount=7,
        encoding="utf-8",
    )
    _file_handler.setFormatter(logging.Formatter(_log_fmt))
    _file_handler.setLevel(_log_level)
    logging.root.addHandler(_file_handler)

# Attach the request-id filter to all root handlers (console + file)
for _h in logging.root.handlers:
    _h.addFilter(RequestIdFilter())

# Structured JSON metrics logger — writes raw JSON lines to a dedicated file
# so metrics can be parsed independently of the human-readable log.
if _settings.metrics_log_file:
    _metrics_path = os.path.join(os.path.dirname(__file__), "..", _settings.metrics_log_file)
    _metrics_path = os.path.normpath(_metrics_path)
    os.makedirs(os.path.dirname(_metrics_path), exist_ok=True)
    _metrics_handler = logging.handlers.RotatingFileHandler(
        _metrics_path,
        maxBytes=50 * 1024 * 1024,  # 50 MB — metrics are verbose
        backupCount=14,
        encoding="utf-8",
    )
    # Raw message only — the JSON payload is already fully formed by sonarft_metrics
    _metrics_handler.setFormatter(logging.Formatter("%(message)s"))
    _metrics_handler.setLevel(logging.DEBUG)
    _metrics_logger = logging.getLogger("sonarft.metrics")
    _metrics_logger.addHandler(_metrics_handler)
    _metrics_logger.propagate = False  # don't duplicate into the root handler


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
        # Prevent trade history and config responses from being cached by
        # browsers or intermediary proxies.
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request with method, path, status code, and duration.

    Provides a minimal access log so operators can reconstruct request
    history from the application log without a separate web server log.
    Format: ACCESS {METHOD} {path} -> {status} ({duration_ms:.1f}ms)
    """

    _access_logger = logging.getLogger("sonarft.access")

    async def dispatch(self, request: Request, call_next) -> Response:
        import time as _time
        t0 = _time.monotonic()
        response = await call_next(request)
        duration_ms = (_time.monotonic() - t0) * 1000
        self._access_logger.info(
            "ACCESS %s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
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

    # Warn loudly if auth is completely disabled — prevents silent open deployments.
    settings = get_settings()
    if not settings.netlify_site_url and not settings.sonarft_api_token:
        _logger.warning(
            "⚠️  AUTH DISABLED — neither NETLIFY_SITE_URL nor SONARFT_API_TOKEN is set. "
            "All endpoints are publicly accessible. Do not use this configuration in production."
        )

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
        default_response_class=ORJSONResponse,
    )

    # GZip compression — reduces response size ~3-10x for history payloads
    # minimum_size=1000 skips compression for tiny responses (health, bot list)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Security headers (outermost — applied to all responses)
    app.add_middleware(SecurityHeadersMiddleware)

    # Access log — logs method, path, status, and duration for every request
    app.add_middleware(AccessLogMiddleware)

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
    app.add_exception_handler(BotCreationFailedError, bot_creation_failed_handler)
    app.add_exception_handler(ConfigNotFoundError, config_not_found_handler)
    app.add_exception_handler(ConfigWriteError, config_write_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    # Routers
    prefix = settings.api_prefix
    app.include_router(health_router, prefix=prefix)
    app.include_router(clients_router, prefix=prefix)          # canonical: /clients/{id}/bots
    app.include_router(bots_router, prefix=prefix)             # legacy: /bots?client_id=
    app.include_router(config_router, prefix=prefix)           # legacy: /parameters?client_id=
    app.include_router(ws_ticket_router, prefix=prefix)

    # WebSocket
    ws_manager = WebSocketManager()

    @app.websocket(f"{prefix}/ws/{{client_id}}")
    async def websocket_endpoint(
        websocket: WebSocket,
        client_id: str,
        ticket: str | None = None,
        token: str | None = None,
    ) -> None:
        """
        WebSocket endpoint.
        Preferred auth: ?ticket=<single-use ticket from POST /ws/ticket>
        Legacy auth:    ?token=<JWT> (kept for backward compatibility)
        """
        bot_service = app.state.bot_service
        if bot_service is None:
            await websocket.close(code=1011)
            return

        # Resolve identity from ticket (preferred) or token (legacy)
        resolved_token: str | None = None
        if ticket:
            store = get_ticket_store()
            identity = store.redeem(ticket)
            if identity is None:
                await websocket.close(code=1008)  # invalid/expired ticket
                return
            # Ticket is valid — identity already verified; pass None so
            # verify_token in handle_connection runs in dev-mode pass-through
            # We set a sentinel so the manager knows auth is pre-verified.
            resolved_token = "__ticket_verified__"
        else:
            resolved_token = token

        await ws_manager.handle_connection(
            websocket, client_id, resolved_token, bot_service._manager
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
