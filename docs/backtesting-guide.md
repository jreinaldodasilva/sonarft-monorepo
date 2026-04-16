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
