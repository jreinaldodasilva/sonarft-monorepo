"""
SonarFT Shared Market Cache (T31)

A process-level cache shared across all SonarftApiManager instances in the
same process. When multiple bots trade the same symbol on the same exchange,
they share one OHLCV/order-book/ticker fetch per TTL window instead of each
bot fetching independently.

Usage:
    from shared_cache import get_shared_cache
    cache = get_shared_cache()
    # Pass to SonarftApiManager via use_shared_cache=cache
"""
from __future__ import annotations

import asyncio
from typing import Any

from cachetools import TTLCache

# Default TTLs matching SonarftApiManager's per-instance caches
_OHLCV_TTL_DEFAULT = 60      # 1m candle duration
_ORDER_BOOK_TTL = 2.0
_TICKER_TTL = 2.0
_MAX_SIZE = 1000              # larger than per-bot 500 to accommodate N bots


class SharedMarketCache:
    """Process-level market data cache shared across all SonarftApiManager instances.

    Thread-safe via asyncio.Lock (all access is from the asyncio event loop).
    Uses TTLCache for automatic expiry and LRU eviction.

    Attributes:
        ohlcv:       TTLCache for OHLCV history (key: exchange:symbol:timeframe)
        order_book:  TTLCache for order books (key: exchange:symbol)
        ticker:      TTLCache for tickers (key: exchange:symbol)
    """

    def __init__(
        self,
        ohlcv_ttl: int = _OHLCV_TTL_DEFAULT,
        order_book_ttl: float = _ORDER_BOOK_TTL,
        ticker_ttl: float = _TICKER_TTL,
        maxsize: int = _MAX_SIZE,
    ) -> None:
        self.ohlcv: TTLCache = TTLCache(maxsize=maxsize, ttl=ohlcv_ttl)
        self.order_book: TTLCache = TTLCache(maxsize=maxsize, ttl=order_book_ttl)
        self.ticker: TTLCache = TTLCache(maxsize=maxsize, ttl=ticker_ttl)
        self._lock = asyncio.Lock()

    async def get_ohlcv(self, key: str) -> Any | None:
        """Return cached OHLCV data or None if absent/expired."""
        return self.ohlcv.get(key)

    async def set_ohlcv(self, key: str, value: Any) -> None:
        """Store OHLCV data in the shared cache."""
        self.ohlcv[key] = value

    async def get_order_book(self, key: str) -> Any | None:
        return self.order_book.get(key)

    async def set_order_book(self, key: str, value: Any) -> None:
        self.order_book[key] = value

    async def get_ticker(self, key: str) -> Any | None:
        return self.ticker.get(key)

    async def set_ticker(self, key: str, value: Any) -> None:
        self.ticker[key] = value


# Process-level singleton — one instance per Python process.
_shared_cache: SharedMarketCache | None = None
_cache_lock = asyncio.Lock()


async def get_shared_cache() -> SharedMarketCache:
    """Return the process-level SharedMarketCache, creating it on first call."""
    global _shared_cache
    if _shared_cache is None:
        async with _cache_lock:
            if _shared_cache is None:
                _shared_cache = SharedMarketCache()
    return _shared_cache


def reset_shared_cache() -> None:
    """Reset the process-level cache. Intended for testing only."""
    global _shared_cache
    _shared_cache = None
