"""
Canonical client-scoped endpoint tests — /clients/{client_id}/...

Covers all 11 endpoints in clients.py:
  GET/POST  /clients/{id}/bots
  POST      /clients/{id}/bots/{botid}/run
  POST      /clients/{id}/bots/{botid}/stop
  DELETE    /clients/{id}/bots/{botid}
  GET       /clients/{id}/bots/{botid}/orders
  GET       /clients/{id}/bots/{botid}/trades
  GET/PUT   /clients/{id}/parameters
  GET/PUT   /clients/{id}/indicators

Each endpoint is tested for: success, error cases, input validation,
and auth (spot-checked via the static-token fixture from test_security.py).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from src.core.errors import BotLimitExceededError, BotNotFoundError
from src.models.schemas import ClientParametersConfig, IndicatorsConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE = "/api/v1/clients"


def _trade_record(**overrides) -> dict:
    base = dict(
        timestamp="2025-07-01T12:00:00",
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


def _params() -> ClientParametersConfig:
    return ClientParametersConfig(exchanges={"Binance": True}, symbols={"BTC/USDT": True})


def _indicators() -> IndicatorsConfig:
    return IndicatorsConfig(
        periods={"5min": True},
        oscillators={"Relative Strength Index (14)": True},
        movingaverages={"Exponential Moving Average (10)": True},
    )


# ---------------------------------------------------------------------------
# 1. GET /clients/{client_id}/bots
# ---------------------------------------------------------------------------

class TestCanonicalListBots:

    def test_returns_botids(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_botids.return_value = ["bot-001", "bot-002"]
        r = client.get(f"{BASE}/test-client/bots", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == {"botids": ["bot-001", "bot-002"]}

    def test_empty_list(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_botids.return_value = []
        r = client.get(f"{BASE}/test-client/bots", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["botids"] == []

    def test_invalid_client_id_returns_422(self, client: TestClient, auth_headers):
        r = client.get(f"{BASE}/bad client!/bots", headers=auth_headers)
        assert r.status_code in (404, 422)

    def test_oversized_client_id_returns_422(self, client: TestClient, auth_headers):
        r = client.get(f"{BASE}/{'a' * 65}/bots", headers=auth_headers)
        assert r.status_code == 422

    def test_no_auth_returns_401_in_static_mode(self):
        from unittest.mock import patch

        from src.core.config import get_settings
        from src.services.bot_service import get_bot_service
        get_settings.cache_clear()
        get_bot_service.cache_clear()
        with patch.dict("os.environ", {"SONARFT_API_TOKEN": "secret"}, clear=False):
            get_settings.cache_clear()
            from src.main import create_app
            app = create_app()
            with TestClient(app, raise_server_exceptions=False) as c:
                r = c.get(f"{BASE}/test-client/bots")
                assert r.status_code == 401
        get_settings.cache_clear()
        get_bot_service.cache_clear()


# ---------------------------------------------------------------------------
# 2. POST /clients/{client_id}/bots
# ---------------------------------------------------------------------------

class TestCanonicalCreateBot:

    def test_returns_201_with_botid(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.create_bot = AsyncMock(return_value="new-bot-001")
        r = client.post(f"{BASE}/test-client/bots", headers=auth_headers)
        assert r.status_code == 201
        assert r.json()["botid"] == "new-bot-001"

    def test_bot_limit_returns_429(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.create_bot = AsyncMock(side_effect=BotLimitExceededError(5))
        r = client.post(f"{BASE}/test-client/bots", headers=auth_headers)
        assert r.status_code == 429
        assert "5" in r.json()["detail"]

    def test_invalid_client_id_returns_422(self, client: TestClient, auth_headers):
        r = client.post(f"{BASE}/bad client!/bots", headers=auth_headers)
        assert r.status_code in (404, 422)


# ---------------------------------------------------------------------------
# 3. POST /clients/{client_id}/bots/{botid}/run
# ---------------------------------------------------------------------------

class TestCanonicalRunBot:

    def test_returns_200_with_message(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.run_bot = AsyncMock(return_value=None)
        r = client.post(f"{BASE}/test-client/bots/bot-001/run", headers=auth_headers)
        assert r.status_code == 200
        assert "started" in r.json()["message"]

    def test_not_found_returns_404(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.run_bot = AsyncMock(side_effect=BotNotFoundError("bot-999"))
        r = client.post(f"{BASE}/test-client/bots/bot-999/run", headers=auth_headers)
        assert r.status_code == 404
        assert "bot-999" in r.json()["detail"]

    def test_invalid_botid_returns_422(self, client: TestClient, auth_headers):
        r = client.post(f"{BASE}/test-client/bots/bad bot!/run", headers=auth_headers)
        assert r.status_code in (404, 422)

    def test_oversized_botid_returns_422(self, client: TestClient, auth_headers):
        r = client.post(f"{BASE}/test-client/bots/{'a' * 65}/run", headers=auth_headers)
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# 4. POST /clients/{client_id}/bots/{botid}/stop
# ---------------------------------------------------------------------------

class TestCanonicalStopBot:

    def test_returns_200_with_message(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.stop_bot = AsyncMock(return_value=None)
        r = client.post(f"{BASE}/test-client/bots/bot-001/stop", headers=auth_headers)
        assert r.status_code == 200
        assert "stopped" in r.json()["message"]

    def test_not_found_returns_404(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.stop_bot = AsyncMock(side_effect=BotNotFoundError("bot-999"))
        r = client.post(f"{BASE}/test-client/bots/bot-999/stop", headers=auth_headers)
        assert r.status_code == 404

    def test_invalid_botid_returns_422(self, client: TestClient, auth_headers):
        r = client.post(f"{BASE}/test-client/bots/bad bot!/stop", headers=auth_headers)
        assert r.status_code in (404, 422)


# ---------------------------------------------------------------------------
# 5. DELETE /clients/{client_id}/bots/{botid}
# ---------------------------------------------------------------------------

class TestCanonicalRemoveBot:

    def test_returns_204_on_success(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.remove_bot = AsyncMock(return_value=None)
        r = client.delete(f"{BASE}/test-client/bots/bot-001", headers=auth_headers)
        assert r.status_code == 204

    def test_not_found_returns_404(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.remove_bot = AsyncMock(side_effect=BotNotFoundError("bot-999"))
        r = client.delete(f"{BASE}/test-client/bots/bot-999", headers=auth_headers)
        assert r.status_code == 404

    def test_invalid_botid_returns_422(self, client: TestClient, auth_headers):
        r = client.delete(f"{BASE}/test-client/bots/bad bot!", headers=auth_headers)
        assert r.status_code in (404, 422)


# ---------------------------------------------------------------------------
# 6. GET /clients/{client_id}/bots/{botid}/orders
# ---------------------------------------------------------------------------

class TestCanonicalGetOrders:

    def test_returns_list(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_orders = AsyncMock(return_value=[_trade_record()])
        r = client.get(f"{BASE}/test-client/bots/bot-001/orders", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_empty_list(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_orders = AsyncMock(return_value=[])
        r = client.get(f"{BASE}/test-client/bots/bot-001/orders", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_foreign_botid_returns_404(self, client: TestClient, mock_bot_service, auth_headers):
        """SEC-001: a client must not read another client's orders."""
        mock_bot_service.get_orders = AsyncMock(side_effect=BotNotFoundError("bot-foreign"))
        r = client.get(f"{BASE}/test-client/bots/bot-foreign/orders", headers=auth_headers)
        assert r.status_code == 404

    def test_pagination_params_forwarded(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_orders = AsyncMock(return_value=[])
        r = client.get(
            f"{BASE}/test-client/bots/bot-001/orders?limit=50&offset=10",
            headers=auth_headers,
        )
        assert r.status_code == 200
        mock_bot_service.get_orders.assert_called_once_with("bot-001", "test-client", 50, 10, None, None)

    def test_limit_above_max_returns_422(self, client: TestClient, auth_headers):
        r = client.get(
            f"{BASE}/test-client/bots/bot-001/orders?limit=9999",
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_negative_offset_returns_422(self, client: TestClient, auth_headers):
        r = client.get(
            f"{BASE}/test-client/bots/bot-001/orders?offset=-1",
            headers=auth_headers,
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# 7. GET /clients/{client_id}/bots/{botid}/trades
# ---------------------------------------------------------------------------

class TestCanonicalGetTrades:

    def test_returns_list(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_trades = AsyncMock(return_value=[_trade_record()])
        r = client.get(f"{BASE}/test-client/bots/bot-001/trades", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_foreign_botid_returns_404(self, client: TestClient, mock_bot_service, auth_headers):
        """SEC-001: a client must not read another client's trades."""
        mock_bot_service.get_trades = AsyncMock(side_effect=BotNotFoundError("bot-foreign"))
        r = client.get(f"{BASE}/test-client/bots/bot-foreign/trades", headers=auth_headers)
        assert r.status_code == 404

    def test_pagination_params_forwarded(self, client: TestClient, mock_bot_service, auth_headers):
        mock_bot_service.get_trades = AsyncMock(return_value=[])
        r = client.get(
            f"{BASE}/test-client/bots/bot-001/trades?limit=25&offset=5",
            headers=auth_headers,
        )
        assert r.status_code == 200
        mock_bot_service.get_trades.assert_called_once_with("bot-001", "test-client", 25, 5, None, None)

    def test_not_found_propagates_500(self, client: TestClient, mock_bot_service, auth_headers):
        """Service exceptions not wrapped in BotNotFoundError become 500."""
        mock_bot_service.get_trades = AsyncMock(side_effect=RuntimeError("db error"))
        r = client.get(f"{BASE}/test-client/bots/bot-001/trades", headers=auth_headers)
        assert r.status_code == 500


# ---------------------------------------------------------------------------
# 8. GET /clients/{client_id}/parameters
# ---------------------------------------------------------------------------

class TestCanonicalGetParameters:

    def test_returns_200(self, client: TestClient, mock_config_service, auth_headers):
        mock_config_service.get_parameters = AsyncMock(return_value=_params())
        r = client.get(f"{BASE}/test-client/parameters", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "exchanges" in data
        assert "symbols" in data
        assert "strategy" in data

    def test_not_found_returns_404(self, client: TestClient, mock_config_service, auth_headers):
        from fastapi import HTTPException
        mock_config_service.get_parameters = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Parameters not found")
        )
        r = client.get(f"{BASE}/test-client/parameters", headers=auth_headers)
        assert r.status_code == 404

    def test_invalid_client_id_returns_422(self, client: TestClient, auth_headers):
        r = client.get(f"{BASE}/bad client!/parameters", headers=auth_headers)
        assert r.status_code in (404, 422)


# ---------------------------------------------------------------------------
# 9. PUT /clients/{client_id}/parameters
# ---------------------------------------------------------------------------

class TestCanonicalUpdateParameters:

    def test_returns_200_with_message(self, client: TestClient, mock_config_service, auth_headers):
        mock_config_service.update_parameters = AsyncMock(return_value=None)
        r = client.put(
            f"{BASE}/test-client/parameters",
            json={"exchanges": {"Binance": True}, "symbols": {"BTC/USDT": True}},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "updated" in r.json()["message"]
        assert "test-client" in r.json()["message"]

    def test_invalid_key_returns_422(self, client: TestClient, auth_headers):
        r = client.put(
            f"{BASE}/test-client/parameters",
            json={"exchanges": {"<script>alert(1)</script>": True}, "symbols": {}},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_invalid_strategy_returns_422(self, client: TestClient, auth_headers):
        r = client.put(
            f"{BASE}/test-client/parameters",
            json={"exchanges": {}, "symbols": {}, "strategy": "invalid_strategy"},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_path_traversal_client_id_returns_422(self, client: TestClient, auth_headers):
        r = client.put(
            f"{BASE}/../../etc/parameters",
            json={"exchanges": {}, "symbols": {}},
            headers=auth_headers,
        )
        assert r.status_code in (404, 422)


# ---------------------------------------------------------------------------
# 10. GET /clients/{client_id}/indicators
# ---------------------------------------------------------------------------

class TestCanonicalGetIndicators:

    def test_returns_200(self, client: TestClient, mock_config_service, auth_headers):
        mock_config_service.get_indicators = AsyncMock(return_value=_indicators())
        r = client.get(f"{BASE}/test-client/indicators", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "periods" in data
        assert "oscillators" in data
        assert "movingaverages" in data

    def test_not_found_returns_404(self, client: TestClient, mock_config_service, auth_headers):
        from fastapi import HTTPException
        mock_config_service.get_indicators = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Indicators not found")
        )
        r = client.get(f"{BASE}/test-client/indicators", headers=auth_headers)
        assert r.status_code == 404

    def test_invalid_client_id_returns_422(self, client: TestClient, auth_headers):
        r = client.get(f"{BASE}/bad client!/indicators", headers=auth_headers)
        assert r.status_code in (404, 422)


# ---------------------------------------------------------------------------
# 11. PUT /clients/{client_id}/indicators
# ---------------------------------------------------------------------------

class TestCanonicalUpdateIndicators:

    def test_returns_200_with_message(self, client: TestClient, mock_config_service, auth_headers):
        mock_config_service.update_indicators = AsyncMock(return_value=None)
        r = client.put(
            f"{BASE}/test-client/indicators",
            json={
                "periods": {"5min": True},
                "oscillators": {"Relative Strength Index (14)": True},
                "movingaverages": {"Exponential Moving Average (10)": True},
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert "updated" in r.json()["message"]
        assert "test-client" in r.json()["message"]

    def test_invalid_key_returns_422(self, client: TestClient, auth_headers):
        r = client.put(
            f"{BASE}/test-client/indicators",
            json={"periods": {}, "oscillators": {"key\x00null": True}, "movingaverages": {}},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_path_traversal_client_id_returns_422(self, client: TestClient, auth_headers):
        r = client.put(
            f"{BASE}/../../etc/indicators",
            json={"periods": {}, "oscillators": {}, "movingaverages": {}},
            headers=auth_headers,
        )
        assert r.status_code in (404, 422)


# ---------------------------------------------------------------------------
# 12. Cross-cutting: error handlers and security headers
# ---------------------------------------------------------------------------

class TestCanonicalCrossCutting:

    def test_bot_not_found_returns_404_with_detail(
        self, client: TestClient, mock_bot_service, auth_headers
    ):
        mock_bot_service.run_bot = AsyncMock(side_effect=BotNotFoundError("missing"))
        r = client.post(f"{BASE}/test-client/bots/missing/run", headers=auth_headers)
        assert r.status_code == 404
        assert "missing" in r.json()["detail"]

    def test_bot_limit_returns_429_with_detail(
        self, client: TestClient, mock_bot_service, auth_headers
    ):
        mock_bot_service.create_bot = AsyncMock(side_effect=BotLimitExceededError(5))
        r = client.post(f"{BASE}/test-client/bots", headers=auth_headers)
        assert r.status_code == 429
        assert "5" in r.json()["detail"]

    def test_unhandled_exception_returns_500(
        self, client: TestClient, mock_bot_service, auth_headers
    ):
        mock_bot_service.get_botids = MagicMock(side_effect=RuntimeError("unexpected"))
        r = client.get(f"{BASE}/test-client/bots", headers=auth_headers)
        assert r.status_code == 500
        assert r.json()["detail"] == "Internal server error"

    def test_security_headers_present(self, client: TestClient, auth_headers):
        r = client.get(f"{BASE}/test-client/bots", headers=auth_headers)
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"
        assert r.headers.get("cache-control") == "no-store, no-cache, must-revalidate"
        assert "x-request-id" in r.headers

    def test_request_id_echoed(self, client: TestClient, auth_headers):
        r = client.get(
            f"{BASE}/test-client/bots",
            headers={**auth_headers, "X-Request-ID": "trace-xyz"},
        )
        assert r.headers.get("x-request-id") == "trace-xyz"


# ---------------------------------------------------------------------------
# Date-range filtering on history endpoints  [L8]
# ---------------------------------------------------------------------------

class TestDateRangeFiltering:

    def test_from_ts_forwarded_to_service(
        self, client: TestClient, mock_bot_service, auth_headers
    ):
        mock_bot_service.get_orders = AsyncMock(return_value=[])
        r = client.get(
            f"{BASE}/test-client/bots/bot-001/orders?from_ts=2025-01-01T00:00:00",
            headers=auth_headers,
        )
        assert r.status_code == 200
        mock_bot_service.get_orders.assert_called_once_with(
            "bot-001", "test-client", 100, 0, "2025-01-01T00:00:00", None
        )

    def test_to_ts_forwarded_to_service(
        self, client: TestClient, mock_bot_service, auth_headers
    ):
        mock_bot_service.get_trades = AsyncMock(return_value=[])
        r = client.get(
            f"{BASE}/test-client/bots/bot-001/trades?to_ts=2025-12-31T23:59:59",
            headers=auth_headers,
        )
        assert r.status_code == 200
        mock_bot_service.get_trades.assert_called_once_with(
            "bot-001", "test-client", 100, 0, None, "2025-12-31T23:59:59"
        )

    def test_from_ts_and_to_ts_combined(
        self, client: TestClient, mock_bot_service, auth_headers
    ):
        mock_bot_service.get_orders = AsyncMock(return_value=[])
        r = client.get(
            f"{BASE}/test-client/bots/bot-001/orders"
            "?from_ts=2025-01-01T00:00:00&to_ts=2025-06-30T23:59:59",
            headers=auth_headers,
        )
        assert r.status_code == 200
        mock_bot_service.get_orders.assert_called_once_with(
            "bot-001", "test-client", 100, 0,
            "2025-01-01T00:00:00", "2025-06-30T23:59:59",
        )

    def test_no_date_filter_passes_none(
        self, client: TestClient, mock_bot_service, auth_headers
    ):
        mock_bot_service.get_orders = AsyncMock(return_value=[])
        r = client.get(
            f"{BASE}/test-client/bots/bot-001/orders",
            headers=auth_headers,
        )
        assert r.status_code == 200
        mock_bot_service.get_orders.assert_called_once_with(
            "bot-001", "test-client", 100, 0, None, None
        )


# ---------------------------------------------------------------------------
# ClientParametersConfig rename  [L10]
# ---------------------------------------------------------------------------

class TestClientParametersConfigRename:

    def test_parameters_response_has_expected_fields(
        self, client: TestClient, mock_config_service, auth_headers
    ):
        """Verify the renamed model still serialises correctly."""
        r = client.get(f"{BASE}/test-client/parameters", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "exchanges" in data
        assert "symbols" in data
        assert "strategy" in data
        assert "version" in data

    def test_parameters_update_accepts_valid_body(
        self, client: TestClient, mock_config_service, auth_headers
    ):
        from unittest.mock import AsyncMock
        mock_config_service.update_parameters = AsyncMock(return_value=None)
        r = client.put(
            f"{BASE}/test-client/parameters",
            json={"exchanges": {"Binance": True}, "symbols": {}, "strategy": "arbitrage"},
            headers=auth_headers,
        )
        assert r.status_code == 200
