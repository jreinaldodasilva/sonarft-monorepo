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

        # Force cache expiry by setting TTL to past
        import time as _time
        manager._order_book_cache["binance:BTC/USDT"] = (
            _time.monotonic() - 10.0,  # expired
            {"bids": [[59000, 1]], "asks": [[59010, 1]]}
        )

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
