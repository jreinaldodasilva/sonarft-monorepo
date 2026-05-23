"""
Unit tests for SonarftApiManager — call_api_method dispatch and WS→REST fallback.
Covers T-07 (WS→REST fallback) and partial Q-16 (ApiManager test coverage).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(library: str = "ccxtpro"):
    """Build a SonarftApiManager with mocked exchange instances."""
    from sonarft_api_manager import SonarftApiManager

    manager = SonarftApiManager.__new__(SonarftApiManager)
    manager.logger = MagicMock()
    manager.library = library
    manager.__ccxt__ = (library == "ccxt")
    manager.__ccxtpro__ = (library == "ccxtpro")
    manager.exchanges_list = ["binance"]
    manager.exchanges_fees = []
    manager.markets = {}
    manager._ohlcv_cache = {}
    manager._order_book_cache = {}
    manager._ticker_cache = {}

    # Mock exchange instance
    mock_exchange = MagicMock()
    mock_exchange.id = "binance"
    mock_exchange.apiKey = "test_key"
    mock_exchange.secret = "test_secret"
    mock_exchange.password = ""
    manager.exchanges_instances = [mock_exchange]
    manager._exchange_map = {"binance": mock_exchange}

    return manager, mock_exchange


# ---------------------------------------------------------------------------
# call_api_method — ccxt (REST) path
# ---------------------------------------------------------------------------

class TestCallApiMethodCcxt:

    @pytest.mark.asyncio
    async def test_ccxt_uses_thread_executor(self):
        """ccxt path must run the method in a thread executor (sync call)."""
        manager, exchange = _make_manager(library="ccxt")
        exchange.fetch_order_book = MagicMock(return_value={"bids": [], "asks": []})

        result = await manager.call_api_method(
            "binance", "fetch_order_book", "watch_order_book", "BTC/USDT"
        )

        exchange.fetch_order_book.assert_called_once_with("BTC/USDT")
        assert result == {"bids": [], "asks": []}

    @pytest.mark.asyncio
    async def test_ccxt_returns_none_on_exception(self):
        manager, exchange = _make_manager(library="ccxt")
        exchange.fetch_order_book = MagicMock(side_effect=RuntimeError("network error"))

        result = await manager.call_api_method(
            "binance", "fetch_order_book", "watch_order_book", "BTC/USDT"
        )

        assert result is None
        manager.logger.exception.assert_called()


# ---------------------------------------------------------------------------
# call_api_method — ccxtpro (WebSocket) path
# ---------------------------------------------------------------------------

class TestCallApiMethodCcxtpro:

    @pytest.mark.asyncio
    async def test_ccxtpro_uses_async_call(self):
        """ccxtpro path must await the method directly."""
        manager, exchange = _make_manager(library="ccxtpro")
        exchange.watch_order_book = AsyncMock(return_value={"bids": [[60000, 1]], "asks": [[60010, 1]]})

        result = await manager.call_api_method(
            "binance", "fetch_order_book", "watch_order_book", "BTC/USDT"
        )

        exchange.watch_order_book.assert_called_once_with("BTC/USDT")
        assert result["bids"] == [[60000, 1]]

    @pytest.mark.asyncio
    async def test_ccxtpro_returns_none_on_exception_no_fallback_when_methods_same(self):
        """When ccxt_method == ccxtpro_method, no REST fallback is attempted."""
        manager, exchange = _make_manager(library="ccxtpro")
        exchange.create_order = AsyncMock(side_effect=RuntimeError("ws error"))

        result = await manager.call_api_method(
            "binance", "create_order", "create_order",
            "BTC/USDT", "limit", "buy", 1.0, 60000.0
        )

        assert result is None
        # No fallback warning logged since methods are identical
        warning_calls = [str(c) for c in manager.logger.warning.call_args_list]
        assert not any("Falling back" in w for w in warning_calls)


# ---------------------------------------------------------------------------
# T-07: WS→REST fallback
# ---------------------------------------------------------------------------

class TestWsRestFallback:

    @pytest.mark.asyncio
    async def test_fallback_triggered_when_ws_fails_and_methods_differ(self):
        """When ccxtpro call fails and methods differ, REST fallback is attempted."""
        manager, exchange = _make_manager(library="ccxtpro")
        exchange.watch_order_book = AsyncMock(side_effect=RuntimeError("ws disconnected"))

        fallback_result = {"bids": [[59000, 1]], "asks": [[59010, 1]]}

        # Mock the ccxt REST module and exchange class
        mock_rest_exchange_instance = MagicMock()
        mock_rest_exchange_instance.fetch_order_book = MagicMock(return_value=fallback_result)
        mock_rest_exchange_class = MagicMock(return_value=mock_rest_exchange_instance)

        with patch.dict("sys.modules", {}):
            with patch("sonarft_api_manager.asyncio.get_running_loop") as mock_loop:
                # Make run_in_executor return the fallback result directly
                loop = asyncio.get_event_loop()
                mock_loop.return_value = loop

                import ccxt as real_ccxt
                with patch.dict(vars(real_ccxt), {"binance": mock_rest_exchange_class}):
                    with patch("sonarft_api_manager.__import__", create=True):
                        # Patch the import inside call_api_method
                        with patch("builtins.__import__") as mock_import:
                            def side_effect(name, *args, **kwargs):
                                if name == "ccxt":
                                    mock_ccxt = MagicMock()
                                    mock_ccxt.__dict__ = {"binance": mock_rest_exchange_class}
                                    mock_ccxt.get = lambda k, d=None: mock_ccxt.__dict__.get(k, d)
                                    return mock_ccxt
                                return real_import(name, *args, **kwargs)
                            real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
                            mock_import.side_effect = side_effect

                            await manager.call_api_method(
                                "binance", "fetch_order_book", "watch_order_book", "BTC/USDT"
                            )

        # Fallback warning must have been logged
        warning_calls = [str(c) for c in manager.logger.warning.call_args_list]
        assert any("Falling back" in w for w in warning_calls)

    @pytest.mark.asyncio
    async def test_no_fallback_when_ccxt_mode(self):
        """In ccxt mode, no fallback logic runs (already using REST)."""
        manager, exchange = _make_manager(library="ccxt")
        exchange.fetch_order_book = MagicMock(side_effect=RuntimeError("rest error"))

        result = await manager.call_api_method(
            "binance", "fetch_order_book", "watch_order_book", "BTC/USDT"
        )

        assert result is None
        # No fallback warning
        warning_calls = [str(c) for c in manager.logger.warning.call_args_list]
        assert not any("Falling back" in w for w in warning_calls)

    @pytest.mark.asyncio
    async def test_no_fallback_when_methods_identical(self):
        """When ccxt_method == ccxtpro_method, no fallback is attempted even in ccxtpro mode."""
        manager, exchange = _make_manager(library="ccxtpro")
        exchange.fetch_ohlcv = AsyncMock(side_effect=RuntimeError("error"))

        result = await manager.call_api_method(
            "binance", "fetch_ohlcv", "fetch_ohlcv", "BTC/USDT", "1m", None, 50
        )

        assert result is None
        warning_calls = [str(c) for c in manager.logger.warning.call_args_list]
        assert not any("Falling back" in w for w in warning_calls)

    @pytest.mark.asyncio
    async def test_rest_fallback_instance_closed_after_use(self):
        """T12: the temporary REST instance must be closed after the fallback call
        regardless of success or failure, to release the underlying HTTP session."""
        from unittest.mock import patch, MagicMock, AsyncMock
        manager, exchange = _make_manager(library="ccxtpro")
        exchange.watch_order_book = AsyncMock(side_effect=RuntimeError("ws error"))

        close_called = {"n": 0}
        mock_rest_instance = MagicMock()
        mock_rest_instance.fetch_order_book = MagicMock(
            return_value={"bids": [[59000, 1]], "asks": [[59010, 1]]}
        )
        def track_close():
            close_called["n"] += 1
        mock_rest_instance.close = track_close
        mock_rest_class = MagicMock(return_value=mock_rest_instance)

        import ccxt as real_ccxt
        with patch.dict(vars(real_ccxt), {"binance": mock_rest_class}):
            with patch("builtins.__import__") as mock_import:
                real_import = __import__
                def side_effect(name, *args, **kwargs):
                    if name == "ccxt":
                        m = MagicMock()
                        m.__dict__ = {"binance": mock_rest_class}
                        return m
                    return real_import(name, *args, **kwargs)
                mock_import.side_effect = side_effect

                await manager.call_api_method(
                    "binance", "fetch_order_book", "watch_order_book", "BTC/USDT"
                )

        # close() must have been called exactly once
        assert close_called["n"] == 1, (
            f"rest_instance.close() called {close_called['n']} times, expected 1"
        )

    @pytest.mark.asyncio
    async def test_rest_fallback_instance_closed_even_on_failure(self):
        """T12: close must be called even when the fallback call itself fails."""
        from unittest.mock import patch, MagicMock, AsyncMock
        manager, exchange = _make_manager(library="ccxtpro")
        exchange.watch_order_book = AsyncMock(side_effect=RuntimeError("ws error"))

        close_called = {"n": 0}
        mock_rest_instance = MagicMock()
        mock_rest_instance.fetch_order_book = MagicMock(
            side_effect=RuntimeError("rest also failed")
        )
        def track_close():
            close_called["n"] += 1
        mock_rest_instance.close = track_close
        mock_rest_class = MagicMock(return_value=mock_rest_instance)

        import ccxt as real_ccxt
        with patch.dict(vars(real_ccxt), {"binance": mock_rest_class}):
            with patch("builtins.__import__") as mock_import:
                real_import = __import__
                def side_effect(name, *args, **kwargs):
                    if name == "ccxt":
                        m = MagicMock()
                        m.__dict__ = {"binance": mock_rest_class}
                        return m
                    return real_import(name, *args, **kwargs)
                mock_import.side_effect = side_effect

                result = await manager.call_api_method(
                    "binance", "fetch_order_book", "watch_order_book", "BTC/USDT"
                )

        assert result is None  # fallback failed gracefully
        assert close_called["n"] == 1  # close still called


# ---------------------------------------------------------------------------
# Order book cache
# ---------------------------------------------------------------------------

class TestOrderBookCache:

    @pytest.mark.asyncio
    async def test_cache_hit_does_not_call_api(self):
        manager, exchange = _make_manager(library="ccxtpro")
        exchange.watch_order_book = AsyncMock(return_value={"bids": [[60000, 1]], "asks": [[60010, 1]]})

        # First call — populates cache
        await manager.get_order_book("binance", "BTC", "USDT")
        # Second call — should be served from cache
        await manager.get_order_book("binance", "BTC", "USDT")

        assert exchange.watch_order_book.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_miss_calls_api(self):
        manager, exchange = _make_manager(library="ccxtpro")
        exchange.watch_order_book = AsyncMock(return_value={"bids": [[60000, 1]], "asks": [[60010, 1]]})

        # With TTLCache, simulate a miss by simply not pre-populating the cache
        # (the key is absent, so get_order_book must call the API)
        assert "binance:BTC/USDT" not in manager._order_book_cache

        result = await manager.get_order_book("binance", "BTC", "USDT")

        exchange.watch_order_book.assert_called_once()
        assert result["bids"] == [[60000, 1]]


# ---------------------------------------------------------------------------
# T-13 (extended): get_latest_prices and get_weighted_prices
# ---------------------------------------------------------------------------

class TestGetLatestPrices:

    def _make_manager_with_markets(self):
        from sonarft_api_manager import SonarftApiManager
        manager = SonarftApiManager.__new__(SonarftApiManager)
        manager.logger = MagicMock()
        manager.__ccxt__ = True
        manager.__ccxtpro__ = False
        manager.markets = {'binance': {'BTC/USDT': {}}}
        manager._order_book_cache = {}
        manager._ticker_cache = {}

        mock_exchange = MagicMock()
        mock_exchange.id = 'binance'
        mock_exchange.fetch_order_book = MagicMock(return_value={
            'bids': [[60000.0, 1.0], [59990.0, 2.0]],
            'asks': [[60010.0, 1.5], [60020.0, 0.5]],
        })
        mock_exchange.fetch_ticker = MagicMock(return_value={
            'last': 60005.0, 'bid': 60000.0, 'ask': 60010.0, 'baseVolume': 100.0
        })
        manager.exchanges_instances = [mock_exchange]
        manager._exchange_map = {'binance': mock_exchange}
        return manager, mock_exchange

    @pytest.mark.asyncio
    async def test_returns_price_tuple_for_valid_symbol(self):
        manager, _ = self._make_manager_with_markets()
        prices = await manager.get_latest_prices('BTC', 'USDT', weight=2)
        assert len(prices) == 1
        exchange_id, bid_vwap, ask_vwap, last, symbol = prices[0]
        assert exchange_id == 'binance'
        assert bid_vwap > 0
        assert ask_vwap > 0
        assert symbol == 'BTC/USDT'

    @pytest.mark.asyncio
    async def test_populates_order_book_cache(self):
        """get_latest_prices() must populate _order_book_cache via get_order_book()."""
        manager, _ = self._make_manager_with_markets()
        assert 'binance:BTC/USDT' not in manager._order_book_cache
        await manager.get_latest_prices('BTC', 'USDT', weight=2)
        assert 'binance:BTC/USDT' in manager._order_book_cache

    @pytest.mark.asyncio
    async def test_skips_symbol_not_in_markets(self):
        manager, _ = self._make_manager_with_markets()
        prices = await manager.get_latest_prices('ETH', 'USDT', weight=2)
        assert prices == []


class TestGetWeightedPrices:

    def _make_manager(self):
        from sonarft_api_manager import SonarftApiManager
        manager = SonarftApiManager.__new__(SonarftApiManager)
        return manager

    def test_correct_vwap_formula(self):
        manager = self._make_manager()
        order_book = {
            'bids': [[60000.0, 1.0], [59990.0, 2.0]],
            'asks': [[60010.0, 1.5], [60020.0, 0.5]],
        }
        bid_vwap, ask_vwap = manager.get_weighted_prices(2, order_book)
        expected_bid = (60000.0 * 1.0 + 59990.0 * 2.0) / 3.0
        expected_ask = (60010.0 * 1.5 + 60020.0 * 0.5) / 2.0
        assert abs(bid_vwap - expected_bid) < 1e-9
        assert abs(ask_vwap - expected_ask) < 1e-9

    def test_zero_volume_returns_zero(self):
        manager = self._make_manager()
        order_book = {'bids': [[60000.0, 0.0]], 'asks': [[60010.0, 0.0]]}
        bid_vwap, ask_vwap = manager.get_weighted_prices(1, order_book)
        assert bid_vwap == 0.0
        assert ask_vwap == 0.0


# ---------------------------------------------------------------------------
# T03: create_order recovery check after timeout / None return
# ---------------------------------------------------------------------------

class TestCreateOrderRecovery:
    """T03: when create_order's primary call returns None (timeout or error),
    fetch_open_orders is queried and a matching recent order is returned
    instead of silently abandoning it."""

    def _make_api(self, library="ccxt"):
        """Build a minimal SonarftApiManager with mocked exchange."""
        from sonarft_api_manager import SonarftApiManager
        from unittest.mock import AsyncMock, MagicMock, patch
        import ccxt

        api = SonarftApiManager.__new__(SonarftApiManager)
        api.logger = MagicMock()
        api.library = library
        api.__ccxt__ = (library == "ccxt")
        api.__ccxtpro__ = (library == "ccxtpro")
        api.exchanges_fees = []
        api.markets = {}
        api._ohlcv_cache = {}
        api._order_book_cache = {}
        api._ticker_cache = {}

        mock_exchange = MagicMock()
        mock_exchange.id = "binance"
        api.exchanges_instances = [mock_exchange]
        api._exchange_map = {"binance": mock_exchange}
        return api

    @pytest.mark.asyncio
    async def test_successful_placement_returns_order_no_recovery(self):
        """Normal path: order placed successfully — no recovery check needed."""
        from unittest.mock import AsyncMock, patch
        api = self._make_api()
        order = {"id": "order_001", "side": "buy", "amount": 1.0, "price": 60000.0}
        with patch.object(api, "call_api_method", new=AsyncMock(return_value=order)) as mock_call:
            result = await api.create_order("binance", "BTC", "USDT", "buy", 1.0, 60000.0)
            assert result == order
            # call_api_method called once (placement only, no recovery)
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_triggers_recovery_check(self):
        """When primary call returns None, fetch_open_orders must be called."""
        from unittest.mock import AsyncMock, call
        api = self._make_api()

        now_ms = int(__import__("time").time() * 1000)
        recovered_order = {
            "id": "order_recovered",
            "side": "buy",
            "amount": 1.0,
            "price": 60000.0,
            "timestamp": now_ms,
        }

        call_results = [None, [recovered_order]]  # first=placement fails, second=open orders
        api.call_api_method = AsyncMock(side_effect=call_results)

        result = await api.create_order("binance", "BTC", "USDT", "buy", 1.0, 60000.0)

        assert result == recovered_order
        assert api.call_api_method.call_count == 2

    @pytest.mark.asyncio
    async def test_recovery_returns_none_when_no_matching_order(self):
        """If open orders exist but none match, return None (order truly failed)."""
        from unittest.mock import AsyncMock
        api = self._make_api()

        now_ms = int(__import__("time").time() * 1000)
        unrelated_order = {
            "id": "order_other",
            "side": "sell",          # wrong side
            "amount": 1.0,
            "price": 60000.0,
            "timestamp": now_ms,
        }

        api.call_api_method = AsyncMock(side_effect=[None, [unrelated_order]])
        result = await api.create_order("binance", "BTC", "USDT", "buy", 1.0, 60000.0)
        assert result is None

    @pytest.mark.asyncio
    async def test_recovery_ignores_orders_older_than_60s(self):
        """Orders placed more than 60 seconds ago must not be recovered."""
        from unittest.mock import AsyncMock
        api = self._make_api()

        stale_ms = int((__import__("time").time() - 120) * 1000)  # 2 minutes ago
        stale_order = {
            "id": "order_stale",
            "side": "buy",
            "amount": 1.0,
            "price": 60000.0,
            "timestamp": stale_ms,
        }

        api.call_api_method = AsyncMock(side_effect=[None, [stale_order]])
        result = await api.create_order("binance", "BTC", "USDT", "buy", 1.0, 60000.0)
        assert result is None

    @pytest.mark.asyncio
    async def test_recovery_returns_none_when_open_orders_empty(self):
        """If fetch_open_orders returns empty list, return None."""
        from unittest.mock import AsyncMock
        api = self._make_api()
        api.call_api_method = AsyncMock(side_effect=[None, []])
        result = await api.create_order("binance", "BTC", "USDT", "buy", 1.0, 60000.0)
        assert result is None

    @pytest.mark.asyncio
    async def test_recovery_check_fails_gracefully(self):
        """If fetch_open_orders itself raises, return None without propagating."""
        from unittest.mock import AsyncMock
        api = self._make_api()
        api.call_api_method = AsyncMock(side_effect=[None, Exception("network error")])
        result = await api.create_order("binance", "BTC", "USDT", "buy", 1.0, 60000.0)
        assert result is None
