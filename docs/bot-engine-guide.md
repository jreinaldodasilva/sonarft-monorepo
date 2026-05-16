# Bot Engine Guide

The bot engine (`packages/bot`) is a pure Python trading library with no HTTP or authentication concerns. It is imported by `packages/api` as `sonarft-bot` and driven entirely through `BotManager`.

---

## Module Overview

| Module | Class | Responsibility |
|---|---|---|
| `sonarft_manager.py` | `BotManager` | Bot lifecycle, client→bot mapping, asyncio.Lock |
| `sonarft_bot.py` | `SonarftBot` | Config loading, module wiring, run loop, circuit breaker |
| `sonarft_search.py` | `SonarftSearch` | Concurrent symbol search, daily risk controls |
| `trade_processor.py` | `TradeProcessor` | Per-symbol price fetch, adjustment, profit check |
| `trade_validator.py` | `TradeValidator` | Liquidity and spread validation |
| `trade_executor.py` | `TradeExecutor` | Async task management for execution |
| `sonarft_prices.py` | `SonarftPrices` | VWAP, weighted price adjustment, spread logic |
| `sonarft_indicators.py` | `SonarftIndicators` | RSI, MACD, StochRSI, SMA, volatility |
| `sonarft_math.py` | `SonarftMath` | Profit/fee calculation, exchange precision rules |
| `sonarft_execution.py` | `SonarftExecution` | Order placement (real and simulated) |
| `sonarft_validators.py` | `SonarftValidators` | Order book depth and spread threshold checks |
| `sonarft_api_manager.py` | `SonarftApiManager` | Exchange API abstraction (ccxtpro/ccxt) |
| `sonarft_helpers.py` | `SonarftHelpers` | File I/O, trade history persistence |
| `sonarft_metrics.py` | `SonarftMetrics` | Metrics collection and JSON line emission |
| `config_schemas.py` | Pydantic models | Config validation at load time |
| `models.py` | Dataclasses | Shared data models |

---

## BotManager

`BotManager` is the entry point for all bot lifecycle operations. It maintains a registry of all running bots and maps client IDs to their bot IDs.

```python
class BotManager:
    def __init__(self, logger=None):
        self._bots: dict[str, SonarftBot] = {}
        self._clients: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()
```

### Key Operations

**Creating a bot:**
```python
botid = await manager.create_bot(client_id, library="ccxtpro", config="config_1")
```

This creates a `SonarftBot` instance, calls `create_bot(config_setup)` on it (which loads config and wires all modules), registers it in `_bots` and `_clients`, and returns the `botid`. The run loop is **not** started — call `run_bot(botid)` separately.

**Running a bot:**
```python
await manager.run_bot(botid)
```

This calls `SonarftBot.run_bot()`, which is a long-running coroutine. In the API layer, this is dispatched as an `asyncio.Task` so it runs concurrently with other operations.

**Removing a bot:**
```python
await manager.remove_bot(botid)
```

Calls `stop_bot()` outside the lock (to avoid blocking during network I/O), then removes the bot from the registry and deletes its registry file.

**Hot-reloading parameters:**
```python
await manager.reload_parameters(client_id, new_parameters)
```

Applies new parameters to all running bots for the client. Uses `SonarftBot.apply_parameters()` which validates and rolls back on failure.

---

## SonarftBot Lifecycle

```
create_bot(config_setup)
  ├── create_botid()                    # UUID
  ├── _write_botid_file()               # sonarftdata/bots/{botid}.json
  ├── load_configurations(config_setup) # load + validate all JSON config
  ├── SonarftApiManager(...)            # exchange API abstraction
  ├── _load_api_keys()                  # from environment variables
  ├── initialize_modules()              # wire all dependencies
  ├── api_manager.load_all_markets()    # fetch exchange market data
  ├── _validate_precision_rules()       # warn on missing precision data
  ├── api_manager.refresh_fees()        # fetch live fee rates
  ├── asyncio.create_task(_periodic_fee_refresh)   # 24h background task
  ├── asyncio.create_task(_periodic_db_backup)     # 24h background task
  └── _reconcile_open_orders()          # cancel stale orders (live mode only)

run_bot()
  └── while not _stop_event.is_set():
        ├── sonarft_search.search_trades(botid)
        ├── on success: reset consecutive_failures, sleep 6–18s
        └── on failure: increment consecutive_failures
              ├── if >= max_failures: circuit breaker → _send_alert → stop
              └── else: exponential backoff sleep

stop_bot()
  ├── _stop_event.set()
  ├── cancel _fee_refresh_task
  ├── cancel _db_backup_task
  ├── trade_executor.shutdown()         # await in-flight trade tasks
  └── close all exchange connections
```

### Circuit Breaker

The run loop tracks consecutive failures. After `SONARFT_MAX_FAILURES` (default: 5) consecutive errors, the bot:

1. Sets `_stop_event` to stop the run loop
2. Calls `_send_alert()` to POST to `SONARFT_ALERT_WEBHOOK` (if configured)
3. Logs an error with the failure count and last error message

The backoff between retries is `SONARFT_BACKOFF_BASE * consecutive_failures` seconds (default: 30s, 60s, 90s, 120s, 150s).

### Startup Reconciliation (Live Mode Only)

In live mode (`is_simulating_trade=0`), the bot queries all configured exchanges for open orders on all configured symbols and cancels any stale orders from previous runs. This prevents orphaned orders from accumulating on the exchange.

Open positions (first leg filled, second leg not completed) are logged as warnings and trigger an alert. These require manual review on the exchange.

---

## SonarftSearch

`SonarftSearch` orchestrates the trade search across all configured symbols. Each call to `search_trades()` processes all symbols concurrently:

```python
async def search_trades(self, botid) -> None:
    if self._paused or await self.is_halted():
        return

    futures = [
        self.trade_processor.process_symbol(
            botid, symbol, self.trade_amount, self.profit_percentage_threshold
        )
        for symbol in self.symbols
    ]
    results = await asyncio.gather(*futures, return_exceptions=True)
```

### Daily Risk Controls

`SonarftSearch` enforces daily risk limits:

- **Max daily loss:** Accumulated losses are persisted to SQLite (`sonarftdata/history/sonarft.db`). If `daily_loss_accumulated >= max_daily_loss`, `is_halted()` returns `True` and all trades are skipped.
- **Max daily trades:** If `_daily_trades_count >= max_daily_trades`, trading halts for the day.
- **Daily reset:** Both counters reset at midnight (detected by date change on each `search_trades` call).

The SQLite persistence ensures that a bot restart mid-day does not reset the daily loss counter.

---

## Price Analysis

### VWAP Calculation

Initial bid/ask prices are established using Volume-Weighted Average Price from the order book:

```python
def get_weighted_prices(self, depth: int, order_book: dict) -> tuple[float, float]:
    bids = order_book['bids'][:depth]
    asks = order_book['asks'][:depth]

    total_bid_volume = sum(volume for _, volume in bids)
    bid_vwap = sum(price * volume for price, volume in bids) / total_bid_volume

    total_ask_volume = sum(volume for _, volume in asks)
    ask_vwap = sum(price * volume for price, volume in asks) / total_ask_volume

    return bid_vwap, ask_vwap
```

VWAP is preferred over the best bid/ask because it accounts for order book depth. A large order at the best price may not be fillable at that price — VWAP gives a more realistic execution price.

### Price Adjustment

`weighted_adjust_prices` combines multiple market signals to compute adjusted bid/ask prices:

| Signal | Source | How it affects prices |
|---|---|---|
| Market direction | SMA/EMA trend | Bull: raise ask, lower bid; Bear: inverse |
| Short-term trend | Recent OHLCV close changes | Amplifies or dampens direction signal |
| RSI | pandas-ta | Overbought (≥70): widen spread; Oversold (≤30): tighten |
| StochRSI %K/%D | pandas-ta | Crossover signals refine entry/exit timing |
| MACD | pandas-ta | Weights the dynamic volatility adjustment factor |
| Volatility | Order book mid-price std dev | Scales the final price adjustment magnitude |
| Support/resistance | Historical high/low | Clamps adjusted prices within bounds |
| Spread factors | Config parameters | Applied based on combined direction signal |

The final adjusted price is a weighted blend:
```
adjusted_price = (target_vwap * volatility_weight) + (current_weighted_price * (1 - volatility_weight))
```

---

## Technical Indicators

All indicators are computed from OHLCV data fetched via `SonarftApiManager.get_history()`. OHLCV data format: `[timestamp, open, high, low, close, volume]`.

### RSI (Relative Strength Index)

```python
close_prices = pd.Series([x[4] for x in ohlcv])
rsi = pta.rsi(close_prices, length=moving_average_period)
return float(rsi.iloc[-1])
```

- Overbought threshold: ≥ 70 (widen spread — expect price reversal)
- Oversold threshold: ≤ 30 (tighten spread — expect price recovery)
- Default period: 14 candles

### Stochastic RSI

```python
stochrsi = pta.stochrsi(close_prices, length=period)
k = float(stochrsi['STOCHRSIk_...'].iloc[-1])
d = float(stochrsi['STOCHRSId_...'].iloc[-1])
```

%K/%D crossovers signal momentum shifts. Used to refine entry/exit timing beyond RSI alone.

### MACD

```python
macd_df = pta.macd(close_prices, fast=12, slow=26, signal=9)
macd_line = float(macd_df['MACD_12_26_9'].iloc[-1])
signal_line = float(macd_df['MACDs_12_26_9'].iloc[-1])
histogram = float(macd_df['MACDh_12_26_9'].iloc[-1])
```

MACD is used to weight the dynamic volatility adjustment factor. A strong MACD signal increases the weight of the trend-based price adjustment.

**Warmup requirement:** MACD requires approximately 45 candles (26 + 9 + buffer) before producing valid signals. The bot logs a warmup warning and skips trades until all indicators are ready.

### SMA / EMA (Market Direction)

```python
sma = pta.sma(close_prices, length=period)
# or
ema = pta.ema(close_prices, length=period)
```

Used to determine overall market direction (`'bull'`, `'bear'`, `'neutral'`). The direction drives the primary spread adjustment.

### Volatility

Computed from the standard deviation of order book mid-prices over a rolling window. Classified as `Low`, `Medium`, or `High`. Higher volatility increases the spread adjustment magnitude.

---

## Profit Calculation

`SonarftMath.calculate_trade` computes whether a trade is profitable after fees:

```python
# Buy side
buy_price = round(buy_price, buy_rules['prices_precision'])
buy_fee_quote = round(buy_price * trade_amount * buy_fee_rate, buy_rules['fee_precision'])
buy_value = buy_price * trade_amount + buy_fee_quote

# Sell side
sell_price = round(sell_price, sell_rules['prices_precision'])
sell_fee_quote = round(sell_price * trade_amount * sell_fee_rate, sell_rules['fee_precision'])
sell_value = sell_price * trade_amount - sell_fee_quote

# Profit
profit = sell_value - buy_value
profit_percentage = profit / buy_value
```

The trade is only executed if `profit_percentage >= profit_percentage_threshold`.

**Exchange precision rules** (`EXCHANGE_RULES`) define per-exchange rounding precision for prices, amounts, and fees. Supported exchanges with hardcoded rules: `okx`, `bitfinex`, `binance`. For other exchanges, live precision is fetched from the exchange API via `load_all_markets()`.

---

## Trade Validation

Before execution, two parallel validations run via `asyncio.gather`:

### Liquidity Depth Verification

`SonarftValidators.deeper_verify_liquidity` checks that the order book on both exchanges has sufficient depth and volume to absorb the trade amount without excessive slippage:

```python
result_buy, result_sell = await asyncio.gather(
    self.sonarft_validators.deeper_verify_liquidity(buy_exchange, base, quote, trade_amount),
    self.sonarft_validators.deeper_verify_liquidity(sell_exchange, base, quote, trade_amount),
)
if result_buy is False or result_sell is False:
    return  # insufficient liquidity
```

### Spread Threshold Verification

`SonarftValidators.verify_spread_threshold` computes a dynamic spread threshold based on historical data and current volatility classification, then verifies the current spread ratio falls within acceptable bounds.

---

## Order Execution

`SonarftExecution.execute_trade` places limit orders on the buy and sell exchanges:

### Simulation Mode

```python
if self.is_simulation_mode:
    slippage = random.uniform(0, 0.001)
    executed_amount = trade_amount
    remaining_amount = 0
    order_placed_id = f"{side}_{random.randint(100000, 999999)}"
```

Simulation generates synthetic order IDs and simulates slippage. No exchange API calls are made for order placement. Balance checks short-circuit: `if self.is_simulation_mode: return True`.

### Live Mode

```python
if not self.is_simulation_mode:
    order_placed = await self.api_manager.create_order(
        exchange_id, symbol, 'limit', side, amount, price
    )
```

Live mode places real limit orders on the exchange. The execution module includes:

- **Flash crash guard:** If the price drops more than `flash_crash_threshold` (default: 2%) between price fetch and order placement, the trade is aborted.
- **Max trade amount guard:** If `trade_amount > max_trade_amount`, the trade is aborted.
- **Order rate limiting:** If `max_orders_per_minute > 0`, order placement is rate-limited.
- **Order monitoring:** After placement, the order is monitored until filled or timed out. On timeout, the order is cancelled with exponential backoff retry.

### Trade Position

The trade position (`LONG` or `SHORT`) is determined by market direction and RSI/StochRSI signals:
- `LONG`: Buy on the lower-priced exchange, sell on the higher-priced exchange
- `SHORT`: Inverse

---

## Exchange API Abstraction

`SonarftApiManager` abstracts all exchange API calls through a single dispatch method:

```python
await self.call_api_method(
    exchange_id,
    'fetch_order_book',   # ccxt (REST) method name
    'watch_order_book',   # ccxtpro (WebSocket) method name
    symbol
)
```

The library selection (`ccxtpro` or `ccxt`) is set at bot creation time. WebSocket (ccxtpro) is the default — it is faster and lower latency. REST (ccxt) is the fallback for exchanges that don't support WebSocket streaming.

---

## Trade History Persistence

Trade and order history are persisted to JSON files:

```
sonarftdata/history/
├── {botid}_orders.json   # individual order records
└── {botid}_trades.json   # completed trade records
```

`SonarftHelpers` handles all file I/O using `asyncio.to_thread` to avoid blocking the event loop on disk writes.

Daily loss tracking uses SQLite (`sonarftdata/history/sonarft.db`) for atomic upserts that survive concurrent access and process restarts.

---

## Metrics Collection

`SonarftMetrics` emits structured JSON lines to the metrics logger (`sonarft.metrics`), which writes to `logs/sonarft_metrics.jsonl`. Each metric event includes:

- Timestamp
- Bot ID
- Event type (trade, order, error, cycle)
- Relevant numeric values (profit, price, amount, duration)

The metrics file is separate from the human-readable log and can be parsed independently by log aggregation tools (Loki, CloudWatch, Datadog).
