"""
Shared pytest fixtures for the SonarFT API test suite.
"""
from __future__ import annotations
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# App / client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """Create the FastAPI app once per test session."""
    from src.main import create_app
    return create_app()


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_headers() -> dict:
    return {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# BotService mock — injected into app.state
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_bot_service(app):
    """
    Injects a mock BotService into app.state so get_bot_service_from_state
    returns it. Restores the original on teardown.
    """
    from src.services.bot_service import get_bot_service
    get_bot_service.cache_clear()

    service = MagicMock()
    service.get_botids = MagicMock(return_value=["bot-001", "bot-002"])
    service.create_bot = AsyncMock(return_value="bot-003")
    service.run_bot = AsyncMock(return_value=None)
    service.stop_bot = AsyncMock(return_value=None)
    service.remove_bot = AsyncMock(return_value=None)
    service.get_orders = AsyncMock(return_value=[])
    service.get_trades = AsyncMock(return_value=[])
    # _manager is used directly by the WebSocket handler
    manager = MagicMock()
    manager.get_botids = MagicMock(return_value=["bot-001", "bot-002"])
    manager.create_bot = AsyncMock(return_value="bot-003")
    manager.run_bot = AsyncMock(return_value=None)
    manager.remove_bot = AsyncMock(return_value=None)
    manager.set_simulation_mode = AsyncMock(return_value=None)
    service._manager = manager

    original = getattr(app.state, "bot_service", None)
    app.state.bot_service = service
    yield service
    app.state.bot_service = original


# ---------------------------------------------------------------------------
# ConfigService mock — injected into app.state
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config_service(app):
    """
    Injects a mock ConfigService into app.state so get_config_service_from_state
    returns it. Restores the original on teardown.
    """
    from src.services.config_service import get_config_service
    get_config_service.cache_clear()

    service = MagicMock()
    service.get_default_parameters = AsyncMock(return_value=MagicMock(
        exchanges={"binance": True}, symbols={"BTC/USDT": True}
    ))
    service.get_parameters = AsyncMock(return_value=MagicMock(
        exchanges={"binance": True}, symbols={"BTC/USDT": True}
    ))
    service.update_parameters = AsyncMock(return_value=None)
    service.get_default_indicators = AsyncMock(return_value=MagicMock(
        periods={"5min": True}, oscillators={}, movingaverages={}
    ))
    service.get_indicators = AsyncMock(return_value=MagicMock(
        periods={"5min": True}, oscillators={}, movingaverages={}
    ))
    service.update_indicators = AsyncMock(return_value=None)

    original = getattr(app.state, "config_service", None)
    app.state.config_service = service
    yield service
    app.state.config_service = original
