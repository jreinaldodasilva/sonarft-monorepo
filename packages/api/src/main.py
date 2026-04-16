"""
SonarFT API — FastAPI application factory.
"""
from __future__ import annotations
import logging
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.errors import (
    BotNotFoundError, BotLimitExceededError,
    bot_not_found_handler, bot_limit_handler, generic_error_handler,
)
from .api.v1.endpoints.health import router as health_router
from .api.v1.endpoints.bots import router as bots_router
from .api.v1.endpoints.config import router as config_router
from .websocket.manager import WebSocketManager
from .services.bot_service import get_bot_service
from .core.security import verify_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

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
        bot_service = get_bot_service()
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
