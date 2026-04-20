"""
Shared pytest fixtures for the SonarFT API test suite.
"""
from __future__ import annotations
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

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
    """Synchronous TestClient — works for both sync and async endpoints."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_headers() -> dict:
    """
    In dev mode (no NETLIFY_SITE_URL / SONARFT_API_TOKEN configured),
    any bearer token is accepted. Use this fixture for authenticated requests.
    """
    return {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# BotService mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_bot_service():
    """
    Patch get_bot_service() at the endpoint level and clear the lru_cache
    so the mock is always used regardless of import order.
    Yields the mock service instance so tests can configure return values.
    """
    from src.services.bot_service import get_bot_service
    get_bot_service.cache_clear()

    with patch("src.api.v1.endpoints.bots.get_bot_service") as factory:
        service = MagicMock()
        service.get_botids = MagicMock(return_value=["bot-001", "bot-002"])
        service.create_bot = AsyncMock(return_value="bot-003")
        service.run_bot = AsyncMock(return_value=None)
        service.stop_bot = AsyncMock(return_value=None)
        service.remove_bot = AsyncMock(return_value=None)
        service.get_orders = AsyncMock(return_value=[])
        service.get_trades = AsyncMock(return_value=[])
        factory.return_value = service
        yield service


# ---------------------------------------------------------------------------
# ConfigService mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config_service():
    """
    Patch get_config_service() at the endpoint level.
    """
    from src.services.config_service import get_config_service
    get_config_service.cache_clear()

    with patch("src.api.v1.endpoints.config.get_config_service") as factory:
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
        factory.return_value = service
        yield service
