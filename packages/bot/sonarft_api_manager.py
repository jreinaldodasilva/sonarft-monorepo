"""
SonarFT API Manager Module
Exchange API abstraction (WebSocket/ccxt), caching, and market data.
"""

import asyncio
import logging
import time as _time
from typing import Union

from models import vwap
from sonarft_metrics import log_api_call

# Candle duration in seconds per timeframe — used as cache TTL
_TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


class SonarftApiManager:
    """
    SonarftApiManager class is responsible for managing external API calls.
    """

    def __init__(
        self,
        library: str,
        exchanges: list[str],
        exchanges_fees: list[dict[str, Union[str, float]]],
        logger: logging.Logger | None = None,
    ):
        # Initialize logger
        self.logger = logger or logging.getLogger(__name__)

        # Initialize library type (ccxt or ccxtpro)
        self.library = library
        self.load_api_library()

        # Initialize exchanges and their fees
        self.exchanges_list = exchanges
        self.exchanges_fees = exchanges_fees
        self.exchanges_instances = self.load_exchanges_instances(self.exchanges_list)
        self._exchange_map = {ex.id: ex for ex in self.exchanges_instances}

        self.exchanges_fees = exchanges_fees

        self.markets: dict[str, dict] = {}
        self._ohlcv_cache: dict[str, tuple[float, list]] = (
            {}
        )  # key -> (expires_at, data)
        self._order_book_cache: dict[str, tuple[float, dict]] = (
            {}
        )  # key -> (expires_at, order_book)
        self._ticker_cache: dict[str, tuple[float, dict]] = (
            {}
        )  # key -> (expires_at, ticker)

    def load_api_library(self):
        """
        Load the appropriate API library based on the library type.
        """

        if self.library == "ccxt":
            import ccxt as apilib

            self.__ccxt__ = True
            self.__ccxtpro__ = False
        elif self.library == "ccxtpro":
            import ccxt.pro as apilib

            self.__ccxt__ = False
            self.__ccxtpro__ = True

        self.apilib = apilib

    # ###  Manager Calls ***********************************************************************
    async def call_api_method(
        self, exchange_id, ccxt_method, ccxtpro_method, *args, **kwargs
    ):
        """
        Call the provided method for the given exchange_id.

        When running in ccxtpro (WebSocket) mode and the primary call fails,
        automatically falls back to the ccxt REST method if the two method
        names differ. This prevents silent degradation on WebSocket failures.
        """
        result = None
        exchange = self.get_exchange_by_id(exchange_id)

        # --- Primary call ---
        method = ccxt_method if self.__ccxt__ else ccxtpro_method
        method_call = getattr(exchange, method)
        try:
            if self.__ccxt__:
                loop = asyncio.get_running_loop()
                coro = loop.run_in_executor(None, lambda: method_call(*args, **kwargs))
            else:
                coro = method_call(*args, **kwargs)
            t0 = _time.monotonic()
            result = await asyncio.wait_for(coro, timeout=30.0)
            log_api_call(exchange_id, method, (_time.monotonic() - t0) * 1000, True)
            return result
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout (30s) calling {method} on {exchange_id}")
            log_api_call(exchange_id, method, 30000.0, False, "TimeoutError")
        except Exception as e:
            self.logger.error(f"Error calling method {method}: {e}")
            log_api_call(exchange_id, method, 0.0, False, str(e)[:120])

        # --- REST fallback (ccxtpro only, and only when methods differ) ---
        if self.__ccxtpro__ and ccxt_method != ccxtpro_method:
            self.logger.warning(
                f"Falling back to REST ({ccxt_method}) for {exchange_id} "
                f"after ccxtpro ({ccxtpro_method}) failure"
            )
            try:
                import ccxt as _ccxt_rest
                rest_exchange = _ccxt_rest.__dict__.get(exchange_id)
                if rest_exchange is None:
                    self.logger.error(
                        f"REST fallback: exchange '{exchange_id}' not found in ccxt"
                    )
                    return None
                # Reuse credentials from the ccxtpro instance
                ws_exchange = exchange
                rest_instance = rest_exchange({
                    "enableRateLimit": True,
                    "apiKey": getattr(ws_exchange, "apiKey", ""),
                    "secret": getattr(ws_exchange, "secret", ""),
                    "password": getattr(ws_exchange, "password", ""),
                })
                rest_method_call = getattr(rest_instance, ccxt_method)
                loop = asyncio.get_running_loop()
                t0 = _time.monotonic()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: rest_method_call(*args, **kwargs)),
                    timeout=30.0,
                )
                log_api_call(
                    exchange_id, ccxt_method,
                    (_time.monotonic() - t0) * 1000, True, "rest_fallback"
                )
            except Exception as fallback_err:
                self.logger.error(
                    f"REST fallback also failed for {exchange_id} {ccxt_method}: {fallback_err}"
                )
                log_api_call(exchange_id, ccxt_method, 0.0, False, str(fallback_err)[:120])

        return result

    # ###  Load and Setup ***********************************************************************
    def load_exchanges_instances(self, exchanges: list[str]) -> list:
        """
        Load instances of the provided exchanges.
        """
        return [
            getattr(self.apilib, exchange)({"enableRateLimit": True})
            for exchange in exchanges
        ]

    async def load_markets(self, exchange_id):
        """Load and cache markets for a single exchange. Safe to call multiple times."""
        if exchange_id in self.markets:
            return self.markets[exchange_id]
        try:
            exchange = self.get_exchange_by_id(exchange_id)
            # load_markets is a REST initialisation call in both ccxt and ccxtpro
            # — call directly to surface errors instead of silently returning None
            exchange_markets = await asyncio.wait_for(
                exchange.load_markets(), timeout=30.0
            )
            if exchange_markets:
                self.markets[exchange_id] = exchange_markets
                self.logger.info(
                    f"Markets loaded for {exchange_id}: {len(exchange_markets)} symbols"
                )
            else:
                self.logger.warning(f"load_markets returned empty for {exchange_id}")
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout loading markets for {exchange_id}")
        except Exception as e:
            self.logger.error(f"Error loading markets for {exchange_id}: {e}")
        return self.markets.get(exchange_id, {})

    async def load_all_markets(self):
        """Load markets for all configured exchanges at startup."""
        await asyncio.gather(
            *[self.load_markets(exchange.id) for exchange in self.exchanges_instances]
        )
        loaded_count = len([ex_id for ex_id in self.markets if self.markets[ex_id]])
        self.logger.info(
            f"Markets loaded for {loaded_count}/{len(self.exchanges_instances)} exchange(s)"
        )

    async def refresh_fees(self) -> None:
        """Refresh fee rates from the exchange API for all configured exchanges.

        Replaces the in-memory fee list with live rates fetched via
        fetch_trading_fees(). Falls back to the existing config rates if the
        exchange does not support the endpoint or the call fails.

        Call at startup and periodically (e.g. every 24 hours) to keep fee
        rates current. Stale fees cause the bot to execute unprofitable trades.
        """
        for exchange in self.exchanges_instances:
            try:
                loop = asyncio.get_running_loop()
                fees = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, lambda ex=exchange: ex.fetch_trading_fees()
                    ),
                    timeout=30.0,
                )
                if not fees:
                    self.logger.warning(
                        f"refresh_fees: empty response from {exchange.id} — keeping existing rates"
                    )
                    continue
                # ccxt returns {symbol: {maker: float, taker: float, ...}}
                # We update the flat per-exchange fee entry used by get_buy/sell_fee().
                # Use the minimum maker fee across all symbols as the exchange-level rate.
                maker_fees = [
                    v.get("maker", 0.0)
                    for v in fees.values()
                    if isinstance(v, dict) and v.get("maker") is not None
                ]
                taker_fees = [
                    v.get("taker", 0.0)
                    for v in fees.values()
                    if isinstance(v, dict) and v.get("taker") is not None
                ]
                if not maker_fees and not taker_fees:
                    self.logger.warning(
                        f"refresh_fees: no maker/taker fees found for {exchange.id}"
                    )
                    continue
                maker_rate = min(maker_fees) if maker_fees else None
                taker_rate = min(taker_fees) if taker_fees else None
                # Update the in-memory fee entry for this exchange
                updated = False
                for fee_entry in self.exchanges_fees:
                    if fee_entry.get("exchange") == exchange.id:
                        if maker_rate is not None:
                            fee_entry["maker_buy_fee"] = maker_rate
                            fee_entry["maker_sell_fee"] = maker_rate
                        if taker_rate is not None:
                            fee_entry["buy_fee"] = taker_rate
                            fee_entry["sell_fee"] = taker_rate
                        updated = True
                        break
                if updated:
                    self.logger.info(
                        f"Fee rates refreshed for {exchange.id}: "
                        f"maker={maker_rate}, taker={taker_rate}"
                    )
                else:
                    self.logger.warning(
                        f"refresh_fees: no fee entry found for {exchange.id} in config — skipping"
                    )
            except asyncio.TimeoutError:
                self.logger.warning(
                    f"refresh_fees: timeout fetching fees from {exchange.id} — keeping existing rates"
                )
            except Exception as e:
                self.logger.warning(
                    f"refresh_fees: failed for {exchange.id}: {e} — keeping existing rates"
                )

    def set_api_keys(self, exchange_id: str, api_key: str, secret: str, password: str):
        """
        Set the api keys for the given exchange_id.
        """
        exchange = self.get_exchange_by_id(exchange_id)
        exchange.apiKey = api_key
        exchange.secret = secret
        exchange.password = password
        exchange.options["defaultType"] = "spot"

    # ###  Action ***********************************************************************
    async def get_balance(self, exchange_id: str) -> dict[str, Union[str, float]]:
        """
        Get the balance for the given exchange_id.
        """
        balance = await self.call_api_method(
            exchange_id, "fetch_balance", "watch_balance"
        )
        return balance

    async def create_order(
        self,
        exchange_id: str,
        base: str,
        quote: str,
        side: str,
        amount: float,
        price: float,
    ) -> dict[str, Union[str, float]]:
        """
        Create an order for the given exchange_id, base, quote, side, amount and price.
        """
        try:
            symbol = f"{base}/{quote}"
            order = await self.call_api_method(
                exchange_id,
                "create_order",
                "create_order",
                symbol,
                "limit",
                side,
                amount,
                price,
            )
            self.logger.info(
                f"Created order {order['id']} on {exchange_id} for {amount} {base} at {price} {quote}"
            )
        except Exception as e:
            self.logger.error(f"Error creating order: {e}")
            order = None
        return order

    async def cancel_order(
        self, exchange_id: str, order_id: str, base: str, quote: str
    ) -> dict | None:
        """
        Cancel an open order on the given exchange.
        Returns the cancellation result dict, or None on failure.
        """
        try:
            symbol = f"{base}/{quote}"
            result = await self.call_api_method(
                exchange_id, "cancel_order", "cancel_order", order_id, symbol
            )
            self.logger.info(f"Cancelled order {order_id} on {exchange_id}")
            return result
        except Exception as e:
            self.logger.error(
                f"Error cancelling order {order_id} on {exchange_id}: {e}"
            )
            return None

    async def close_exchange(self, exchange_id: str):
        """
        Close exchange instance
        """
        exchange = self.get_exchange_by_id(exchange_id)
        await exchange.close()

    async def watch_orders(self, exchange_id, base, quote):

        symbol = f"{base}/{quote}"
        orders = await self.call_api_method(
            exchange_id, "fetch_orders", "watch_orders", symbol
        )

        return orders

    # ###  API Get ***********************************************************************
    # TODO: See if its possible(trust) to use api to get fees
    def get_buy_fee(
        self, exchange_id: str, order_type: str = "limit"
    ) -> Union[float, None]:
        """
        Get the buy fee for the given exchange_id.
        Uses maker_buy_fee for limit orders if available, falls back to buy_fee.
        """
        for exchange_fee in self.exchanges_fees:
            if exchange_fee["exchange"] == exchange_id:
                if order_type == "limit" and "maker_buy_fee" in exchange_fee:
                    return exchange_fee["maker_buy_fee"]
                return exchange_fee["buy_fee"]
        return None

    def get_sell_fee(
        self, exchange_id: str, order_type: str = "limit"
    ) -> Union[float, None]:
        """
        Get the sell fee for the given exchange_id.
        Uses maker_sell_fee for limit orders if available, falls back to sell_fee.
        """
        for exchange_fee in self.exchanges_fees:
            if exchange_fee["exchange"] == exchange_id:
                if order_type == "limit" and "maker_sell_fee" in exchange_fee:
                    return exchange_fee["maker_sell_fee"]
                return exchange_fee["sell_fee"]
        return None

    async def get_order_book(
        self, exchange_id: str, base: str, quote: str
    ) -> dict[str, Union[str, list[list[float]]]]:
        """Get the order book with a 2-second TTL cache to avoid redundant fetches per cycle.
        Cache is capped at 500 entries with LRU eviction to prevent unbounded memory growth.
        """
        symbol = f"{base}/{quote}"
        cache_key = f"{exchange_id}:{symbol}"
        now = _time.monotonic()
        cached = self._order_book_cache.get(cache_key)
        if cached and now < cached[0]:
            return cached[1]
        order_book = await self.call_api_method(
            exchange_id, "fetch_order_book", "watch_order_book", symbol
        )
        if order_book:
            if len(self._order_book_cache) >= 500:
                oldest_key = next(iter(self._order_book_cache))
                del self._order_book_cache[oldest_key]
            self._order_book_cache[cache_key] = (now + 2.0, order_book)
        return order_book

    async def _get_ticker(self, exchange_id: str, base: str, quote: str) -> dict | None:
        """Fetch ticker with a 2-second TTL cache.
        Cache is capped at 500 entries with LRU eviction to prevent unbounded memory growth.
        """
        symbol = f"{base}/{quote}"
        cache_key = f"{exchange_id}:{symbol}"
        now = _time.monotonic()
        cached = self._ticker_cache.get(cache_key)
        if cached and now < cached[0]:
            return cached[1]
        ticker = await self.call_api_method(
            exchange_id, "fetch_ticker", "watch_ticker", symbol
        )
        if ticker:
            if len(self._ticker_cache) >= 500:
                oldest_key = next(iter(self._ticker_cache))
                del self._ticker_cache[oldest_key]
            self._ticker_cache[cache_key] = (now + 2.0, ticker)
        return ticker

    async def get_trading_volume(
        self, exchange_id: str, base: str, quote: str
    ) -> float | None:
        """
        Get the trading volume for the given exchange_id, base and quote.
        """
        ticker = await self._get_ticker(exchange_id, base, quote)
        if ticker is None:
            return None
        return ticker["baseVolume"]

    async def get_last_price(
        self, exchange_id: str, base: str, quote: str
    ) -> float | None:
        """
        Get the last price for the given exchange_id, base and quote.
        """
        ticker = await self._get_ticker(exchange_id, base, quote)
        if ticker is None:
            return None
        return ticker["last"]

    async def get_ohlcv_history(
        self, exchange_id: str, base: str, quote: str, timeframe, since, limit
    ) -> list:
        """Fetch OHLCV history with a per-candle TTL cache (max 500 entries, LRU eviction).
        Cache key ignores limit — a cached response with >= requested candles is reused.
        """
        symbol = f"{base}/{quote}"
        cache_key = f"{exchange_id}:{symbol}:{timeframe}"
        ttl = _TIMEFRAME_SECONDS.get(timeframe, 60)
        now = _time.monotonic()
        cached = self._ohlcv_cache.get(cache_key)
        if cached and now < cached[0] and len(cached[1]) >= limit:
            return cached[1][-limit:] if limit else cached[1]
        # Fetch with requested limit (or reuse a larger cached set next time)
        history = await self.call_api_method(
            exchange_id, "fetch_ohlcv", "fetch_ohlcv", symbol, timeframe, since, limit
        )
        if history:
            if len(self._ohlcv_cache) >= 500:
                oldest_key = next(iter(self._ohlcv_cache))
                del self._ohlcv_cache[oldest_key]
            # Store full response — subsequent calls with smaller limit get a slice
            existing = self._ohlcv_cache.get(cache_key)
            if not existing or len(history) >= len(existing[1]):
                self._ohlcv_cache[cache_key] = (now + ttl, history)
        return history or []

    # TODO: Pass since and limit through to call_api_method once the API contract is confirmed.
    async def get_trades_history(
        self, exchange_id: str, base: str, quote: str
    ) -> list[dict[str, Union[int, float]]]:
        """
        Get the trade history for the given exchange_id, base and quote.
        Note: since and limit parameters are not yet forwarded to the exchange call.
        """
        symbol = f"{base}/{quote}"
        trades_history = await self.call_api_method(
            exchange_id, "fetch_trades", "fetch_trades", symbol
        )
        return trades_history

    def get_symbol_precision(
        self, exchange_id: str, base: str, quote: str
    ) -> dict | None:
        """Return precision rules for a symbol from loaded market data, or None if unavailable."""
        symbol = f"{base}/{quote}"
        market = self.markets.get(exchange_id, {}).get(symbol)
        if not market:
            return None
        precision = market.get("precision", {})
        market.get("limits", {})
        price_prec = precision.get("price")
        amount_prec = precision.get("amount")
        if price_prec is None or amount_prec is None:
            return None

        # Convert to decimal places if given as a tick size (e.g. 0.01 -> 2)
        def _to_dp(v):
            if v is None:
                return 8
            if isinstance(v, int):
                return v
            s = f"{v:.10f}".rstrip("0")
            return len(s.split(".")[-1]) if "." in s else 0

        return {
            "prices_precision": _to_dp(price_prec),
            "buy_amount_precision": _to_dp(amount_prec),
            "sell_amount_precision": _to_dp(amount_prec),
            "cost_precision": 8,
            "fee_precision": 8,
        }

    def get_exchange_by_id(self, exchange_id: str):
        """Get the exchange instance by its ID (O(1) dict lookup)."""
        return self._exchange_map.get(exchange_id)

    async def get_latest_prices(
        self, base: str, quote: str, weight
    ) -> list[tuple[str, float, float, float, str]]:
        """Get the latest prices for the given base and quote across all exchanges."""
        symbol = f"{base}/{quote}"
        prices = []

        async def _fetch_exchange(exchange):
            try:
                cached = self.markets.get(exchange.id, {})
                if symbol not in cached:
                    self.logger.warning(f"{symbol} is not available on {exchange.id}.")
                    return None
                # Route through cached methods so the order book and ticker
                # are available to subsequent indicator fetches in the same cycle.
                order_book, ticker = await asyncio.gather(
                    self.get_order_book(exchange.id, base, quote),
                    self._get_ticker(exchange.id, base, quote),
                )
                if (
                    order_book is None
                    or order_book["asks"] is None
                    or order_book["bids"] is None
                ):
                    self.logger.warning(
                        f"Order book for {symbol} in {exchange.id} is invalid."
                    )
                    return None
                bid_vwap, ask_vwap = self.get_weighted_prices(weight, order_book)
                if (
                    ticker["ask"]
                    and ticker["ask"] != 0
                    and ticker["bid"]
                    and ticker["bid"] != 0
                ):
                    return (exchange.id, bid_vwap, ask_vwap, ticker["last"], symbol)
                self.logger.warning(f"Ticker for {symbol} in {exchange.id} is invalid.")
                return None
            except Exception as e:
                self.logger.error(
                    f"Error fetching latest price for {exchange.id} {symbol}: {e}"
                )
                return None

        results = await asyncio.gather(
            *[_fetch_exchange(ex) for ex in self.exchanges_instances]
        )
        prices = [r for r in results if r is not None]
        return prices

    def get_weighted_prices(self, depth: int, order_book: dict) -> tuple[float, float]:
        """Calculate the volume-weighted average bid and ask prices. Delegates to shared vwap()."""
        bid_vwap = vwap(order_book["bids"], depth)
        ask_vwap = vwap(order_book["asks"], depth)
        return bid_vwap, ask_vwap

    # ###  support methods ***********************************************************************

    async def wait_for_rate_limit(self, exchange):
        """Kept for backward compatibility. Rate limiting is handled internally by ccxt
        via enableRateLimit=True set on each exchange instance."""
        rate_limit = exchange.rateLimit / 1000
        await exchange.sleep(rate_limit)
