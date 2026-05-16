# Configuration Guide

All trading behavior in SonarFT is controlled by JSON configuration files in `packages/bot/sonarftdata/`. No trading parameters are hardcoded. This document describes every configuration file, its structure, validation rules, and runtime behavior.

---

## Configuration Architecture

`config.json` is the entry point. It defines named configuration sets (e.g. `config_1`, `config_2`) that reference specific setups in each of the other config files. This allows multiple independent configurations to coexist and be selected at bot creation time.

```
config.json
  └── config_1
        ├── parameters_pathname → config_parameters.json → parameters_2
        ├── exchanges_pathname  → config_exchanges.json  → exchanges_1
        ├── symbols_pathname    → config_symbols.json    → symbols_2
        ├── indicators_pathname → config_indicators.json → indicators_1
        ├── fees_pathname       → config_fees.json       → exchanges_fees_1
        └── markets_pathname    → config_markets.json    → market_1
```

---

## config.json

**Purpose:** Maps named configuration sets to specific setups in each config file.

**Structure:**

```json
{
    "config_1": [
        {
            "markets_pathname": "sonarftdata/config_markets.json",
            "markets_setup": 1,
            "exchanges_pathname": "sonarftdata/config_exchanges.json",
            "exchanges_setup": 1,
            "symbols_pathname": "sonarftdata/config_symbols.json",
            "symbols_setup": 2,
            "indicators_pathname": "sonarftdata/config_indicators.json",
            "indicators_setup": 1,
            "parameters_pathname": "sonarftdata/config_parameters.json",
            "parameters_setup": 2,
            "fees_pathname": "sonarftdata/config_fees.json",
            "fees_setup": 1
        }
    ],
    "config_2": [
        {
            "markets_pathname": "sonarftdata/config_markets.json",
            "markets_setup": 1,
            "exchanges_pathname": "sonarftdata/config_exchanges.json",
            "exchanges_setup": 1,
            "symbols_pathname": "sonarftdata/config_symbols.json",
            "symbols_setup": 1,
            "indicators_pathname": "sonarftdata/config_indicators.json",
            "indicators_setup": 1,
            "parameters_pathname": "sonarftdata/config_parameters.json",
            "parameters_setup": 1,
            "fees_pathname": "sonarftdata/config_fees.json",
            "fees_setup": 1
        }
    ]
}
```

**Fields:**

| Field | Type | Description |
|---|---|---|
| `markets_pathname` | string | Path to `config_markets.json` (relative to bot package dir) |
| `markets_setup` | integer | Which `market_N` entry to use |
| `exchanges_pathname` | string | Path to `config_exchanges.json` |
| `exchanges_setup` | integer | Which `exchanges_N` entry to use |
| `symbols_pathname` | string | Path to `config_symbols.json` |
| `symbols_setup` | integer | Which `symbols_N` entry to use |
| `indicators_pathname` | string | Path to `config_indicators.json` |
| `indicators_setup` | integer | Which `indicators_N` entry to use |
| `parameters_pathname` | string | Path to `config_parameters.json` |
| `parameters_setup` | integer | Which `parameters_N` entry to use |
| `fees_pathname` | string | Path to `config_fees.json` |
| `fees_setup` | integer | Which `exchanges_fees_N` entry to use |

**Adding a new configuration:**

1. Add a new entry to each relevant config file (e.g. `parameters_3`, `symbols_3`)
2. Add a new named set to `config.json` referencing those entries
3. Pass the config name when creating a bot via the API

---

## config_parameters.json

**Purpose:** Defines trading parameters — profit thresholds, trade amounts, risk controls, and strategy settings.

**Structure:**

```json
{
    "parameters_1": [
        {
            "strategy": "arbitrage",
            "profit_percentage_threshold": 0.0001,
            "trade_amount": 0.01,
            "is_simulating_trade": 1,
            "max_daily_loss": 100.0,
            "max_trade_amount": 0.1,
            "max_orders_per_minute": 10,
            "spread_increase_factor": 1.00020,
            "spread_decrease_factor": 0.99980,
            "slippage_buffer": 0.0002,
            "flash_crash_threshold": 0.02,
            "max_daily_trades": 0,
            "max_total_exposure": 0.0
        }
    ],
    "parameters_2": [
        {
            "strategy": "market_making",
            "profit_percentage_threshold": 0.0001,
            "trade_amount": 0.01,
            "is_simulating_trade": 1,
            "max_daily_loss": 100.0,
            "max_trade_amount": 0.1,
            "max_orders_per_minute": 10,
            "spread_increase_factor": 1.00115,
            "spread_decrease_factor": 0.99885,
            "slippage_buffer": 0.0002,
            "flash_crash_threshold": 0.02,
            "max_daily_trades": 0,
            "max_total_exposure": 0.0
        }
    ]
}
```

**Field Reference:**

| Field | Type | Constraints | Description |
|---|---|---|---|
| `strategy` | string | `"arbitrage"` or `"market_making"` | Trading strategy |
| `profit_percentage_threshold` | float | `0 < x < 1` | Minimum profit percentage to execute a trade (e.g. `0.0001` = 0.01%) |
| `trade_amount` | float | `> 0` | Trade amount in base currency units |
| `is_simulating_trade` | integer | `0` or `1` | `1` = simulation mode (no real orders); `0` = live trading |
| `max_daily_loss` | float | `>= 0` | Maximum cumulative loss per day in quote currency; `0` = unlimited |
| `max_trade_amount` | float | `>= 0` | Maximum single trade amount; `0` = unlimited |
| `max_orders_per_minute` | integer | `>= 0` | Rate limit for order placement; `0` = unlimited |
| `spread_increase_factor` | float | `1.0 < x < 1.01` (market_making) | Multiplier to widen the ask price |
| `spread_decrease_factor` | float | `0.99 < x < 1.0` (market_making) | Multiplier to narrow the bid price |
| `slippage_buffer` | float | `>= 0` | Additional price buffer for slippage (e.g. `0.0002` = 0.02%) |
| `flash_crash_threshold` | float | `0 < x < 1` | Price drop percentage that triggers a flash crash guard (e.g. `0.02` = 2%) |
| `max_daily_trades` | integer | `>= 0` | Maximum trades per day; `0` = unlimited |
| `max_total_exposure` | float | `>= 0` | Maximum total open position value; `0` = unlimited |

**Validation:** All fields are validated by `ParametersConfig` (Pydantic) in `config_schemas.py` at bot creation time. Invalid values raise `BotCreationError` with a descriptive message.

**Live trading safeguard:** Setting `is_simulating_trade: 0` requires the `SONARFT_ALLOW_LIVE=true` environment variable. Without it, bot creation fails with:
```
BotCreationError: Live trading requires SONARFT_ALLOW_LIVE=true environment variable.
```

**Spread factors for market_making strategy:** The `spread_increase_factor` and `spread_decrease_factor` are validated to be within tight bounds (`1.0–1.01` and `0.99–1.0` respectively) to prevent accidentally setting spreads that are too wide to fill or too narrow to be profitable.

---

## config_exchanges.json

**Purpose:** Lists the exchanges to use for each setup. Exchange IDs must match CCXT exchange identifiers.

**Structure:**

```json
{
    "exchanges_1": ["okx", "binance"],
    "exchanges_2": ["okx", "bitfinex"],
    "exchanges_3": ["okx", "binance", "bitfinex"]
}
```

**Supported exchanges:** Any exchange supported by CCXT. Common options: `okx`, `binance`, `binanceus`, `bitfinex`, `bitget`, `bybit`, `kraken`, `kucoin`, `gate`, `huobi`.

**Single-exchange vs multi-exchange:** A single exchange in the list runs market-making on that exchange. Two or more exchanges enable cross-exchange arbitrage.

**API keys:** For each exchange in the list, set environment variables:
```bash
OKX_API_KEY=your-key
OKX_SECRET=your-secret
OKX_PASSWORD=your-passphrase  # required for OKX

BINANCE_API_KEY=your-key
BINANCE_SECRET=your-secret
```

In simulation mode, API keys are not required for order placement but are needed for market data (order books, OHLCV).

---

## config_symbols.json

**Purpose:** Defines the trading pairs to monitor and trade.

**Structure:**

```json
{
    "symbols_1": [
        { "base": "BTC", "quotes": ["USDT"] },
        { "base": "ETH", "quotes": ["USDT"] }
    ],
    "symbols_2": [
        { "base": "ETH", "quotes": ["USDT"] }
    ]
}
```

**Fields:**

| Field | Type | Description |
|---|---|---|
| `base` | string | Base currency (e.g. `"BTC"`, `"ETH"`) |
| `quotes` | array of strings | Quote currencies (e.g. `["USDT"]`, `["USDT", "BTC"]`) |

Each `base`/`quote` combination becomes a trading pair (`ETH/USDT`). Multiple quotes per base are supported — the bot processes each pair independently.

**Validation:** `SymbolConfig` (Pydantic) validates that `base` is non-empty and `quotes` contains at least one non-empty string.

**Performance note:** Each symbol adds one concurrent coroutine per bot cycle. More symbols = more concurrent exchange API calls. Start with 1–2 symbols and scale up after verifying stability.

---

## config_fees.json

**Purpose:** Defines taker and maker fee rates per exchange. These are used by `SonarftMath.calculate_trade` to verify that the price spread covers trading costs before executing.

**Structure:**

```json
{
    "exchanges_fees_1": [
        { "exchange": "binance",  "buy_fee": 0.001,  "sell_fee": 0.001,  "maker_buy_fee": 0.001,  "maker_sell_fee": 0.001  },
        { "exchange": "okx",      "buy_fee": 0.001,  "sell_fee": 0.001,  "maker_buy_fee": 0.0008, "maker_sell_fee": 0.0008 },
        { "exchange": "bitfinex", "buy_fee": 0.002,  "sell_fee": 0.002,  "maker_buy_fee": 0.001,  "maker_sell_fee": 0.001  }
    ]
}
```

**Fields:**

| Field | Type | Description |
|---|---|---|
| `exchange` | string | CCXT exchange ID |
| `buy_fee` | float | Taker buy fee rate (e.g. `0.001` = 0.1%) |
| `sell_fee` | float | Taker sell fee rate |
| `maker_buy_fee` | float | Maker buy fee rate (optional) |
| `maker_sell_fee` | float | Maker sell fee rate (optional) |

**Fee refresh:** At bot startup, `SonarftApiManager.refresh_fees()` queries the exchange API for live fee rates and updates the in-memory fee structures. This overrides the config file values with current rates. A background task repeats this every 24 hours (configurable via `SONARFT_FEE_REFRESH_INTERVAL`).

**Why config fees matter:** The live fee refresh may fail for some exchanges or pairs. The config file values serve as the fallback. Stale or incorrect fee values will cause the bot to execute trades that are not actually profitable after fees.

---

## config_indicators.json

**Purpose:** Specifies which technical indicators to activate for price adjustment.

**Structure:**

```json
{
    "indicators_1": ["rsi", "stoch rsi"],
    "indicators_2": ["stoch rsi"],
    "indicators_3": ["rsi", "stoch rsi"]
}
```

**Supported values:**

| Value | Indicator | Effect |
|---|---|---|
| `"rsi"` | Relative Strength Index | Overbought/oversold signals adjust spread width |
| `"stoch rsi"` | Stochastic RSI | %K/%D crossover signals refine entry/exit timing |

MACD and SMA/EMA are always computed internally for volatility and trend direction regardless of this setting. This list controls which signals are applied to the price adjustment calculation.

**Warmup period:** Indicators require historical OHLCV data to produce valid signals. MACD requires approximately 45 candles (45 minutes at 1-minute timeframe). The bot logs a warmup warning and skips trades until indicators are ready.

---

## config_markets.json

**Purpose:** Specifies the market type for each setup.

**Structure:**

```json
{
    "market_1": ["crypto"],
    "market_2": ["forex"]
}
```

Currently `"crypto"` is the primary supported market type. The market type influences indicator parameter defaults and price precision handling.

---

## Per-Client Runtime Configuration

When a client updates parameters or indicators via the API (`PUT /api/v1/clients/{id}/parameters`), the new values are persisted to:

```
sonarftdata/config/
├── {client_id}_parameters.json
└── {client_id}_indicators.json
```

These files are loaded on the next bot creation for that client, providing persistence across restarts. The format mirrors the API request body:

```json
{
    "version": 1,
    "exchanges": { "okx": true, "binance": false },
    "symbols": { "ETH/USDT": true, "BTC/USDT": false },
    "strategy": "arbitrage"
}
```

---

## Adding a New Configuration

To add a new trading configuration:

1. Add a new parameters entry to `config_parameters.json`:
   ```json
   "parameters_3": [{ "strategy": "arbitrage", "profit_percentage_threshold": 0.0002, ... }]
   ```

2. Add a new symbols entry to `config_symbols.json`:
   ```json
   "symbols_3": [{ "base": "BTC", "quotes": ["USDT", "ETH"] }]
   ```

3. Add a new named set to `config.json`:
   ```json
   "config_3": [{
       "parameters_pathname": "sonarftdata/config_parameters.json",
       "parameters_setup": 3,
       "symbols_pathname": "sonarftdata/config_symbols.json",
       "symbols_setup": 3,
       ...
   }]
   ```

4. Create a bot using the new config via the API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/clients/{client_id}/bots \
        -H "Content-Type: application/json" \
        -d '{"config": "config_3"}'
   ```

---

## Configuration Validation Summary

| File | Validated by | When |
|---|---|---|
| `config_parameters.json` | `ParametersConfig` (Pydantic) | Bot creation |
| `config_symbols.json` | `SymbolConfig` (Pydantic) | Bot creation |
| `config_fees.json` | `FeeConfig` (Pydantic) | Bot creation |
| `config_exchanges.json` | Non-empty list check | Bot creation |
| `config_indicators.json` | String list (no schema) | Bot creation |
| `config_markets.json` | String list (no schema) | Bot creation |
| Per-client parameters | `ClientParametersConfig` (Pydantic) | API PUT request |
| Per-client indicators | `IndicatorsConfig` (Pydantic) | API PUT request |

Validation errors at bot creation raise `BotCreationError` and are returned as HTTP 422 responses. Validation errors during hot-reload raise `ValueError`, trigger rollback to previous values, and are returned as HTTP 422 responses.
