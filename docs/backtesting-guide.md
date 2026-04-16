# SonarFT Backtesting — Developer Guide

**Version:** 1.0.0  
**Last Updated:** July 2025  
**Repository:** `sonarft-monorepo/packages/bot/`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Data Model](#3-data-model)
4. [Implementation — Bot Package](#4-implementation--bot-package)
5. [Implementation — API Package](#5-implementation--api-package)
6. [Implementation — Web Package](#6-implementation--web-package)
7. [Historical Data Sources](#7-historical-data-sources)
8. [Running a Backtest](#8-running-a-backtest)
9. [Interpreting Results](#9-interpreting-results)
10. [Testing the Backtester](#10-testing-the-backtester)
11. [Limitations and Considerations](#11-limitations-and-considerations)

---

## 1. Overview

### What is backtesting?

Backtesting replays the SonarFT trading strategy against historical OHLCV
(Open, High, Low, Close, Volume) data to evaluate how it would have performed
in the past. It answers the question: *"If this strategy had been running on
this data, what would the P&L, win rate, and drawdown have been?"*

### What backtesting is NOT

- It is **not** a guarantee of future performance
- It is **not** a live simulation (no real order book, no slippage model)
- It is **not** a replacement for paper trading before going live

### How SonarFT backtesting works

The existing live trading pipeline is:

```
SonarftSearch → TradeProcessor → SonarftPrices (VWAP + indicators)
             → SonarftMath (profit calculation)
             → SonarftExecution (order placement)
```

Backtesting replaces the **live data sources** with **historical OHLCV data**
and replaces **SonarftExecution** with a **simulated fill engine** that records
trades without placing real orders. Everything else — price adjustment,
indicator calculation, profit math, fee calculation — runs unchanged.

```
BacktestRunner
    │
    ├── BacktestDataFeed      ← replaces SonarftApiManager (live exchange)
    │   └── loads OHLCV CSV / CCXT historical fetch
    │
    ├── SonarftIndicators     ← unchanged (reads from BacktestDataFeed)
    ├── SonarftPrices         ← unchanged
    ├── SonarftMath           ← unchanged
    │
    └── BacktestExecution     ← replaces SonarftExecution (no real orders)
        └── records fills, P&L, drawdown
```

---

## 2. Architecture

### New files to create

```
packages/bot/
├── sonarft_backtest.py          # BacktestRunner — main entry point
├── sonarft_backtest_data.py     # BacktestDataFeed — historical data provider
├── sonarft_backtest_execution.py # BacktestExecution — simulated fill engine
├── sonarft_backtest_report.py   # BacktestReport — results and metrics
└── tests/
    └── test_sonarft_backtest.py

packages/api/src/api/v1/endpoints/
└── backtest.py                  # REST endpoints for backtest management

packages/web/src/
├── components/Backtest/
│   ├── BacktestForm.tsx         # Configuration form
│   ├── BacktestResults.tsx      # Results display
│   └── BacktestChart.tsx        # P&L equity curve
└── pages/Backtest/
    └── Backtest.tsx             # Backtest page
```

### Component interaction

```
Web (BacktestForm)
    │  POST /api/v1/backtest
    ▼
API (backtest.py endpoint)
    │  calls BacktestRunner.run()
    ▼
Bot (sonarft_backtest.py)
    ├── BacktestDataFeed.load(exchange, symbol, timeframe, start, end)
    ├── For each candle window:
    │   ├── SonarftIndicators.get_rsi()  ← reads from feed, not live exchange
    │   ├── SonarftPrices.weighted_adjust_prices()
    │   ├── SonarftMath.calculate_trade()
    │   └── BacktestExecution.fill_trade()  ← records, no real order
    └── BacktestReport.generate()
    │
    ▼
API returns BacktestResult JSON
    │
    ▼
Web renders equity curve + metrics table
```

---

## 3. Data Model

### BacktestConfig — input

```python
@dataclass
class BacktestConfig:
    # Data range
    exchange: str           # e.g. "binance"
    base: str               # e.g. "BTC"
    quote: str              # e.g. "USDT"
    timeframe: str          # e.g. "1h", "15m", "1d"
    start_date: str         # ISO 8601, e.g. "2024-01-01"
    end_date: str           # ISO 8601, e.g. "2024-12-31"

    # Strategy parameters (mirrors sonarftdata/config_parameters.json)
    trade_amount: float             # e.g. 1.0
    profit_percentage_threshold: float  # e.g. 0.0001
    spread_increase_factor: float   # e.g. 1.00072
    spread_decrease_factor: float   # e.g. 0.99936

    # Fee model
    buy_fee_rate: float     # e.g. 0.001 (0.1%)
    sell_fee_rate: float    # e.g. 0.001

    # Indicator settings (mirrors config_indicators.json)
    rsi_period: int         # e.g. 14
    ma_period: int          # e.g. 14
    ma_type: str            # "sma" or "ema"

    # Optional: data source
    data_source: str        # "ccxt" (fetch live) or "csv" (local file)
    csv_path: str | None    # path to CSV if data_source == "csv"
```

### BacktestTrade — per-trade record

```python
@dataclass
class BacktestTrade:
    timestamp: str          # candle timestamp when trade was triggered
    position: str           # "LONG" or "SHORT"
    base: str
    quote: str
    buy_price: float
    sell_price: float
    trade_amount: float
    buy_value: float
    sell_value: float
    buy_fee: float
    sell_fee: float
    profit: float
    profit_percentage: float
    cumulative_profit: float    # running total
    market_direction: str       # "bull" / "bear" / "neutral"
    rsi: float
```

### BacktestResult — output

```python
@dataclass
class BacktestResult:
    config: BacktestConfig

    # Summary metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float             # winning_trades / total_trades
    total_profit: float
    total_profit_pct: float
    avg_profit_per_trade: float
    max_drawdown: float         # largest peak-to-trough decline
    max_drawdown_pct: float
    sharpe_ratio: float         # risk-adjusted return
    profit_factor: float        # gross_profit / gross_loss

    # Time series (for equity curve chart)
    equity_curve: list[dict]    # [{"timestamp": ..., "equity": ...}, ...]
    trades: list[BacktestTrade]

    # Metadata
    duration_seconds: float
    candles_processed: int
    start_date: str
    end_date: str
```

### TypeScript types (shared/types/api.ts additions)

```typescript
export interface BacktestConfig {
    exchange: string;
    base: string;
    quote: string;
    timeframe: string;
    start_date: string;
    end_date: string;
    trade_amount: number;
    profit_percentage_threshold: number;
    spread_increase_factor: number;
    spread_decrease_factor: number;
    buy_fee_rate: number;
    sell_fee_rate: number;
    rsi_period: number;
    ma_period: number;
    ma_type: "sma" | "ema";
    data_source: "ccxt" | "csv";
    csv_path?: string;
}

export interface BacktestTrade {
    timestamp: string;
    position: "LONG" | "SHORT";
    base: string;
    quote: string;
    buy_price: number;
    sell_price: number;
    trade_amount: number;
    profit: number;
    profit_percentage: number;
    cumulative_profit: number;
    market_direction: string;
    rsi: number;
}

export interface EquityPoint {
    timestamp: string;
    equity: number;
}

export interface BacktestResult {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: number;
    total_profit: number;
    total_profit_pct: number;
    avg_profit_per_trade: number;
    max_drawdown: number;
    max_drawdown_pct: number;
    sharpe_ratio: number;
    profit_factor: number;
    equity_curve: EquityPoint[];
    trades: BacktestTrade[];
    duration_seconds: number;
    candles_processed: number;
    start_date: string;
    end_date: string;
}
```

---

## 4. Implementation — Bot Package

### 4.1 BacktestDataFeed (`sonarft_backtest_data.py`)

This class replaces `SonarftApiManager` for the backtest. It provides the
same interface (`get_ohlcv_history`, `get_order_book`) but reads from a
pre-loaded OHLCV dataset instead of a live exchange.

Create `packages/bot/sonarft_backtest_data.py`:

```python
"""
SonarFT Backtest Data Feed
Provides historical OHLCV data to the indicator and price modules,
replacing the live SonarftApiManager during backtesting.
"""
from __future__ import annotations
import csv
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict

import ccxt.async_support as ccxt


class BacktestDataFeed:
    """
    Wraps a pre-loaded OHLCV dataset and exposes the same async interface
    as SonarftApiManager so that SonarftIndicators and SonarftPrices work
    without modification.

    OHLCV format: [timestamp_ms, open, high, low, close, volume]
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        # {(exchange, base, quote, timeframe): [candle, ...]}
        self._data: Dict[tuple, List] = {}
        # Pointer to the current candle index during replay
        self._cursor: int = 0
        self._fee_rates: Dict[str, float] = {}

    # ── Data loading ──────────────────────────────────────────────────────────

    async def load_from_ccxt(
        self,
        exchange_id: str,
        base: str,
        quote: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> int:
        """
        Fetch historical OHLCV from a CCXT exchange and cache it.
        Returns the number of candles loaded.
        """
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({"enableRateLimit": True})

        symbol = f"{base}/{quote}"
        since = int(datetime.fromisoformat(start_date)
                    .replace(tzinfo=timezone.utc).timestamp() * 1000)
        end_ms = int(datetime.fromisoformat(end_date)
                     .replace(tzinfo=timezone.utc).timestamp() * 1000)

        all_candles = []
        self.logger.info(
            f"Fetching {symbol} {timeframe} from {exchange_id} "
            f"({start_date} → {end_date})..."
        )

        try:
            while since < end_ms:
                candles = await exchange.fetch_ohlcv(
                    symbol, timeframe, since=since, limit=1000
                )
                if not candles:
                    break
                all_candles.extend(
                    c for c in candles if c[0] < end_ms
                )
                since = candles[-1][0] + 1
                await asyncio.sleep(exchange.rateLimit / 1000)
        finally:
            await exchange.close()

        key = (exchange_id, base, quote, timeframe)
        self._data[key] = all_candles
        self.logger.info(f"Loaded {len(all_candles)} candles for {symbol}")
        return len(all_candles)

    def load_from_csv(
        self,
        exchange_id: str,
        base: str,
        quote: str,
        timeframe: str,
        csv_path: str,
    ) -> int:
        """
        Load OHLCV data from a CSV file.
        Expected columns: timestamp,open,high,low,close,volume
        timestamp must be Unix milliseconds or ISO 8601.
        """
        candles = []
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row["timestamp"]
                # Accept both Unix ms and ISO 8601
                if ts.isdigit():
                    ts_ms = int(ts)
                else:
                    ts_ms = int(
                        datetime.fromisoformat(ts)
                        .replace(tzinfo=timezone.utc).timestamp() * 1000
                    )
                candles.append([
                    ts_ms,
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row["volume"]),
                ])

        key = (exchange_id, base, quote, timeframe)
        self._data[key] = sorted(candles, key=lambda c: c[0])
        self.logger.info(
            f"Loaded {len(candles)} candles from {csv_path}"
        )
        return len(candles)

    def set_fee_rate(self, exchange_id: str, fee_rate: float) -> None:
        self._fee_rates[exchange_id] = fee_rate

    def set_cursor(self, index: int) -> None:
        """Advance the replay cursor to a specific candle index."""
        self._cursor = index

    # ── SonarftApiManager-compatible interface ────────────────────────────────

    async def get_ohlcv_history(
        self,
        exchange_id: str,
        base: str,
        quote: str,
        timeframe: str,
        since=None,
        limit: int = 100,
    ) -> List:
        """
        Return the `limit` candles ending at the current cursor position.
        This simulates what a live exchange would return at this point in time.
        """
        key = (exchange_id, base, quote, timeframe)
        data = self._data.get(key, [])
        end = self._cursor + 1
        start = max(0, end - limit)
        return data[start:end]

    async def get_order_book(
        self, exchange_id: str, base: str, quote: str
    ) -> dict:
        """
        Synthesise a minimal order book from the current candle's OHLC.
        Uses the close price as mid, with a small synthetic spread.
        """
        key = (exchange_id, base, quote, "1h")
        # Fall back to any timeframe available for this exchange/symbol
        if key not in self._data:
            for k in self._data:
                if k[0] == exchange_id and k[1] == base and k[2] == quote:
                    key = k
                    break

        data = self._data.get(key, [])
        if not data or self._cursor >= len(data):
            return {"bids": [], "asks": []}

        candle = data[self._cursor]
        close = candle[4]
        spread = close * 0.0002  # 0.02% synthetic spread

        # Synthesise 10 levels of depth around the close price
        bids = [[close - spread * (i + 1), 1.0] for i in range(10)]
        asks = [[close + spread * (i + 1), 1.0] for i in range(10)]
        return {"bids": bids, "asks": asks}

    async def get_latest_prices(
        self, base: str, quote: str, weight: int
    ) -> List:
        """
        Return a price list in the format expected by SonarftPrices.
        For backtesting a single exchange, returns one entry.
        """
        # Find all exchanges that have data for this symbol
        results = []
        seen_exchanges = set()
        for (ex, b, q, tf), data in self._data.items():
            if b == base and q == quote and ex not in seen_exchanges:
                if self._cursor < len(data):
                    candle = data[self._cursor]
                    close = candle[4]
                    spread = close * 0.0002
                    # Format: [exchange, bid_vwap, ask_vwap, last_bid, last_ask]
                    results.append([
                        ex,
                        close - spread,
                        close + spread,
                        close - spread,
                        close + spread,
                    ])
                    seen_exchanges.add(ex)
        return results

    def get_buy_fee(self, exchange_id: str) -> float:
        return self._fee_rates.get(exchange_id, 0.001)

    def get_sell_fee(self, exchange_id: str) -> float:
        return self._fee_rates.get(exchange_id, 0.001)

    def get_symbol_precision(
        self, exchange_id: str, base: str, quote: str
    ) -> Optional[dict]:
        return None  # use EXCHANGE_RULES defaults in SonarftMath

    async def load_all_markets(self) -> None:
        pass  # no-op for backtesting

    def setAPIKeys(self, *args, **kwargs) -> None:
        pass  # no-op for backtesting
```

---

### 4.2 BacktestExecution (`sonarft_backtest_execution.py`)

Replaces `SonarftExecution`. Records fills without placing real orders.

Create `packages/bot/sonarft_backtest_execution.py`:

```python
"""
SonarFT Backtest Execution
Simulated fill engine — records trades without placing real orders.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BacktestFill:
    timestamp: str
    position: str
    base: str
    quote: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    trade_amount: float
    buy_value: float
    sell_value: float
    buy_fee: float
    sell_fee: float
    profit: float
    profit_percentage: float
    cumulative_profit: float = 0.0
    market_direction_buy: str = ""
    market_direction_sell: str = ""
    market_rsi_buy: float = 50.0
    market_rsi_sell: float = 50.0


class BacktestExecution:
    """
    Drop-in replacement for SonarftExecution during backtesting.
    Accepts the same execute_trade() call signature but records fills
    instead of placing real orders.
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.fills: List[BacktestFill] = []
        self._cumulative_profit: float = 0.0
        self._current_timestamp: str = ""

        # Compatibility attributes expected by SonarftSearch
        self.is_simulation_mode = True
        self.max_trade_amount = 0.0
        self.max_orders_per_minute = 0

    def set_timestamp(self, timestamp: str) -> None:
        """Called by BacktestRunner before each candle to stamp fills."""
        self._current_timestamp = timestamp

    async def execute_trade(self, botid, trade: dict) -> bool:
        """Record a simulated fill from the trade_data dict."""
        try:
            profit = trade.get("profit", 0.0)
            self._cumulative_profit += profit

            fill = BacktestFill(
                timestamp=self._current_timestamp,
                position=trade.get("position", "LONG"),
                base=trade["base"],
                quote=trade["quote"],
                buy_exchange=trade["buy_exchange"],
                sell_exchange=trade["sell_exchange"],
                buy_price=trade["buy_price"],
                sell_price=trade["sell_price"],
                trade_amount=trade["buy_trade_amount"],
                buy_value=trade["buy_value"],
                sell_value=trade["sell_value"],
                buy_fee=trade.get("buy_fee_quote", 0.0),
                sell_fee=trade.get("sell_fee_quote", 0.0),
                profit=profit,
                profit_percentage=trade.get("profit_percentage", 0.0),
                cumulative_profit=self._cumulative_profit,
                market_direction_buy=trade.get("market_direction_buy", ""),
                market_direction_sell=trade.get("market_direction_sell", ""),
                market_rsi_buy=trade.get("market_rsi_buy", 50.0),
                market_rsi_sell=trade.get("market_rsi_sell", 50.0),
            )
            self.fills.append(fill)
            self.logger.debug(
                f"Backtest fill: {fill.position} {fill.base}/{fill.quote} "
                f"profit={profit:.6f} cumulative={self._cumulative_profit:.6f}"
            )
            return True
        except Exception as e:
            self.logger.error(f"BacktestExecution.execute_trade error: {e}")
            return False

    def reset(self) -> None:
        self.fills.clear()
        self._cumulative_profit = 0.0
        self._current_timestamp = ""
```

---

### 4.3 BacktestReport (`sonarft_backtest_report.py`)

Computes summary metrics from the list of fills.

Create `packages/bot/sonarft_backtest_report.py`:

```python
"""
SonarFT Backtest Report
Computes summary metrics and equity curve from backtest fills.
"""
from __future__ import annotations
import math
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any

from sonarft_backtest_execution import BacktestFill


@dataclass
class BacktestReport:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_profit: float = 0.0
    total_profit_pct: float = 0.0
    avg_profit_per_trade: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    equity_curve: List[Dict] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)
    duration_seconds: float = 0.0
    candles_processed: int = 0
    start_date: str = ""
    end_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def generate_report(
    fills: List[BacktestFill],
    candles_processed: int,
    start_date: str,
    end_date: str,
    duration_seconds: float,
    logger=None,
) -> BacktestReport:
    """Compute all metrics from a list of BacktestFill records."""
    log = logger or logging.getLogger(__name__)
    report = BacktestReport(
        candles_processed=candles_processed,
        start_date=start_date,
        end_date=end_date,
        duration_seconds=duration_seconds,
    )

    if not fills:
        log.warning("No fills to report — strategy produced zero trades.")
        return report

    report.total_trades = len(fills)
    profits = [f.profit for f in fills]
    report.winning_trades = sum(1 for p in profits if p > 0)
    report.losing_trades = sum(1 for p in profits if p <= 0)
    report.win_rate = report.winning_trades / report.total_trades
    report.total_profit = sum(profits)
    report.avg_profit_per_trade = report.total_profit / report.total_trades

    # Profit factor: gross profit / gross loss
    gross_profit = sum(p for p in profits if p > 0)
    gross_loss = abs(sum(p for p in profits if p < 0))
    report.profit_factor = (
        gross_profit / gross_loss if gross_loss > 0 else float("inf")
    )

    # Equity curve and max drawdown
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    curve = []
    for fill in fills:
        equity += fill.profit
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_dd:
            max_dd = drawdown
        curve.append({"timestamp": fill.timestamp, "equity": round(equity, 8)})

    report.equity_curve = curve
    report.max_drawdown = max_dd
    report.max_drawdown_pct = (max_dd / peak * 100) if peak > 0 else 0.0

    # Total profit as percentage of initial trade value
    if fills:
        initial_value = fills[0].buy_value
        report.total_profit_pct = (
            report.total_profit / initial_value * 100
            if initial_value > 0 else 0.0
        )

    # Sharpe ratio (annualised, assuming daily returns from equity curve)
    if len(profits) > 1:
        mean_r = sum(profits) / len(profits)
        variance = sum((p - mean_r) ** 2 for p in profits) / (len(profits) - 1)
        std_r = math.sqrt(variance) if variance > 0 else 0.0
        report.sharpe_ratio = (
            (mean_r / std_r) * math.sqrt(252) if std_r > 0 else 0.0
        )

    # Serialise fills
    report.trades = [
        {
            "timestamp": f.timestamp,
            "position": f.position,
            "base": f.base,
            "quote": f.quote,
            "buy_exchange": f.buy_exchange,
            "sell_exchange": f.sell_exchange,
            "buy_price": f.buy_price,
            "sell_price": f.sell_price,
            "trade_amount": f.trade_amount,
            "profit": round(f.profit, 8),
            "profit_percentage": round(f.profit_percentage, 8),
            "cumulative_profit": round(f.cumulative_profit, 8),
            "market_direction_buy": f.market_direction_buy,
            "market_rsi_buy": round(f.market_rsi_buy, 2),
        }
        for f in fills
    ]

    log.info(
        f"Backtest complete: {report.total_trades} trades, "
        f"win_rate={report.win_rate:.1%}, "
        f"total_profit={report.total_profit:.6f}, "
        f"max_drawdown={report.max_drawdown:.6f}, "
        f"sharpe={report.sharpe_ratio:.2f}"
    )
    return report
```

---

### 4.4 BacktestRunner (`sonarft_backtest.py`)

The main orchestrator. Wires the data feed, indicators, prices, math, and
execution together and replays candles.

Create `packages/bot/sonarft_backtest.py`:

```python
"""
SonarFT Backtest Runner
Replays historical OHLCV data through the SonarFT strategy pipeline.
"""
from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sonarft_backtest_data import BacktestDataFeed
from sonarft_backtest_execution import BacktestExecution
from sonarft_backtest_report import BacktestReport, generate_report
from sonarft_indicators import SonarftIndicators
from sonarft_math import SonarftMath
from sonarft_prices import SonarftPrices


@dataclass
class BacktestConfig:
    exchange: str
    base: str
    quote: str
    timeframe: str
    start_date: str
    end_date: str
    trade_amount: float = 1.0
    profit_percentage_threshold: float = 0.0001
    spread_increase_factor: float = 1.00072
    spread_decrease_factor: float = 0.99936
    buy_fee_rate: float = 0.001
    sell_fee_rate: float = 0.001
    rsi_period: int = 14
    ma_period: int = 14
    ma_type: str = "sma"
    data_source: str = "ccxt"   # "ccxt" or "csv"
    csv_path: Optional[str] = None


class BacktestRunner:
    """
    Replays historical OHLCV data through the SonarFT strategy.

    Usage:
        runner = BacktestRunner()
        config = BacktestConfig(
            exchange="binance", base="BTC", quote="USDT",
            timeframe="1h", start_date="2024-01-01", end_date="2024-06-30",
        )
        report = await runner.run(config)
        print(report.total_profit, report.win_rate)
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    async def run(self, config: BacktestConfig) -> BacktestReport:
        """Run a full backtest and return the report."""
        t_start = time.monotonic()
        self.logger.info(
            f"Starting backtest: {config.exchange} {config.base}/{config.quote} "
            f"{config.timeframe} {config.start_date} → {config.end_date}"
        )

        # 1. Load historical data
        feed = BacktestDataFeed(self.logger)
        feed.set_fee_rate(config.exchange, config.buy_fee_rate)

        if config.data_source == "csv" and config.csv_path:
            n_candles = feed.load_from_csv(
                config.exchange, config.base, config.quote,
                config.timeframe, config.csv_path,
            )
        else:
            n_candles = await feed.load_from_ccxt(
                config.exchange, config.base, config.quote,
                config.timeframe, config.start_date, config.end_date,
            )

        if n_candles == 0:
            self.logger.error("No candles loaded — aborting backtest.")
            return BacktestReport(start_date=config.start_date, end_date=config.end_date)

        # 2. Wire up modules (same as SonarftBot.InitializeModules, but with feed)
        indicators = SonarftIndicators(feed, self.logger)
        math_module = SonarftMath(feed, self.logger)
        prices = SonarftPrices(feed, indicators, self.logger)
        prices.spread_increase_factor = config.spread_increase_factor
        prices.spread_decrease_factor = config.spread_decrease_factor
        prices.active_indicators = ["rsi", "stoch rsi", "macd"]

        execution = BacktestExecution(self.logger)

        # 3. Determine the minimum warmup period needed for indicators
        # RSI(14) + StochRSI(14,14) needs at least 28 candles of history
        warmup = max(config.rsi_period * 2 + 10, 50)

        # 4. Replay candles
        data_key = (config.exchange, config.base, config.quote, config.timeframe)
        all_candles = feed._data.get(data_key, [])

        self.logger.info(
            f"Replaying {n_candles} candles "
            f"(warmup: first {warmup} skipped)..."
        )

        for i in range(warmup, n_candles):
            feed.set_cursor(i)
            candle = all_candles[i]
            ts_ms = candle[0]
            ts_str = datetime.fromtimestamp(
                ts_ms / 1000, tz=timezone.utc
            ).isoformat()
            execution.set_timestamp(ts_str)

            await self._process_candle(
                config, feed, prices, math_module, execution,
                ts_str, i,
            )

        # 5. Generate report
        duration = time.monotonic() - t_start
        report = generate_report(
            fills=execution.fills,
            candles_processed=n_candles - warmup,
            start_date=config.start_date,
            end_date=config.end_date,
            duration_seconds=round(duration, 2),
            logger=self.logger,
        )
        return report

    async def _process_candle(
        self,
        config: BacktestConfig,
        feed: BacktestDataFeed,
        prices: SonarftPrices,
        math_module: SonarftMath,
        execution: BacktestExecution,
        timestamp: str,
        cursor: int,
    ) -> None:
        """Evaluate the strategy for a single candle."""
        try:
            # Get price lists (same call as TradeProcessor.process_symbol)
            buy_prices_list, sell_prices_list = \
                await prices.get_the_latest_prices(
                    config.base, config.quote, config.trade_amount, weight=12
                )

            if not buy_prices_list or not sell_prices_list:
                return

            for buy_price_list in buy_prices_list:
                for sell_price_list in sell_prices_list:
                    # Skip same-exchange combinations
                    if buy_price_list[0] == sell_price_list[0]:
                        continue

                    buy_exchange = buy_price_list[0]
                    sell_exchange = sell_price_list[0]
                    buy_price = buy_price_list[1]
                    sell_price = sell_price_list[2]

                    # Adjust prices using indicators (same as live)
                    adj_buy, adj_sell, indicators = \
                        await prices.weighted_adjust_prices(
                            "backtest",
                            buy_exchange, sell_exchange,
                            config.base, config.quote,
                            buy_price, sell_price,
                            buy_price, sell_price,
                        )

                    if adj_buy == 0 or adj_sell == 0:
                        continue

                    # Build price list tuples for SonarftMath
                    buy_pl = (buy_exchange, adj_buy, buy_price, buy_price, None)
                    sell_pl = (sell_exchange, sell_price, adj_sell, sell_price, None)

                    # Calculate profit (same as live)
                    profit, profit_pct, trade_data = math_module.calculate_trade(
                        adj_buy, adj_sell,
                        buy_pl, sell_pl,
                        config.trade_amount,
                        config.base, config.quote,
                    )

                    if trade_data is None:
                        continue

                    trade_data.update(indicators)

                    # Apply profit threshold (same as live)
                    if profit_pct >= config.profit_percentage_threshold:
                        await execution.execute_trade("backtest", trade_data)

        except asyncio.TimeoutError:
            self.logger.debug(f"Candle {cursor} timed out — skipping")
        except Exception as e:
            self.logger.debug(f"Candle {cursor} error: {e}")
```

---

## 5. Implementation — API Package

### 5.1 Pydantic schemas

Add to `packages/api/src/models/schemas.py`:

```python
# ### Backtest models ###

from typing import Optional, List
from pydantic import BaseModel, Field

class BacktestConfigRequest(BaseModel):
    exchange: str = Field(..., example="binance")
    base: str = Field(..., example="BTC")
    quote: str = Field(..., example="USDT")
    timeframe: str = Field("1h", example="1h")
    start_date: str = Field(..., example="2024-01-01")
    end_date: str = Field(..., example="2024-06-30")
    trade_amount: float = Field(1.0, gt=0)
    profit_percentage_threshold: float = Field(0.0001, gt=0, lt=1)
    spread_increase_factor: float = Field(1.00072)
    spread_decrease_factor: float = Field(0.99936)
    buy_fee_rate: float = Field(0.001, ge=0)
    sell_fee_rate: float = Field(0.001, ge=0)
    rsi_period: int = Field(14, ge=2, le=100)
    ma_period: int = Field(14, ge=2, le=100)
    ma_type: str = Field("sma", pattern="^(sma|ema)$")
    data_source: str = Field("ccxt", pattern="^(ccxt|csv)$")
    csv_path: Optional[str] = None


class EquityPoint(BaseModel):
    timestamp: str
    equity: float


class BacktestTradeRecord(BaseModel):
    timestamp: str
    position: str
    base: str
    quote: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    trade_amount: float
    profit: float
    profit_percentage: float
    cumulative_profit: float
    market_direction_buy: str
    market_rsi_buy: float


class BacktestResultResponse(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    total_profit_pct: float
    avg_profit_per_trade: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    equity_curve: List[EquityPoint]
    trades: List[BacktestTradeRecord]
    duration_seconds: float
    candles_processed: int
    start_date: str
    end_date: str
```

### 5.2 Backtest endpoint

Create `packages/api/src/api/v1/endpoints/backtest.py`:

```python
"""
Backtest endpoints.
POST /api/v1/backtest        — run a backtest synchronously
POST /api/v1/backtest/async  — submit a backtest job (returns job_id)
GET  /api/v1/backtest/{job_id} — poll job status and retrieve result
"""
from __future__ import annotations
import asyncio
import uuid
import logging
from typing import Annotated, Dict

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from ....core.security import require_auth
from ....models.schemas import (
    BacktestConfigRequest,
    BacktestResultResponse,
    MessageResponse,
)

router = APIRouter(prefix="/backtest", tags=["Backtest"])
Auth = Annotated[None, Depends(require_auth)]
_logger = logging.getLogger(__name__)

# In-memory job store — replace with Redis or a DB for production
_jobs: Dict[str, dict] = {}


def _run_backtest(config_req: BacktestConfigRequest) -> dict:
    """Import and run the backtest synchronously (called in a thread)."""
    from sonarft_backtest import BacktestRunner, BacktestConfig  # type: ignore

    cfg = BacktestConfig(
        exchange=config_req.exchange,
        base=config_req.base,
        quote=config_req.quote,
        timeframe=config_req.timeframe,
        start_date=config_req.start_date,
        end_date=config_req.end_date,
        trade_amount=config_req.trade_amount,
        profit_percentage_threshold=config_req.profit_percentage_threshold,
        spread_increase_factor=config_req.spread_increase_factor,
        spread_decrease_factor=config_req.spread_decrease_factor,
        buy_fee_rate=config_req.buy_fee_rate,
        sell_fee_rate=config_req.sell_fee_rate,
        rsi_period=config_req.rsi_period,
        ma_period=config_req.ma_period,
        ma_type=config_req.ma_type,
        data_source=config_req.data_source,
        csv_path=config_req.csv_path,
    )
    runner = BacktestRunner()
    # Run the async backtest in a new event loop inside the thread
    loop = asyncio.new_event_loop()
    try:
        report = loop.run_until_complete(runner.run(cfg))
    finally:
        loop.close()
    return report.to_dict()


@router.post("", response_model=BacktestResultResponse, status_code=200)
async def run_backtest_sync(
    body: BacktestConfigRequest,
    _: Auth,
) -> BacktestResultResponse:
    """
    Run a backtest synchronously and return the full result.
    Suitable for short date ranges (< 3 months of hourly data).
    For longer ranges use POST /backtest/async.
    """
    try:
        result = await asyncio.to_thread(_run_backtest, body)
        return BacktestResultResponse(**result)
    except Exception as exc:
        _logger.error("Backtest error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/async", response_model=MessageResponse, status_code=202)
async def run_backtest_async(
    body: BacktestConfigRequest,
    background_tasks: BackgroundTasks,
    _: Auth,
) -> MessageResponse:
    """
    Submit a backtest job. Returns a job_id immediately.
    Poll GET /backtest/{job_id} for status and result.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "result": None, "error": None}

    def _background_job():
        try:
            result = _run_backtest(body)
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = result
        except Exception as exc:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)

    background_tasks.add_task(_background_job)
    return MessageResponse(message=job_id)


@router.get("/{job_id}")
async def get_backtest_result(
    job_id: str,
    _: Auth,
) -> dict:
    """
    Poll a backtest job.
    Returns {"status": "running"} while in progress,
    {"status": "done", "result": {...}} when complete,
    {"status": "error", "error": "..."} on failure.
    """
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job
```

### 5.3 Register the router

In `packages/api/src/main.py`, add alongside the existing routers:

```python
from .api.v1.endpoints.backtest import router as backtest_router

# Inside create_app(), after the existing include_router calls:
app.include_router(backtest_router, prefix=prefix)
```

### 5.4 New API endpoints summary

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/backtest` | Run backtest synchronously, return full result |
| `POST` | `/api/v1/backtest/async` | Submit backtest job, return `job_id` |
| `GET` | `/api/v1/backtest/{job_id}` | Poll job status and retrieve result |

**Example — synchronous backtest:**

```bash
curl -X POST http://localhost:8000/api/v1/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "exchange": "binance",
    "base": "BTC",
    "quote": "USDT",
    "timeframe": "1h",
    "start_date": "2024-01-01",
    "end_date": "2024-03-31",
    "trade_amount": 1.0,
    "profit_percentage_threshold": 0.0001,
    "buy_fee_rate": 0.001,
    "sell_fee_rate": 0.001
  }'
```

**Example — async backtest (long date range):**

```bash
# Submit
curl -X POST http://localhost:8000/api/v1/backtest/async \
  -H "Content-Type: application/json" \
  -d '{"exchange":"binance","base":"BTC","quote":"USDT","timeframe":"1h","start_date":"2023-01-01","end_date":"2024-01-01",...}'
# → {"message": "a1b2c3d4-..."}

# Poll
curl http://localhost:8000/api/v1/backtest/a1b2c3d4-...
# → {"status": "running"}   (while in progress)
# → {"status": "done", "result": {...}}  (when complete)
```

---

## 6. Implementation — Web Package

### 6.1 API client functions

Add to `packages/web/src/utils/api.ts`:

```typescript
import type { BacktestConfig, BacktestResult } from "../../shared/types/api";

// Run a backtest synchronously (suitable for short date ranges)
export const runBacktest = async (
    config: BacktestConfig
): Promise<BacktestResult> => {
    const response = await fetch(HTTP + "/backtest", {
        method: "POST",
        headers: { ...baseHeaders, ...getAuthHeaders() },
        body: JSON.stringify(config),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json() as BacktestResult;
};

// Submit an async backtest job — returns job_id
export const submitBacktest = async (
    config: BacktestConfig
): Promise<string> => {
    const response = await fetch(HTTP + "/backtest/async", {
        method: "POST",
        headers: { ...baseHeaders, ...getAuthHeaders() },
        body: JSON.stringify(config),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json() as { message: string };
    return data.message; // job_id
};

// Poll a backtest job
export const getBacktestResult = async (
    jobId: string
): Promise<{ status: string; result?: BacktestResult; error?: string }> => {
    const response = await fetch(HTTP + `/backtest/${jobId}`, {
        method: "GET",
        headers: { ...baseHeaders, ...getAuthHeaders() },
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
};
```

### 6.2 useBacktest hook

Create `packages/web/src/hooks/useBacktest.ts`:

```typescript
import { useState, useCallback, useRef } from "react";
import { runBacktest, submitBacktest, getBacktestResult } from "../utils/api";
import type { BacktestConfig, BacktestResult } from "../../shared/types/api";

type BacktestStatus = "idle" | "running" | "done" | "error";

interface UseBacktestReturn {
    status: BacktestStatus;
    result: BacktestResult | null;
    error: string | null;
    run: (config: BacktestConfig, async?: boolean) => Promise<void>;
    reset: () => void;
}

const POLL_INTERVAL_MS = 2000;

const useBacktest = (): UseBacktestReturn => {
    const [status, setStatus] = useState<BacktestStatus>("idle");
    const [result, setResult] = useState<BacktestResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const reset = useCallback(() => {
        if (pollRef.current) clearInterval(pollRef.current);
        setStatus("idle");
        setResult(null);
        setError(null);
    }, []);

    const run = useCallback(async (
        config: BacktestConfig,
        useAsync = false
    ) => {
        reset();
        setStatus("running");

        try {
            if (!useAsync) {
                // Synchronous — wait for full result
                const res = await runBacktest(config);
                setResult(res);
                setStatus("done");
            } else {
                // Async — submit job then poll
                const jobId = await submitBacktest(config);
                pollRef.current = setInterval(async () => {
                    try {
                        const job = await getBacktestResult(jobId);
                        if (job.status === "done" && job.result) {
                            clearInterval(pollRef.current!);
                            setResult(job.result);
                            setStatus("done");
                        } else if (job.status === "error") {
                            clearInterval(pollRef.current!);
                            setError(job.error ?? "Backtest failed");
                            setStatus("error");
                        }
                        // status === "running" → keep polling
                    } catch (e) {
                        clearInterval(pollRef.current!);
                        setError(String(e));
                        setStatus("error");
                    }
                }, POLL_INTERVAL_MS);
            }
        } catch (e) {
            setError(String(e));
            setStatus("error");
        }
    }, [reset]);

    return { status, result, error, run, reset };
};

export default useBacktest;
```

### 6.3 BacktestForm component

Create `packages/web/src/components/Backtest/BacktestForm.tsx`:

```tsx
import React, { useState } from "react";
import type { BacktestConfig } from "../../../shared/types/api";
import "./backtest.css";

interface BacktestFormProps {
    onSubmit: (config: BacktestConfig, useAsync: boolean) => void;
    isRunning: boolean;
}

const DEFAULTS: BacktestConfig = {
    exchange: "binance",
    base: "BTC",
    quote: "USDT",
    timeframe: "1h",
    start_date: "2024-01-01",
    end_date: "2024-06-30",
    trade_amount: 1.0,
    profit_percentage_threshold: 0.0001,
    spread_increase_factor: 1.00072,
    spread_decrease_factor: 0.99936,
    buy_fee_rate: 0.001,
    sell_fee_rate: 0.001,
    rsi_period: 14,
    ma_period: 14,
    ma_type: "sma",
    data_source: "ccxt",
};

const BacktestForm: React.FC<BacktestFormProps> = ({ onSubmit, isRunning }) => {
    const [config, setConfig] = useState<BacktestConfig>(DEFAULTS);

    const set = (key: keyof BacktestConfig, value: unknown) =>
        setConfig((prev) => ({ ...prev, [key]: value }));

    const handleSubmit = (e: React.FormEvent, useAsync: boolean) => {
        e.preventDefault();
        onSubmit(config, useAsync);
    };

    return (
        <form className="backtest-form">
            <h3>Data Range</h3>
            <div className="backtest-form__row">
                <label>Exchange
                    <input value={config.exchange}
                        onChange={(e) => set("exchange", e.target.value)} />
                </label>
                <label>Base
                    <input value={config.base}
                        onChange={(e) => set("base", e.target.value.toUpperCase())} />
                </label>
                <label>Quote
                    <input value={config.quote}
                        onChange={(e) => set("quote", e.target.value.toUpperCase())} />
                </label>
                <label>Timeframe
                    <select value={config.timeframe}
                        onChange={(e) => set("timeframe", e.target.value)}>
                        {["1m","5m","15m","30m","1h","4h","1d"].map((tf) => (
                            <option key={tf} value={tf}>{tf}</option>
                        ))}
                    </select>
                </label>
            </div>
            <div className="backtest-form__row">
                <label>Start Date
                    <input type="date" value={config.start_date}
                        onChange={(e) => set("start_date", e.target.value)} />
                </label>
                <label>End Date
                    <input type="date" value={config.end_date}
                        onChange={(e) => set("end_date", e.target.value)} />
                </label>
            </div>

            <h3>Strategy Parameters</h3>
            <div className="backtest-form__row">
                <label title="Trade size in base currency units">Trade Amount
                    <input type="number" step="0.01" value={config.trade_amount}
                        onChange={(e) => set("trade_amount", parseFloat(e.target.value))} />
                </label>
                <label title="Minimum profit % required to execute (e.g. 0.0001 = 0.01%)">
                    Profit Threshold
                    <input type="number" step="0.00001" value={config.profit_percentage_threshold}
                        onChange={(e) => set("profit_percentage_threshold", parseFloat(e.target.value))} />
                </label>
                <label title="Taker fee rate (e.g. 0.001 = 0.1%)">Buy Fee Rate
                    <input type="number" step="0.0001" value={config.buy_fee_rate}
                        onChange={(e) => set("buy_fee_rate", parseFloat(e.target.value))} />
                </label>
                <label title="Taker fee rate (e.g. 0.001 = 0.1%)">Sell Fee Rate
                    <input type="number" step="0.0001" value={config.sell_fee_rate}
                        onChange={(e) => set("sell_fee_rate", parseFloat(e.target.value))} />
                </label>
            </div>

            <h3>Indicator Settings</h3>
            <div className="backtest-form__row">
                <label title="RSI lookback period">RSI Period
                    <input type="number" min="2" max="100" value={config.rsi_period}
                        onChange={(e) => set("rsi_period", parseInt(e.target.value))} />
                </label>
                <label title="Moving average period for market direction">MA Period
                    <input type="number" min="2" max="100" value={config.ma_period}
                        onChange={(e) => set("ma_period", parseInt(e.target.value))} />
                </label>
                <label>MA Type
                    <select value={config.ma_type}
                        onChange={(e) => set("ma_type", e.target.value as "sma" | "ema")}>
                        <option value="sma">SMA</option>
                        <option value="ema">EMA</option>
                    </select>
                </label>
            </div>

            <div className="backtest-form__actions">
                <button type="button"
                    onClick={(e) => handleSubmit(e, false)}
                    disabled={isRunning}>
                    {isRunning ? "Running..." : "Run Backtest"}
                </button>
                <button type="button"
                    onClick={(e) => handleSubmit(e, true)}
                    disabled={isRunning}
                    title="Submit as background job — use for date ranges > 3 months">
                    Run Async
                </button>
            </div>
        </form>
    );
};

export default BacktestForm;
```

### 6.4 BacktestResults component

Create `packages/web/src/components/Backtest/BacktestResults.tsx`:

```tsx
import React from "react";
import type { BacktestResult } from "../../../shared/types/api";
import BacktestChart from "./BacktestChart";
import "./backtest.css";

interface BacktestResultsProps {
    result: BacktestResult;
}

const fmt = (n: number, decimals = 6) => n.toFixed(decimals);
const pct = (n: number) => (n * 100).toFixed(2) + "%";

const BacktestResults: React.FC<BacktestResultsProps> = ({ result }) => (
    <div className="backtest-results">
        <h3>Summary</h3>
        <div className="backtest-results__metrics">
            <div className="metric">
                <span className="metric__label">Total Trades</span>
                <span className="metric__value">{result.total_trades}</span>
            </div>
            <div className="metric">
                <span className="metric__label">Win Rate</span>
                <span className={`metric__value ${result.win_rate >= 0.5 ? "pos" : "neg"}`}>
                    {pct(result.win_rate)}
                </span>
            </div>
            <div className="metric">
                <span className="metric__label">Total Profit</span>
                <span className={`metric__value ${result.total_profit >= 0 ? "pos" : "neg"}`}>
                    {fmt(result.total_profit)} ({result.total_profit_pct.toFixed(2)}%)
                </span>
            </div>
            <div className="metric">
                <span className="metric__label">Avg Profit / Trade</span>
                <span className={`metric__value ${result.avg_profit_per_trade >= 0 ? "pos" : "neg"}`}>
                    {fmt(result.avg_profit_per_trade)}
                </span>
            </div>
            <div className="metric">
                <span className="metric__label">Max Drawdown</span>
                <span className="metric__value neg">
                    {fmt(result.max_drawdown)} ({result.max_drawdown_pct.toFixed(2)}%)
                </span>
            </div>
            <div className="metric">
                <span className="metric__label">Sharpe Ratio</span>
                <span className={`metric__value ${result.sharpe_ratio >= 1 ? "pos" : "neg"}`}>
                    {result.sharpe_ratio.toFixed(2)}
                </span>
            </div>
            <div className="metric">
                <span className="metric__label">Profit Factor</span>
                <span className={`metric__value ${result.profit_factor >= 1 ? "pos" : "neg"}`}>
                    {result.profit_factor === Infinity
                        ? "∞" : result.profit_factor.toFixed(2)}
                </span>
            </div>
            <div className="metric">
                <span className="metric__label">Candles Processed</span>
                <span className="metric__value">{result.candles_processed}</span>
            </div>
            <div className="metric">
                <span className="metric__label">Duration</span>
                <span className="metric__value">{result.duration_seconds.toFixed(1)}s</span>
            </div>
        </div>

        <h3>Equity Curve</h3>
        <BacktestChart equityCurve={result.equity_curve} />

        <h3>Trade Log</h3>
        <div className="backtest-results__table-wrap">
            <table className="backtest-table">
                <thead>
                    <tr>
                        <th>Time</th><th>Pos</th><th>Symbol</th>
                        <th>Buy Price</th><th>Sell Price</th>
                        <th>Profit</th><th>Profit %</th>
                        <th>Cumulative</th><th>Direction</th><th>RSI</th>
                    </tr>
                </thead>
                <tbody>
                    {result.trades.map((t, i) => (
                        <tr key={i} className={t.profit >= 0 ? "row-win" : "row-loss"}>
                            <td>{t.timestamp.slice(0, 16)}</td>
                            <td>{t.position}</td>
                            <td>{t.base}/{t.quote}</td>
                            <td>{t.buy_price.toFixed(2)}</td>
                            <td>{t.sell_price.toFixed(2)}</td>
                            <td className={t.profit >= 0 ? "pos" : "neg"}>
                                {fmt(t.profit)}
                            </td>
                            <td className={t.profit_percentage >= 0 ? "pos" : "neg"}>
                                {(t.profit_percentage * 100).toFixed(4)}%
                            </td>
                            <td>{fmt(t.cumulative_profit)}</td>
                            <td>{t.market_direction_buy}</td>
                            <td>{t.market_rsi_buy.toFixed(1)}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    </div>
);

export default BacktestResults;
```

### 6.5 BacktestChart component

Create `packages/web/src/components/Backtest/BacktestChart.tsx`:

```tsx
import React from "react";
import {
    ResponsiveContainer, AreaChart, Area,
    XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";
import type { EquityPoint } from "../../../shared/types/api";

interface BacktestChartProps {
    equityCurve: EquityPoint[];
}

const BacktestChart: React.FC<BacktestChartProps> = ({ equityCurve }) => {
    if (!equityCurve.length) return null;

    const finalEquity = equityCurve[equityCurve.length - 1].equity;
    const isPositive = finalEquity >= 0;
    const color = isPositive ? "#88dd88" : "#ff8888";
    const gradientColor = isPositive ? "#4a8a4a" : "#a33";

    const data = equityCurve.map((p) => ({
        label: p.timestamp.slice(0, 10),
        equity: p.equity,
    }));

    return (
        <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
                <defs>
                    <linearGradient id="btGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={gradientColor} stopOpacity={0.4} />
                        <stop offset="95%" stopColor={gradientColor} stopOpacity={0} />
                    </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3a4a" />
                <XAxis dataKey="label" tick={{ fill: "#9AA5B1", fontSize: 10 }}
                    interval="preserveStartEnd" />
                <YAxis tick={{ fill: "#9AA5B1", fontSize: 10 }}
                    tickFormatter={(v: number) => v.toFixed(4)} />
                <Tooltip
                    contentStyle={{ background: "#0c2a4e", border: "1px solid #528afc" }}
                    labelStyle={{ color: "#9AA5B1" }}
                    formatter={(v: number) => [v.toFixed(6), "Equity"]}
                />
                <ReferenceLine y={0} stroke="#528afc" strokeDasharray="4 2" />
                <Area type="monotone" dataKey="equity"
                    stroke={color} strokeWidth={2}
                    fill="url(#btGradient)" dot={false} activeDot={{ r: 3 }} />
            </AreaChart>
        </ResponsiveContainer>
    );
};

export default BacktestChart;
```

### 6.6 Backtest page

Create `packages/web/src/pages/Backtest/Backtest.tsx`:

```tsx
import React, { useContext } from "react";
import { AuthContext } from "../../hooks/AuthProvider";
import PrivateRoute from "../../components/PrivateRoute/PrivateRoute";
import ErrorBoundary from "../../components/ErrorBoundary/ErrorBoundary";
import BacktestForm from "../../components/Backtest/BacktestForm";
import BacktestResults from "../../components/Backtest/BacktestResults";
import useBacktest from "../../hooks/useBacktest";
import type { BacktestConfig } from "../../../shared/types/api";
import "./backtest.css";

const Backtest: React.FC = () => {
    const { user } = useContext(AuthContext);
    const { status, result, error, run, reset } = useBacktest();

    const handleSubmit = (config: BacktestConfig, useAsync: boolean) => {
        run(config, useAsync);
    };

    return (
        <section>
            <main className="backtest-page">
                <PrivateRoute value={user}>
                    <ErrorBoundary>
                        <h2>Backtesting</h2>
                        <p className="backtest-page__desc">
                            Replay the SonarFT strategy against historical OHLCV data
                            to evaluate performance before going live.
                        </p>

                        <BacktestForm
                            onSubmit={handleSubmit}
                            isRunning={status === "running"}
                        />

                        {status === "running" && (
                            <div className="backtest-status">
                                ⏳ Running backtest — fetching data and replaying candles...
                            </div>
                        )}

                        {status === "error" && (
                            <div className="backtest-error">
                                ✗ {error}
                                <button onClick={reset}>Dismiss</button>
                            </div>
                        )}

                        {status === "done" && result && (
                            <BacktestResults result={result} />
                        )}
                    </ErrorBoundary>
                </PrivateRoute>
            </main>
        </section>
    );
};

export default Backtest;
```

### 6.7 CSS

Create `packages/web/src/components/Backtest/backtest.css`:

```css
.backtest-form { display: flex; flex-direction: column; gap: 12px; }
.backtest-form h3 { color: var(--textPrimary); margin: 8px 0 4px; }
.backtest-form__row { display: flex; flex-wrap: wrap; gap: 10px; }
.backtest-form__row label {
    display: flex; flex-direction: column; gap: 4px;
    font-size: 0.8rem; color: var(--textTertiary);
}
.backtest-form__row input,
.backtest-form__row select {
    background: var(--backgroundTertiary); color: var(--textSecondary);
    border: 1px solid var(--borderPrimary); border-radius: 4px;
    padding: 4px 8px; font-size: 0.85rem; min-width: 120px;
}
.backtest-form__actions { display: flex; gap: 10px; margin-top: 8px; }
.backtest-form__actions button {
    background: var(--buttonBackground); color: var(--buttonText);
    border: 1px solid var(--borderPrimary); border-radius: 5px;
    padding: 8px 20px; cursor: pointer; transition: all 0.3s ease;
}
.backtest-form__actions button:hover { background: var(--buttonHoverBackground); }
.backtest-form__actions button:disabled { opacity: 0.5; cursor: not-allowed; }

.backtest-results__metrics {
    display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px;
}
.metric {
    background: var(--backgroundSecondary); border: 1px solid var(--borderPrimary);
    border-radius: 6px; padding: 10px 16px; min-width: 140px;
}
.metric__label { display: block; font-size: 0.75rem; color: var(--textTertiary); }
.metric__value { display: block; font-size: 1.1rem; font-weight: bold; margin-top: 4px; }
.pos { color: #88dd88; }
.neg { color: #ff8888; }

.backtest-results__table-wrap { overflow-x: auto; max-height: 300px; overflow-y: auto; }
.backtest-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.backtest-table th, .backtest-table td {
    border: 1px solid var(--borderPrimary); padding: 4px 8px; text-align: center;
}
.row-win { background: rgba(74, 138, 74, 0.08); }
.row-loss { background: rgba(163, 51, 51, 0.08); }

.backtest-status {
    padding: 12px; margin: 12px 0; background: var(--backgroundSecondary);
    border: 1px solid var(--borderPrimary); border-radius: 4px;
    color: var(--textPrimary);
}
.backtest-error {
    padding: 12px; margin: 12px 0; background: #5c1a1a;
    border: 1px solid #a33; border-radius: 4px; color: #ffcccc;
    display: flex; justify-content: space-between; align-items: center;
}
.backtest-page__desc { color: var(--textTertiary); margin-bottom: 16px; }
```

### 6.8 Wire into App.tsx

Add the Backtest route to `packages/web/src/App.tsx`:

```tsx
// Add lazy import
const Backtest = lazy(() => import("./pages/Backtest/Backtest"));

// Add route inside <Routes>
<Route path="/backtest" element={<Backtest />} />
```

Add the nav link to `packages/web/src/components/NavBar/NavBar.tsx`:

```tsx
<Link className="nav-link" to="/backtest">
    <h1>B<span>a</span>cktest</h1>
</Link>
```

---

## 7. Historical Data Sources

### 7.1 CCXT live fetch (default)

When `data_source = "ccxt"`, the `BacktestDataFeed` fetches OHLCV data
directly from the exchange using CCXT. This requires an internet connection
but no pre-downloaded files.

**Supported exchanges:** Any exchange supported by CCXT that provides
`fetch_ohlcv`. Most major exchanges (Binance, OKX, Kraken, Bitfinex) support
this.

**Rate limits:** CCXT respects each exchange's rate limit automatically.
Fetching 1 year of hourly data (~8,760 candles) typically takes 10–30 seconds
depending on the exchange.

**Timeframe availability:** Not all exchanges provide all timeframes.
Binance supports `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`,
`8h`, `12h`, `1d`, `3d`, `1w`, `1M`.

### 7.2 CSV file (offline)

When `data_source = "csv"`, the feed reads from a local CSV file.
This is faster and works offline.

**Required CSV format:**

```csv
timestamp,open,high,low,close,volume
2024-01-01T00:00:00+00:00,42000.0,42500.0,41800.0,42300.0,1250.5
2024-01-01T01:00:00+00:00,42300.0,42800.0,42100.0,42600.0,980.2
...
```

- `timestamp`: Unix milliseconds (e.g. `1704067200000`) or ISO 8601
- All other columns: float values

**Downloading data to CSV using CCXT:**

```python
# scripts/download_ohlcv.py
import asyncio
import csv
from datetime import datetime, timezone
import ccxt.async_support as ccxt

async def download(exchange_id, symbol, timeframe, start, end, output_path):
    exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})
    since = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp() * 1000)
    all_candles = []
    while since < end_ms:
        candles = await exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        if not candles:
            break
        all_candles.extend(c for c in candles if c[0] < end_ms)
        since = candles[-1][0] + 1
        await asyncio.sleep(exchange.rateLimit / 1000)
    await exchange.close()

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for c in all_candles:
            ts = datetime.fromtimestamp(c[0]/1000, tz=timezone.utc).isoformat()
            writer.writerow([ts, c[1], c[2], c[3], c[4], c[5]])
    print(f"Saved {len(all_candles)} candles to {output_path}")

asyncio.run(download(
    "binance", "BTC/USDT", "1h",
    "2024-01-01", "2024-12-31",
    "data/btc_usdt_1h_2024.csv"
))
```

Run from the monorepo root:
```bash
source .venv/bin/activate
python packages/bot/scripts/download_ohlcv.py
```

### 7.3 Data quality considerations

- **Gaps:** Some exchanges have gaps in historical data. The backtest skips
  candles where indicator calculation fails due to insufficient history.
- **Survivorship bias:** Backtesting on a single symbol avoids survivorship
  bias, but be aware that the strategy was designed for current market
  conditions.
- **Look-ahead bias:** The `BacktestDataFeed` cursor ensures indicators only
  see data up to and including the current candle — no future data leaks.

---

## 8. Running a Backtest

### 8.1 From the web UI

1. Sign in and navigate to `/backtest`
2. Fill in the configuration form:
   - **Exchange:** `binance` (or any CCXT-supported exchange)
   - **Base / Quote:** `BTC` / `USDT`
   - **Timeframe:** `1h` (recommended starting point)
   - **Date range:** Start with a 3-month window to test quickly
   - **Trade Amount:** `1.0` (1 BTC per trade)
   - **Profit Threshold:** `0.0001` (0.01% minimum profit)
   - **Fee Rates:** `0.001` (0.1% taker fee — standard for Binance)
3. Click **Run Backtest** for date ranges ≤ 3 months
4. Click **Run Async** for longer date ranges — the page polls for completion

### 8.2 From the API directly

```bash
# Short range — synchronous
curl -X POST http://localhost:8000/api/v1/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "exchange": "binance",
    "base": "BTC",
    "quote": "USDT",
    "timeframe": "1h",
    "start_date": "2024-01-01",
    "end_date": "2024-03-31",
    "trade_amount": 1.0,
    "profit_percentage_threshold": 0.0001,
    "buy_fee_rate": 0.001,
    "sell_fee_rate": 0.001,
    "rsi_period": 14,
    "ma_period": 14,
    "ma_type": "sma",
    "data_source": "ccxt"
  }' | python3 -m json.tool

# Long range — async
JOB=$(curl -s -X POST http://localhost:8000/api/v1/backtest/async \
  -H "Content-Type: application/json" \
  -d '{...same body...}' | python3 -c "import sys,json; print(json.load(sys.stdin)['message'])")

# Poll until done
while true; do
  STATUS=$(curl -s http://localhost:8000/api/v1/backtest/$JOB | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "Status: $STATUS"
  [ "$STATUS" != "running" ] && break
  sleep 2
done
```

### 8.3 From Python directly

```python
import asyncio
from sonarft_backtest import BacktestRunner, BacktestConfig

async def main():
    runner = BacktestRunner()
    config = BacktestConfig(
        exchange="binance",
        base="BTC",
        quote="USDT",
        timeframe="1h",
        start_date="2024-01-01",
        end_date="2024-06-30",
        trade_amount=1.0,
        profit_percentage_threshold=0.0001,
        buy_fee_rate=0.001,
        sell_fee_rate=0.001,
    )
    report = await runner.run(config)
    print(f"Trades:      {report.total_trades}")
    print(f"Win rate:    {report.win_rate:.1%}")
    print(f"Total P&L:   {report.total_profit:.6f}")
    print(f"Max DD:      {report.max_drawdown:.6f}")
    print(f"Sharpe:      {report.sharpe_ratio:.2f}")
    print(f"Duration:    {report.duration_seconds:.1f}s")

asyncio.run(main())
```

Run from the monorepo root:
```bash
source .venv/bin/activate
cd packages/bot
python -c "import asyncio; exec(open('../../docs/examples/run_backtest.py').read())"
```

---

## 9. Interpreting Results

### 9.1 Key metrics explained

| Metric | Good | Acceptable | Poor | Notes |
|---|---|---|---|---|
| **Win Rate** | > 60% | 50–60% | < 50% | Percentage of profitable trades |
| **Profit Factor** | > 2.0 | 1.5–2.0 | < 1.5 | Gross profit ÷ gross loss |
| **Sharpe Ratio** | > 2.0 | 1.0–2.0 | < 1.0 | Risk-adjusted return (annualised) |
| **Max Drawdown %** | < 5% | 5–15% | > 15% | Largest peak-to-trough decline |
| **Total Profit %** | > 10% | 2–10% | < 2% | Return over the test period |

### 9.2 Equity curve patterns

**Healthy strategy:**
```
Equity
  ↑
  │    /\/\/\
  │   /      \___/\/\/\/\
  │  /
  └──────────────────────→ Time
```
Steady upward trend with controlled drawdowns.

**Overfitted strategy:**
```
Equity
  ↑
  │         /\
  │        /  \
  │       /    \___
  │      /
  └──────────────────────→ Time
```
Strong early performance that degrades — likely overfitted to the test period.

**Unprofitable strategy:**
```
Equity
  ↑
  │\  /\
  │ \/  \/\/\
  │          \___
  └──────────────────────→ Time
```
Consistent losses — strategy parameters need adjustment.

### 9.3 Parameter sensitivity

Run multiple backtests varying one parameter at a time to understand
sensitivity:

```python
# Example: test different profit thresholds
thresholds = [0.00005, 0.0001, 0.0002, 0.0005, 0.001]
for t in thresholds:
    config = BacktestConfig(..., profit_percentage_threshold=t)
    report = await runner.run(config)
    print(f"threshold={t}: trades={report.total_trades}, "
          f"profit={report.total_profit:.4f}, sharpe={report.sharpe_ratio:.2f}")
```

### 9.4 Walk-forward validation

To avoid overfitting, split your data into in-sample (optimisation) and
out-of-sample (validation) periods:

```
|── In-sample (optimise) ──|── Out-of-sample (validate) ──|
  2023-01-01 → 2023-09-30    2023-10-01 → 2023-12-31
```

1. Run backtests on the in-sample period to find good parameters
2. Run **one** backtest on the out-of-sample period with those parameters
3. If out-of-sample performance is similar to in-sample, the strategy is robust

---

## 10. Testing the Backtester

### 10.1 Unit tests

Create `packages/bot/tests/test_sonarft_backtest.py`:

```python
"""Tests for the SonarFT backtesting engine."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sonarft_backtest import BacktestRunner, BacktestConfig
from sonarft_backtest_data import BacktestDataFeed
from sonarft_backtest_execution import BacktestExecution
from sonarft_backtest_report import generate_report, BacktestFill


# ### BacktestDataFeed ###

class TestBacktestDataFeed:
    def test_load_from_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "timestamp,open,high,low,close,volume\n"
            "2024-01-01T00:00:00+00:00,42000,42500,41800,42300,100\n"
            "2024-01-01T01:00:00+00:00,42300,42800,42100,42600,90\n"
        )
        feed = BacktestDataFeed()
        n = feed.load_from_csv("binance", "BTC", "USDT", "1h", str(csv_file))
        assert n == 2

    def test_get_ohlcv_history_respects_cursor(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        rows = ["timestamp,open,high,low,close,volume"]
        for i in range(50):
            rows.append(f"2024-01-01T{i:02d}:00:00+00:00,100,110,90,105,10")
        csv_file.write_text("\n".join(rows))

        feed = BacktestDataFeed()
        feed.load_from_csv("binance", "BTC", "USDT", "1h", str(csv_file))
        feed.set_cursor(20)

        result = asyncio.get_event_loop().run_until_complete(
            feed.get_ohlcv_history("binance", "BTC", "USDT", "1h", limit=14)
        )
        assert len(result) == 14
        # Last candle should be at cursor position 20
        assert result[-1] == feed._data[("binance", "BTC", "USDT", "1h")][20]

    def test_synthetic_order_book_uses_close_price(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "timestamp,open,high,low,close,volume\n"
            "2024-01-01T00:00:00+00:00,100,110,90,105,10\n"
        )
        feed = BacktestDataFeed()
        feed.load_from_csv("binance", "BTC", "USDT", "1h", str(csv_file))
        feed.set_cursor(0)

        ob = asyncio.get_event_loop().run_until_complete(
            feed.get_order_book("binance", "BTC", "USDT")
        )
        assert ob["bids"][0][0] < 105  # bid below close
        assert ob["asks"][0][0] > 105  # ask above close


# ### BacktestExecution ###

class TestBacktestExecution:
    def test_records_fill_on_execute_trade(self):
        execution = BacktestExecution()
        execution.set_timestamp("2024-01-01T00:00:00+00:00")

        trade = {
            "position": "LONG",
            "base": "BTC", "quote": "USDT",
            "buy_exchange": "binance", "sell_exchange": "okx",
            "buy_price": 42000.0, "sell_price": 42100.0,
            "buy_trade_amount": 1.0, "sell_trade_amount": 1.0,
            "buy_value": 42000.0, "sell_value": 42100.0,
            "buy_fee_quote": 42.0, "sell_fee_quote": 42.1,
            "profit": 15.9, "profit_percentage": 0.000379,
            "market_direction_buy": "bull", "market_direction_sell": "bull",
            "market_rsi_buy": 55.0, "market_rsi_sell": 52.0,
        }
        result = asyncio.get_event_loop().run_until_complete(
            execution.execute_trade("backtest", trade)
        )
        assert result is True
        assert len(execution.fills) == 1
        assert execution.fills[0].profit == 15.9
        assert execution.fills[0].cumulative_profit == 15.9

    def test_cumulative_profit_accumulates(self):
        execution = BacktestExecution()
        base_trade = {
            "position": "LONG", "base": "BTC", "quote": "USDT",
            "buy_exchange": "binance", "sell_exchange": "okx",
            "buy_price": 42000.0, "sell_price": 42100.0,
            "buy_trade_amount": 1.0, "sell_trade_amount": 1.0,
            "buy_value": 42000.0, "sell_value": 42100.0,
            "buy_fee_quote": 42.0, "sell_fee_quote": 42.1,
            "profit": 10.0, "profit_percentage": 0.0002,
        }
        for i in range(3):
            execution.set_timestamp(f"2024-01-0{i+1}T00:00:00+00:00")
            asyncio.get_event_loop().run_until_complete(
                execution.execute_trade("backtest", base_trade)
            )
        assert execution.fills[-1].cumulative_profit == pytest.approx(30.0)


# ### BacktestReport ###

class TestBacktestReport:
    def _make_fills(self, profits):
        fills = []
        cumulative = 0.0
        for i, p in enumerate(profits):
            cumulative += p
            fills.append(BacktestFill(
                timestamp=f"2024-01-{i+1:02d}T00:00:00+00:00",
                position="LONG", base="BTC", quote="USDT",
                buy_exchange="binance", sell_exchange="okx",
                buy_price=42000.0, sell_price=42100.0,
                trade_amount=1.0, buy_value=42000.0, sell_value=42100.0,
                buy_fee=42.0, sell_fee=42.1,
                profit=p, profit_percentage=p / 42000,
                cumulative_profit=cumulative,
            ))
        return fills

    def test_win_rate_calculation(self):
        fills = self._make_fills([10, -5, 8, -3, 12])
        report = generate_report(fills, 100, "2024-01-01", "2024-01-05", 1.0)
        assert report.win_rate == pytest.approx(0.6)
        assert report.winning_trades == 3
        assert report.losing_trades == 2

    def test_profit_factor(self):
        fills = self._make_fills([10, -5, 8, -3, 12])
        report = generate_report(fills, 100, "2024-01-01", "2024-01-05", 1.0)
        # gross_profit=30, gross_loss=8
        assert report.profit_factor == pytest.approx(30 / 8, rel=1e-4)

    def test_max_drawdown(self):
        # equity: 10, 5, 13, 10, 22 — peak=22, but max DD is at 5 (peak=10, dd=5)
        fills = self._make_fills([10, -5, 8, -3, 12])
        report = generate_report(fills, 100, "2024-01-01", "2024-01-05", 1.0)
        assert report.max_drawdown == pytest.approx(5.0)

    def test_empty_fills_returns_zero_report(self):
        report = generate_report([], 0, "2024-01-01", "2024-01-01", 0.0)
        assert report.total_trades == 0
        assert report.win_rate == 0.0
        assert report.total_profit == 0.0
```

Run the tests:
```bash
source .venv/bin/activate
cd packages/bot
../../.venv/bin/pytest tests/test_sonarft_backtest.py -v
```

---

## 11. Limitations and Considerations

### 11.1 What the backtester does NOT model

| Limitation | Impact | Mitigation |
|---|---|---|
| **Slippage** | Real fills occur at worse prices than the mid-price | Use conservative fee rates; add a slippage factor to `buy_fee_rate` |
| **Market impact** | Large orders move the market | Keep `trade_amount` small relative to typical volume |
| **Order book depth** | Synthetic order book uses a fixed 0.02% spread | Use real historical order book data if available |
| **Partial fills** | Assumes 100% fill at the target price | Acceptable for liquid pairs; less accurate for illiquid markets |
| **Exchange downtime** | Assumes continuous availability | Add gap detection to skip candles with missing data |
| **Funding rates** | Not modelled for perpetual futures | Only applicable if trading perps |
| **Latency** | Assumes instant execution | In practice, execution takes 100–500ms |

### 11.2 Overfitting risk

Backtesting on the same data used to design the strategy produces optimistic
results. To reduce overfitting:

- Use **walk-forward validation** (see §9.4)
- Test on **multiple symbols** and **multiple time periods**
- Prefer **fewer parameters** — simpler strategies generalise better
- Be sceptical of Sharpe ratios > 3.0 on historical data

### 11.3 Performance expectations

| Date range | Timeframe | Candles | Approx. runtime |
|---|---|---|---|
| 1 month | 1h | ~720 | 5–15s |
| 3 months | 1h | ~2,160 | 15–45s |
| 1 year | 1h | ~8,760 | 1–3 min |
| 1 year | 15m | ~35,040 | 4–12 min |
| 3 years | 1h | ~26,280 | 3–9 min |

Use `data_source = "csv"` with pre-downloaded data to avoid re-fetching on
repeated runs. The async endpoint (`POST /backtest/async`) is recommended for
any run expected to take more than 30 seconds.

### 11.4 Extending the backtester

**Add a second exchange for cross-exchange arbitrage:**

The current implementation supports multiple exchanges if data is loaded for
each. Load data for both exchanges before running:

```python
await feed.load_from_ccxt("binance", "BTC", "USDT", "1h", start, end)
await feed.load_from_ccxt("okx",     "BTC", "USDT", "1h", start, end)
```

The `BacktestDataFeed.get_latest_prices()` method returns one entry per
exchange, enabling the existing cross-exchange arbitrage logic to evaluate
both combinations.

**Add a custom indicator:**

Implement the indicator in `SonarftIndicators` as usual. Because
`BacktestDataFeed` provides the same `get_ohlcv_history` interface as the
live API manager, the indicator will work in backtesting automatically.

**Export results to CSV:**

```python
import csv
report = await runner.run(config)
with open("backtest_trades.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=report.trades[0].keys())
    writer.writeheader()
    writer.writerows(report.trades)
```

---

*End of Backtesting Guide*
