# sonarft-bot

**SonarFT core trading engine** — indicators, execution, and exchange integration.

`sonarft-bot` is the pure trading engine layer of the SonarFT monorepo. It has no HTTP server, no authentication, and no WebSocket server of its own. It is imported as a Python library by `packages/api` and driven through the `BotManager` interface.

---

## Status

| Metric | Value |
|---|---|
| Python | 3.11+ |
| Tests | 317 passing |
| Coverage (financial modules) | ≥ 80% (CI enforced) |
| Live trading ready | ✅ Yes |
| Simulation mode | ✅ Default |

---

## Architecture

```
BotManager (sonarft_manager.py)
  └─ SonarftBot (sonarft_bot.py)
        ├─ BotConfig (bot_config.py)          ← config loading
        ├─ SonarftApiManager                  ← exchange connectivity
        │     └─ SharedMarketCache            ← process-level cache (multi-bot)
        ├─ SonarftSearch (sonarft_search.py)
        │     └─ TradeProcessor
        │           ├─ TradeValidator         ← liquidity + spread checks
        │           └─ TradeExecutor          ← async task dispatch
        ├─ SonarftExecution                   ← order placement + position tracking
        ├─ SonarftPrices                      ← VWAP + indicator-driven adjustment
        ├─ SonarftIndicators                  ← RSI, MACD, StochRSI, SMA, volatility
        ├─ SonarftMath                        ← Decimal profit/fee calculation
        ├─ SonarftValidators                  ← liquidity depth + slippage
        └─ SonarftHelpers                     ← SQLite persistence
```

### Module index

| Module | Responsibility |
|---|---|
| `paths.py` | `BOT_DIR`, `DB_PATH`, `bot_path()` — single source of truth for all paths |
| `bot_config.py` | `BotConfig` dataclass + `load_bot_config()` — config loading extracted from `SonarftBot` |
| `shared_cache.py` | `SharedMarketCache` — process-level TTLCache for multi-bot deployments |
| `models.py` | `Trade` dataclass, `vwap()`, `percentage_difference()`, RSI constants |
| `config_schemas.py` | Pydantic v2 models: `ParametersConfig`, `SymbolConfig`, `FeeConfig` |
| `sonarft_manager.py` | `BotManager` — multi-bot lifecycle (create, run, pause, resume, remove) |
| `sonarft_bot.py` | `SonarftBot` — per-bot orchestrator, run loop, periodic tasks, hot-reload |
| `sonarft_api_manager.py` | Exchange API abstraction (ccxt/ccxtpro), caching, market data |
| `sonarft_search.py` | Trade search loop, daily risk controls (loss limit, trade count) |
| `trade_processor.py` | Per-symbol price fetch, profit check, trade dispatch |
| `trade_executor.py` | Async task dispatch, concurrent task limit, session P&L tracking |
| `trade_validator.py` | Pre-execution gate: liquidity depth + spread threshold |
| `sonarft_execution.py` | Order placement (real + simulated), position tracking, balance checks |
| `sonarft_prices.py` | VWAP pricing, indicator-driven price adjustment, strategy dispatch |
| `sonarft_indicators.py` | RSI, MACD, StochRSI, SMA/EMA, volatility, support/resistance |
| `sonarft_math.py` | Decimal-precision profit/fee calculation, exchange precision rules |
| `sonarft_validators.py` | Liquidity depth, spread threshold, slippage tolerance |
| `sonarft_helpers.py` | SQLite persistence (orders, trades, positions, errors, balances, daily_loss) |
| `sonarft_metrics.py` | Structured JSON observability events |

---

## Quick Start

### Install

```bash
pip install -e packages/bot
```

### Run standalone (simulation mode)

```bash
cd packages/bot
python -m sonarft_bot --library ccxtpro --config config_1
```

### Use as a library (from `packages/api`)

```python
from sonarft_manager import BotManager

manager = BotManager(logger=logger)
botid = await manager.create_bot(client_id="user-123", library="ccxtpro", config="config_1")
await manager.run_bot(botid)
```

---

## Configuration

All configuration is JSON-based under `sonarftdata/`. The master index is `sonarftdata/config.json`.

### Config file structure

```
sonarftdata/
├── config.json              ← master index: maps config_N → file paths + setup keys
├── config_markets.json      ← market type (crypto / forex)
├── config_exchanges.json    ← exchange lists per setup
├── config_symbols.json      ← trading pairs per setup
├── config_parameters.json   ← trading parameters per setup
├── config_fees.json         ← exchange fee rates per setup
└── config_indicators.json   ← active indicator list per setup
```

### Key trading parameters (`config_parameters.json`)

| Parameter | Default | Description |
|---|---|---|
| `strategy` | `"arbitrage"` | `"arbitrage"` or `"market_making"` |
| `profit_percentage_threshold` | `0.0001` | Minimum net-of-fee profit % to trade |
| `trade_amount` | `0.01` | Base currency amount per trade |
| `is_simulating_trade` | `1` | `1` = simulation, `0` = live (requires `SONARFT_ALLOW_LIVE=true`) |
| `max_daily_loss` | `100.0` | Daily loss halt threshold (quote currency) |
| `max_trade_amount` | `0.1` | Max single trade size |
| `max_orders_per_minute` | `10` | Order rate cap |
| `slippage_buffer` | `0.0002` | Added to profit threshold; price drift tolerance |
| `flash_crash_threshold` | `0.02` | Max price deviation between exchanges |
| `max_daily_trades` | `0` | Daily trade count cap (0 = disabled) |
| `max_total_exposure` | `0.0` | Aggregate open position cap (0 = disabled) |
| `rsi_overbought` | `70` | RSI overbought threshold |
| `rsi_oversold` | `30` | RSI oversold threshold |
| `monitor_price_timeout` | `120` | Max seconds to wait for favourable price |
| `monitor_order_timeout` | `300` | Max seconds to wait for order fill |
| `min_trading_volume_coefficient` | `50.0` | Liquidity validation multiplier |

### Active indicators (`config_indicators.json`)

Valid values: `"rsi"`, `"stoch rsi"`, `"macd"`, `"sma"`, `"ema"`

Default: `["rsi", "stoch rsi"]`

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `{EXCHANGE}_API_KEY` | Live only | — | Exchange API key (e.g. `BINANCE_API_KEY`) |
| `{EXCHANGE}_SECRET` | Live only | — | Exchange secret |
| `{EXCHANGE}_PASSWORD` | Exchange-dependent | `""` | Exchange passphrase (required for OKX) |
| `SONARFT_ALLOW_LIVE` | Live only | unset | Must be `true` to enable live trading |
| `SONARFT_MAX_FAILURES` | No | `5` | Circuit breaker threshold |
| `SONARFT_BACKOFF_BASE` | No | `30` | Backoff seconds per failure level |
| `SONARFT_CYCLE_SLEEP_MIN` | No | `6` | Min seconds between cycles |
| `SONARFT_CYCLE_SLEEP_MAX` | No | `18` | Max seconds between cycles |
| `SONARFT_MAX_CONCURRENT_TRADES` | No | `10` | Max in-flight trade tasks per bot |
| `SONARFT_FEE_REFRESH_INTERVAL` | No | `86400` | Fee refresh interval in seconds |
| `SONARFT_FEE_ROUNDING` | No | `HALF_EVEN` | Fee rounding: `HALF_EVEN` or `HALF_UP` |
| `SONARFT_ALERT_WEBHOOK` | No | unset | Webhook URL for critical alerts |
| `SONARFT_BACKUP_INTERVAL` | No | `86400` | DB backup interval in seconds (0 = disabled) |
| `SONARFT_BACKUP_DIR` | No | `sonarftdata/backups/` | Backup destination directory |
| `SONARFT_BACKUP_KEEP_DAYS` | No | `7` | Number of daily backups to retain (0 = keep all) |

Copy `.env.example` to `.env` and fill in values. Never commit `.env`.

---

## Live Trading Safety

Live trading requires **two independent opt-ins**:

1. `is_simulating_trade: 0` in `config_parameters.json`
2. `SONARFT_ALLOW_LIVE=true` environment variable

Both must be set. Missing either raises `BotCreationError` at startup.

**Recommended first live deployment parameters:**

```json
{
  "max_trade_amount": 0.01,
  "max_daily_loss": 50.0,
  "max_orders_per_minute": 3,
  "max_daily_trades": 20
}
```

---

## Data Persistence

All runtime data is stored in SQLite (`sonarftdata/history/sonarft.db`) with WAL mode for concurrent access.

| Table | Contents | Retention |
|---|---|---|
| `orders` | All trade search records | Last 10,000 per bot |
| `trades` | Successful trade executions | Last 10,000 per bot |
| `positions` | Open/closed position tracker | No automatic purge |
| `daily_loss` | Daily loss accumulator per bot | No automatic purge |
| `errors` | Error events | No automatic purge |
| `balances` | Balance snapshots | No automatic purge |

**Docker deployment:** Mount `sonarftdata/history/`, `sonarftdata/bots/`, and `sonarftdata/backups/` as Docker volumes to persist data across container replacements. See `infra/docker-compose.yml`.

---

## Testing

```bash
# Run all tests
pytest tests/ -q

# Run with coverage (financial modules)
pytest tests/ -q \
  --cov=sonarft_math \
  --cov=sonarft_execution \
  --cov=sonarft_search \
  --cov=bot_config \
  --cov-report=term-missing \
  --cov-fail-under=80

# Run property-based tests only
pytest tests/test_hypothesis_math.py -v

# Run simulation integration test
pytest tests/test_simulation_integration.py -v
```

### Test file index

| File | Coverage |
|---|---|
| `test_sonarft_bot.py` | Config validation, live mode guard, simulation mode, daily loss, hot-reload, env vars |
| `test_sonarft_math.py` | `calculate_trade` profitability, fees, edge cases, precision, VWAP |
| `test_hypothesis_math.py` | Property-based: profit sign, NaN/Inf, zero amount, fee monotonicity |
| `test_sonarft_math_precision.py` | Decimal precision, rounding, fee rounding modes |
| `test_sonarft_indicators.py` | RSI, MACD, StochRSI, SMA, volatility, support/resistance |
| `test_sonarft_prices.py` | Price adjustment, VWAP blend, strategy dispatch |
| `test_sonarft_api_manager.py` | API dispatch, caching, fee lookup, order book, recovery |
| `test_sonarft_search_execution.py` | Trade dispatch, partial fills, botid, monitor_order paths |
| `test_sonarft_helpers.py` | SQLite CRUD, position tracker, purge, backup |
| `test_sonarft_validators.py` | Liquidity checks, spread threshold |
| `test_sonarft_manager.py` | BotManager lifecycle, hot-reload |
| `test_trade_executor.py` | Task dispatch, concurrent limit, monitor, shutdown |
| `test_phase3_performance.py` | Cache TTL, concurrent indicator fetch, cycle timing |
| `test_phase4_features.py` | Circuit breaker, flash crash, rate limiting, exposure, position tracker |
| `test_simulation_integration.py` | End-to-end simulation flow |

---

## Hot-Reload

Trading parameters can be updated on a running bot without restart:

```python
await manager.reload_parameters(client_id, {
    "profit_percentage_threshold": 0.0005,
    "trade_amount": 0.02,
    "strategy": "market_making",
    "max_daily_loss": 200.0,
    "slippage_buffer": 0.0003,
    "flash_crash_threshold": 0.015,
    "max_daily_trades": 50,
    "max_total_exposure": 500.0,
    "spread_increase_factor": 1.00115,
    "spread_decrease_factor": 0.99885,
    "max_trade_amount": 0.2,
    "max_orders_per_minute": 5,
    "is_simulating_trade": 1,
})
```

All 13 parameters are hot-reloadable. Validation uses Pydantic `ParametersConfig`. Invalid values are rejected and the old values are restored (rollback on failure). Changes are audit-logged at `WARNING` level.

---

## Observability

All events are emitted as structured JSON to the `sonarft.metrics` logger:

| Event type | Emitted by | Key fields |
|---|---|---|
| `signal` | `TradeProcessor` | `symbol`, `buy_exchange`, `sell_exchange`, `expected_profit_pct`, `signal_type` |
| `order_execution` | `SonarftExecution` | `order_id`, `side`, `requested_price`, `executed_price`, `slippage_pct`, `fill_status` |
| `trade_result` | `SonarftExecution` | `position`, `realized_profit`, `realized_profit_pct`, `success` |
| `risk_event` | `SonarftExecution` | `risk_event`, `detail` (size_limit, exposure_limit, rate_limit, flash_crash) |
| `liquidity_check` | `SonarftValidators` | `exchange`, `side`, `required_amount`, `available_depth`, `passed` |
| `api_call` | `SonarftApiManager` | `exchange`, `method`, `latency_ms`, `success` |
| `cycle` | `TradeProcessor` | `cycle_duration_ms`, `trades_found`, `trades_skipped` |
| `session_pnl` | `TradeExecutor` | `session_trades`, `session_profit`, `daily_loss_accumulated` |

Configure a log handler for `sonarft.metrics` to ingest into ELK, Datadog, or CloudWatch.

---

## Documentation

| Document | Contents |
|---|---|
| `docs/architecture/bot-overview.md` | Module structure, dependency graph, complexity hotspots |
| `docs/async/bot-concurrency.md` | Async patterns, race conditions, task lifecycle |
| `docs/trading/engine-review.md` | Trade detection logic, VWAP, spread, fee handling |
| `docs/trading/math-analysis.md` | Financial precision, Decimal arithmetic, rounding |
| `docs/trading/indicators-review.md` | Indicator pipeline, NaN handling, signal generation |
| `docs/trading/execution-review.md` | Order execution, exchange integration, partial fills |
| `docs/operations/bot-config.md` | Configuration system, env vars, Docker |
| `docs/operations/bot-performance.md` | Performance analysis, caching, scaling |
| `docs/security/bot-risks.md` | Security audit, trading safety controls |
| `docs/quality/bot-testing.md` | Code quality, test coverage, refactoring |
| `docs/review/final-audit-report.md` | Executive summary, risk ranking, production readiness |
| `docs/roadmap/implementation-roadmap.md` | All 40 tasks, 6 phases, commit history |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `pandas` | 3.0.2 | OHLCV data processing |
| `pandas-ta` | 0.4.71b0 | Technical indicators (RSI, MACD, StochRSI, SMA, EMA) |
| `ccxt` | 4.5.48 | Exchange REST API |
| `ccxt[pro]` | 4.5.48 | Exchange WebSocket API |
| `cachetools` | ≥5.3 | TTLCache for market data caching |
| `pydantic` | 2.11.7 | Config validation |
| `simple-websocket` | 1.1.0 | WebSocket support |

Dev dependencies: `pytest`, `pytest-asyncio`, `pytest-cov`, `hypothesis`, `ruff`, `mypy`
