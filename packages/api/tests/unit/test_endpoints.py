"""
API endpoint tests — all 14 REST endpoints.
Covers: status codes, response schemas, error cases, pagination, auth.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.core.errors import BotLimitExceededError, BotNotFoundError
from src.models.schemas import (
    IndicatorsConfig,
    ParametersConfig,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trade_record(**overrides) -> dict:
    """Minimal valid TradeRecord dict."""
    base = dict(
        timestamp="07-20-2025 12:00:00",
        position="LONG",
        base="BTC", quote="USDT",
        buy_exchange="binance", sell_exchange="okx",
        buy_price=60000.0, sell_price=60200.0,
        buy_trade_amount=1.0, sell_trade_amount=1.0,
        executed_amount=1.0,
        buy_value=60000.0, sell_value=60200.0,
        buy_fee_rate=0.001, sell_fee_rate=0.001,
        buy_fee_base=0.0, buy_fee_quote=60.0, sell_fee_quote=60.2,
        profit=79.8, profit_percentage=0.00133,
    )
    base.update(overrides)
    return base


def _params_config() -> ParametersConfig:
    return ParametersConfig(exchanges={"Binance": True}, symbols={"BTC/USDT": True})


def _indicators_config() -> IndicatorsConfig:
    return IndicatorsConfig(
        periods={"5min": True},
        oscillators={"Relative Strength Index (14)": True},
        movingaverages={"Exponential Moving Average (10)": True},
    )


# ---------------------------------------------------------------------------
# 1. Health endpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_returns_200(self, client: TestClient):
        assert client.get("/api/v1/health").status_code == 200

    def test_response_schema(self, client: TestClient):
        data = client.get("/api/v1/health").json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_no_auth_required(self, client: TestClient):
        r = client.get("/api/v1/health")
        assert r.status_code == 200

    def test_security_headers_present(self, client: TestClient):
        r = client.get("/api/v1/health")
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"
        assert "x-request-id" in r.headers
        assert r.headers.get("cache-control") == "no-store, no-cache, must-revalidate"
        assert r.headers.get("pragma") == "no-cache"

    def test_request_id_echoed(self, client: TestClient):
        r = client.get("/api/v1/health", headers={"X-Request-ID": "trace-abc"})
        assert r.headers.get("x-request-id") == "trace-abc"


# ---------------------------------------------------------------------------
# 2. GET /bots — list bots
# ---------------------------------------------------------------------------

class TestListBots:

    def test_returns_botids(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_botids.return_value = ["bot-001", "bot-002"]
        r = client.get("/api/v1/bots?client_id=test", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == {"botids": ["bot-001", "bot-002"]}

    def test_empty_list(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_botids.return_value = []
        r = client.get("/api/v1/bots?client_id=test", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["botids"] == []

    def test_missing_client_id_returns_400(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/bots", headers=auth_headers)
        assert r.status_code == 400

    def test_no_auth_returns_401_in_static_mode(self, client: TestClient, mock_bot_service):
        """Covered by TestStaticTokenAuth in test_security.py — skip duplicate here."""
        pass


# ---------------------------------------------------------------------------
# 3. POST /bots — create bot
# ---------------------------------------------------------------------------

class TestCreateBot:

    def test_returns_201_with_botid(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.create_bot = AsyncMock(return_value="new-bot-001")
        r = client.post("/api/v1/bots?client_id=test", headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["botid"] == "new-bot-001"

    def test_bot_limit_returns_429(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.create_bot = AsyncMock(
            side_effect=BotLimitExceededError(5)
        )
        r = client.post("/api/v1/bots?client_id=test", headers=auth_headers)
        assert r.status_code == 429

    def test_missing_client_id_returns_400(self, client: TestClient, auth_headers):
        r = client.post("/api/v1/bots", headers=auth_headers)
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 4. POST /bots/{botid}/run
# ---------------------------------------------------------------------------

class TestRunBot:

    def test_returns_200(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.run_bot = AsyncMock(return_value=None)
        r = client.post("/api/v1/bots/bot-001/run?client_id=test", headers=auth_headers)
        assert r.status_code == 200
        assert "started" in r.json()["message"]

    def test_not_found_returns_404(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.run_bot = AsyncMock(side_effect=BotNotFoundError("bot-999"))
        r = client.post("/api/v1/bots/bot-999/run?client_id=test", headers=auth_headers)
        assert r.status_code == 404

    def test_invalid_botid_returns_422(self, client: TestClient, auth_headers):
        r = client.post("/api/v1/bots/bot evil/run?client_id=test", headers=auth_headers)
        assert r.status_code in (400, 422)

    def test_oversized_botid_returns_422(self, client: TestClient, auth_headers):
        r = client.post(f"/api/v1/bots/{'a' * 65}/run?client_id=test", headers=auth_headers)
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# 5. POST /bots/{botid}/stop
# ---------------------------------------------------------------------------

class TestStopBot:

    def test_returns_200(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.stop_bot = AsyncMock(return_value=None)
        r = client.post("/api/v1/bots/bot-001/stop?client_id=test", headers=auth_headers)
        assert r.status_code == 200
        assert "stopped" in r.json()["message"]

    def test_not_found_returns_404(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.stop_bot = AsyncMock(side_effect=BotNotFoundError("bot-999"))
        r = client.post("/api/v1/bots/bot-999/stop?client_id=test", headers=auth_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 6. DELETE /bots/{botid}
# ---------------------------------------------------------------------------

class TestRemoveBot:

    def test_returns_200(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.remove_bot = AsyncMock(return_value=None)
        r = client.delete("/api/v1/bots/bot-001?client_id=test", headers=auth_headers)
        assert r.status_code == 200
        assert "removed" in r.json()["message"]

    def test_not_found_returns_404(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.remove_bot = AsyncMock(side_effect=BotNotFoundError("bot-999"))
        r = client.delete("/api/v1/bots/bot-999?client_id=test", headers=auth_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 7. GET /bots/{botid}/orders
# ---------------------------------------------------------------------------

class TestGetOrders:

    def test_returns_list(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_orders = AsyncMock(return_value=[_trade_record()])
        r = client.get("/api/v1/bots/bot-001/orders?client_id=test", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) == 1

    def test_empty_list(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_orders = AsyncMock(return_value=[])
        r = client.get("/api/v1/bots/bot-001/orders?client_id=test", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_not_found_returns_404(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_orders = AsyncMock(side_effect=BotNotFoundError("bot-999"))
        r = client.get("/api/v1/bots/bot-999/orders?client_id=test", headers=auth_headers)
        assert r.status_code == 404

    def test_pagination_params_accepted(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_orders = AsyncMock(return_value=[])
        r = client.get(
            "/api/v1/bots/bot-001/orders?client_id=test&limit=50&offset=10",
            headers=auth_headers,
        )
        assert r.status_code == 200
        mock_bot_service.get_orders.assert_called_once_with("bot-001", "test", 50, 10)

    def test_limit_above_max_returns_422(self, client: TestClient, auth_headers):
        r = client.get(
            "/api/v1/bots/bot-001/orders?client_id=test&limit=9999",
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_negative_offset_returns_422(self, client: TestClient, auth_headers):
        r = client.get(
            "/api/v1/bots/bot-001/orders?client_id=test&offset=-1",
            headers=auth_headers,
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# 8. GET /bots/{botid}/trades
# ---------------------------------------------------------------------------

class TestGetTrades:

    def test_returns_list(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_trades = AsyncMock(return_value=[_trade_record()])
        r = client.get("/api/v1/bots/bot-001/trades?client_id=test", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_pagination_params_forwarded(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_trades = AsyncMock(return_value=[])
        r = client.get(
            "/api/v1/bots/bot-001/trades?client_id=test&limit=25&offset=5",
            headers=auth_headers,
        )
        assert r.status_code == 200
        mock_bot_service.get_trades.assert_called_once_with("bot-001", "test", 25, 5)

    def test_not_found_returns_404(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_trades = AsyncMock(side_effect=BotNotFoundError("bot-999"))
        r = client.get("/api/v1/bots/bot-999/trades?client_id=test", headers=auth_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 9. GET /parameters/defaults
# ---------------------------------------------------------------------------

class TestGetDefaultParameters:

    def test_returns_200(self, client: TestClient, mock_config_service, auth_headers):
        mock_config_service.get_default_parameters = AsyncMock(return_value=_params_config())
        r = client.get("/api/v1/parameters/defaults", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "exchanges" in data
        assert "symbols" in data

    def test_not_found_returns_404(self, client: TestClient, mock_config_service, auth_headers):
        from fastapi import HTTPException
        mock_config_service.get_default_parameters = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Default parameters file not found")
        )
        r = client.get("/api/v1/parameters/defaults", headers=auth_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 10. GET /parameters
# ---------------------------------------------------------------------------

class TestGetParameters:

    def test_returns_200(self, client: TestClient, mock_config_service, auth_headers):
        mock_config_service.get_parameters = AsyncMock(return_value=_params_config())
        r = client.get("/api/v1/parameters?client_id=test", headers=auth_headers)
        assert r.status_code == 200

    def test_not_found_returns_404(self, client: TestClient, mock_config_service, auth_headers):
        from fastapi import HTTPException
        mock_config_service.get_parameters = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Parameters not found")
        )
        r = client.get("/api/v1/parameters?client_id=test", headers=auth_headers)
        assert r.status_code == 404

    def test_missing_client_id_returns_400(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/parameters", headers=auth_headers)
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 11. PUT /parameters
# ---------------------------------------------------------------------------

class TestUpdateParameters:

    def test_returns_200(self, client: TestClient, mock_config_service, auth_headers):
        mock_config_service.update_parameters = AsyncMock(return_value=None)
        r = client.put(
            "/api/v1/parameters?client_id=test",
            json={"exchanges": {"Binance": True}, "symbols": {"BTC/USDT": True}},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "updated" in r.json()["message"]

    def test_invalid_key_returns_422(self, client: TestClient, auth_headers):
        r = client.put(
            "/api/v1/parameters?client_id=test",
            json={"exchanges": {"<script>alert(1)</script>": True}, "symbols": {}},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_missing_client_id_returns_400(self, client: TestClient, auth_headers):
        r = client.put(
            "/api/v1/parameters",
            json={"exchanges": {}, "symbols": {}},
            headers=auth_headers,
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 12. GET /indicators/defaults
# ---------------------------------------------------------------------------

class TestGetDefaultIndicators:

    def test_returns_200(self, client: TestClient, mock_config_service, auth_headers):
        mock_config_service.get_default_indicators = AsyncMock(return_value=_indicators_config())
        r = client.get("/api/v1/indicators/defaults", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "periods" in data
        assert "oscillators" in data
        assert "movingaverages" in data


# ---------------------------------------------------------------------------
# 13. GET /indicators
# ---------------------------------------------------------------------------

class TestGetIndicators:

    def test_returns_200(self, client: TestClient, mock_config_service, auth_headers):
        mock_config_service.get_indicators = AsyncMock(return_value=_indicators_config())
        r = client.get("/api/v1/indicators?client_id=test", headers=auth_headers)
        assert r.status_code == 200

    def test_missing_client_id_returns_400(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/indicators", headers=auth_headers)
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 14. PUT /indicators
# ---------------------------------------------------------------------------

class TestUpdateIndicators:

    def test_returns_200(self, client: TestClient, mock_config_service, auth_headers):
        mock_config_service.update_indicators = AsyncMock(return_value=None)
        r = client.put(
            "/api/v1/indicators?client_id=test",
            json={
                "periods": {"5min": True},
                "oscillators": {"Relative Strength Index (14)": True},
                "movingaverages": {"Exponential Moving Average (10)": True},
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "updated" in r.json()["message"]

    def test_invalid_key_returns_422(self, client: TestClient, auth_headers):
        r = client.put(
            "/api/v1/indicators?client_id=test",
            json={"periods": {}, "oscillators": {"key\x00null": True}, "movingaverages": {}},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_missing_client_id_returns_400(self, client: TestClient, auth_headers):
        r = client.put(
            "/api/v1/indicators",
            json={"periods": {}, "oscillators": {}, "movingaverages": {}},
            headers=auth_headers,
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# 15. Error handler tests
# ---------------------------------------------------------------------------

class TestErrorHandlers:

    def test_bot_not_found_returns_404_with_detail(
        self, client: TestClient, mock_bot_service, auth_headers
    ):
        mock_bot_service.run_bot = AsyncMock(side_effect=BotNotFoundError("missing"))
        r = client.post("/api/v1/bots/missing/run?client_id=test", headers=auth_headers)
        assert r.status_code == 404
        assert "missing" in r.json()["detail"]

    def test_bot_limit_returns_429_with_detail(
        self, client: TestClient, mock_bot_service, auth_headers
    ):
        mock_bot_service.create_bot = AsyncMock(side_effect=BotLimitExceededError(5))
        r = client.post("/api/v1/bots?client_id=test", headers=auth_headers)
        assert r.status_code == 429
        assert "5" in r.json()["detail"]

    def test_unhandled_exception_returns_500(
        self, client: TestClient, mock_bot_service, auth_headers
    ):
        mock_bot_service.get_botids = MagicMock(side_effect=RuntimeError("unexpected"))
        r = client.get("/api/v1/bots?client_id=test", headers=auth_headers)
        assert r.status_code == 500
        assert r.json()["detail"] == "Internal server error"
