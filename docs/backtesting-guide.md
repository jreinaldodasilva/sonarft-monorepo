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
