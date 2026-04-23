# SonarFT Bot — Indicator Pipeline Review

**Prompt:** 05-BOT-INDICATORS  
**Reviewer role:** Senior quantitative analyst / indicator systems reviewer  
**Date:** July 2025  
**Status:** Complete  
**Prerequisites:** [01-BOT-ARCH](../architecture/bot-overview.md), [04-BOT-MATH](math-analysis.md)

---

## 1. Indicator Implementation Audit

All indicators live in `SonarftIndicators` (`sonarft_indicators.py`). Each delegates data fetching to `SonarftApiManager` and computation to `pandas-ta`.

### RSI — `get_rsi()`

| Attribute | Value |
|---|---|
| Formula | Wilder's smoothed RSI via `pandas_ta.rsi()` |
| Data source | OHLCV close prices (`x[4]`) via `get_history()` |
| Lookback requested | `moving_average_period + 2` candles (default: 16) |
| Minimum valid | `moving_average_period` candles (14) |
| Output | `float` — last RSI value (`rsi.iloc[-1]`) |
| NaN guard | `if pd.isna(value): return None` ✅ |
| Cache | 60s TTL per `(exchange, base/quote, period, timeframe)` ✅ |

**Finding I-01 (Low):** `get_history()` is called with `limit = moving_average_period + 2`. pandas-ta's RSI requires at least `length + 1` candles to produce a valid first value (it needs one prior close to compute the first change). Requesting `period + 2` provides one extra candle of buffer. This is correct. ✅

**Finding I-02 (Low):** The RSI data sufficiency check:
```python
if not ohlcv or len(ohlcv) < moving_average_period:
    raise ValueError(...)
```
raises `ValueError` which is caught by the outer `except Exception` and returns `None`. The check uses `moving_average_period` (14) as the minimum, but pandas-ta needs `length + 1` = 15 candles for the first valid RSI. If exactly 14 candles are returned, `rsi.iloc[-1]` will be `NaN`, caught by the `pd.isna()` guard. ✅ Safe but the minimum check could be `moving_average_period + 1` for clarity.

---

### MACD — `get_macd()`

| Attribute | Value |
|---|---|
| Formula | EMA(12) − EMA(26), signal = EMA(9) of MACD, histogram = MACD − signal |
| Data source | OHLCV close prices |
| Lookback requested | `long_period + signal_period + warmup` = 26 + 9 + 10 = 45 candles |
| Minimum valid | `long_period + signal_period` = 35 candles |
| Output | `(float, float, float)` — (MACD, signal, histogram) |
| NaN guard | `if pd.isna(m) or pd.isna(s) or pd.isna(h): return None` ✅ |
| Cache | 60s TTL ✅ |

**Finding I-03 (Medium):** The MACD column name is constructed as:
```python
macd_col = f'MACD_{short_period}_{long_period}_{signal_period}'
```
pandas-ta's `macd()` returns columns named `MACD_12_26_9`, `MACDs_12_26_9`, `MACDh_12_26_9`. The code checks `if macd_col not in macd.columns` and raises `KeyError` with the available columns. This is a good defensive check. However, if pandas-ta changes its column naming convention in a future version, this will break silently (the `except Exception` catches the `KeyError` and returns `None`). The trade will be skipped rather than crashing. ✅ Safe but fragile.

**Finding I-04 (Low):** The `warmup=10` parameter adds 10 extra candles beyond the theoretical minimum. This is a good practice — EMA-based indicators need additional warmup candles to stabilise from their initial seed value. 10 candles is a reasonable warmup for a 26-period EMA. ✅

---

### Stochastic RSI — `get_stoch_rsi()`

| Attribute | Value |
|---|---|
| Formula | StochRSI = (RSI − min(RSI, n)) / (max(RSI, n) − min(RSI, n)), smoothed with %K and %D |
| Data source | OHLCV close prices |
| Lookback requested | `rsi_period + stoch_period + d_period + 1` = 14 + 14 + 3 + 1 = 32 candles |
| Minimum valid | `rsi_period + stoch_period` = 28 candles |
| Output | `(float, float)` — (%K, %D) |
| NaN guard | `if pd.isna(k_val) or pd.isna(d_val): return None` ✅ |
| Cache | 60s TTL ✅ |

**Finding I-05 (Medium):** The pandas-ta `stochrsi()` call uses keyword arguments:
```python
stoch_rsi = pta.stochrsi(close_prices, length=stoch_period, rsi_length=rsi_period, k=k_period, d=d_period)
```
The column extraction uses positional indexing:
```python
k_val = last_row.iloc[0]
d_val = last_row.iloc[1]
```
pandas-ta returns StochRSI columns as `STOCHRSIk_14_14_3_3` and `STOCHRSId_14_14_3_3`. Using `iloc[0]` and `iloc[1]` assumes the column order is always K then D. This is true for the current pandas-ta version but is fragile — a future version could reorder columns. Using named column access (e.g. `stoch_rsi.filter(like='STOCHRSIk').iloc[-1, 0]`) would be more robust.

---

### Market Direction — `get_market_direction()`

| Attribute | Value |
|---|---|
| Formula | SMA or EMA of close prices; `current_price > MA` → bull, `< MA` → bear, `== MA` → neutral |
| Data source | OHLCV close prices |
| Lookback requested | `moving_average_period + 2` candles |
| Output | `'bull'` / `'bear'` / `'neutral'` |
| NaN guard | `if pd.isna(ma_value) or pd.isna(current_price): return 'neutral'` ✅ |
| Cache | 60s TTL ✅ |

**Finding I-06 (Low):** `current_price = close_prices.iloc[-1]` — the most recent close price. `ma_value = moving_average.iloc[-1]` — the MA value at the most recent candle. Both use `iloc[-1]` which is the last element of the Series. Since OHLCV data is returned in chronological order (oldest first), `iloc[-1]` is the most recent candle. ✅

**Finding I-07 (Low):** The `== MA` case for `neutral` is a floating-point equality comparison. In practice, `current_price == ma_value` will almost never be exactly true for float values. The `neutral` return from this branch is effectively dead code — `neutral` is only returned via the NaN guard. This is harmless but misleading.

---

### Short-term Market Trend — `get_short_term_market_trend()`

| Attribute | Value |
|---|---|
| Formula | Average close of last N/2 candles vs. average close of prior N/2 candles |
| Data source | OHLCV close prices |
| Lookback requested | `limit` candles (default: 6) |
| Minimum valid | `2 * (limit // 2)` = 6 candles |
| Output | `'bull'` / `'bear'` / `'neutral'` |
| NaN guard | `if previous_avg_price == 0: return 'neutral'` ✅ |
| Cache | None ⚠️ |

**Finding I-08 (Medium):** `get_short_term_market_trend()` has **no indicator cache**. It is called twice per `weighted_adjust_prices()` invocation (once for buy exchange, once for sell exchange), and `weighted_adjust_prices()` is called once per trade combination. With multiple symbols and multiple exchange combinations, this function may be called many times per cycle without caching. Each call fetches 6 OHLCV candles from the exchange. The OHLCV cache in `SonarftApiManager` (60s TTL) will serve most of these from cache, but the computation itself is repeated unnecessarily.

**Finding I-09 (Low):** The threshold comparison:
```python
if price_change > threshold * 100:
    return 'bull'
elif price_change < -(threshold * 100):
    return 'bear'
```
`price_change` is already computed as `100 * (current - previous) / previous` (percentage). `threshold` defaults to `0.001`. So the comparison is `price_change > 0.1%`. This is correct — a 0.1% price change over 3 candles triggers a trend signal. ✅

---

### Volatility — `get_volatility()`

| Attribute | Value |
|---|---|
| Formula | `np.std` of absolute price deviations from mid-price across order book levels |
| Data source | Live order book (not OHLCV) |
| Lookback | None — instantaneous order book snapshot |
| Output | `float` — standard deviation in price units |
| NaN guard | `if np.isnan(volatility): return 0.0` ✅ |
| Cache | None — delegates to `get_order_book()` which has 2s TTL |

As noted in Prompt 04 (M-07), this is not a standard financial volatility measure. It is an order book spread dispersion metric in price units.

---

### Support & Resistance — `get_support_price()` / `get_resistance_price()`

| Attribute | Value |
|---|---|
| Formula | `min(low_prices)` / `max(high_prices)` over lookback period |
| Data source | OHLCV low (`x[3]`) / high (`x[2]`) prices |
| Lookback | 24 candles at 1h timeframe (24 hours) |
| Output | `float` or `None` |
| NaN guard | `if history_data is None or len(history_data) < lookback_period: return None` ✅ |
| Cache | None ⚠️ |

**Finding I-10 (Medium):** `get_support_price()` and `get_resistance_price()` have **no indicator cache**. They fetch 24 hourly candles per call. Each `weighted_adjust_prices()` invocation calls both once. The OHLCV cache in `SonarftApiManager` (TTL = 3600s for 1h candles) will serve these from cache after the first fetch. ✅ The computation (`min()`/`max()`) is trivial. No performance concern.

However, using the 24-hour low/high as support/resistance is a very simple approximation. In trending markets, the 24h low may be the current price (no support), and the 24h high may be the current price (no resistance). The clamping logic:
```python
if support_price is not None and adjusted_buy_price < support_price:
    adjusted_buy_price = support_price
if resistance_price is not None and adjusted_sell_price > resistance_price:
    adjusted_sell_price = resistance_price
```
could force `adjusted_buy_price > adjusted_sell_price` in a trending market, producing a negative spread that `calculate_trade()` would correctly reject as unprofitable.

---

### ATR — `get_atr()`

| Attribute | Value |
|---|---|
| Formula | Average True Range via `pandas_ta.atr()` |
| Data source | OHLCV high, low, close |
| Lookback | `atr_period + 1` = 15 candles |
| Output | `float` or `None` |
| NaN guard | `if pd.isna(value): return None` ✅ |
| Cache | None |

**Finding I-11 (Low):** `get_atr()` is defined but **never called** anywhere in the codebase. It is dead code. It should either be used (e.g. for dynamic position sizing) or removed.

---

### 24h High/Low — `get_24h_high()` / `get_24h_low()`

| Attribute | Value |
|---|---|
| Formula | `np.max(high)` / `np.min(low)` over 1440 1m candles |
| Data source | OHLCV high (`x[2]`) / low (`x[3]`) |
| Lookback | 1440 candles (24 hours at 1m) |
| Output | `float` or `None` |
| NaN guard | Insufficient data → `None` ✅ |
| Cache | 300s TTL (5 minutes) ✅ |

**Finding I-12 (Low):** `get_24h_high()` and `get_24h_low()` are defined but **never called** anywhere in the codebase. Dead code alongside `get_atr()`.

---

### Market Movement — `market_movement()`

| Attribute | Value |
|---|---|
| Formula | Sum of top-N ask prices minus sum of top-N bid prices; spread rate of change |
| Data source | Live order book |
| Output | `("fast"/"slow", "bull"/"bear")` |
| NaN guard | None needed — arithmetic on order book floats |
| Cache | None — delegates to `get_order_book()` (2s TTL) |

As noted in Prompt 03 (T-07), the spread formula sums prices rather than volumes. The `_market_movement_buy` and `_market_movement_sell` results from `weighted_adjust_prices()` are assigned but **never used** in the price adjustment logic — they are computed and discarded.

**Finding I-13 (Medium):** `_market_movement_buy` and `_market_movement_sell` are fetched in the 16-indicator gather of `weighted_adjust_prices()` but the results are assigned to throwaway variables (`_market_movement_buy`, `_market_movement_sell` with leading underscore). The two `market_movement()` calls consume API quota and add to the 30s timeout budget without contributing to any trading decision. This is wasted computation.

---

## 2. OHLCV Data Preprocessing

### Data loading

All OHLCV data flows through a single path:

```
SonarftIndicators.get_history()
  → SonarftApiManager.get_ohlcv_history()
    → call_api_method(exchange_id, 'fetch_ohlcv', 'fetch_ohlcv', symbol, timeframe, since=None, limit)
      → ccxt/ccxtpro exchange.fetch_ohlcv()
```

The `since` parameter is always `None` — the bot always requests the most recent `limit` candles. ✅

### Data validation

**Finding I-14 (Medium):** There is **no validation of OHLCV data integrity** after fetching. The code assumes:
- `x[4]` is a valid close price (float > 0)
- `x[2]` is a valid high price
- `x[3]` is a valid low price
- `x[5]` is a valid volume (float ≥ 0)

If an exchange returns malformed OHLCV data (e.g. `None` values, zero prices, negative volumes), the pandas-ta functions will either produce `NaN` (caught by guards) or raise exceptions (caught by `except Exception`). The bot degrades gracefully but does not log the malformed data for investigation.

**Finding I-15 (Low):** OHLCV data is returned as a list of lists `[[timestamp, open, high, low, close, volume], ...]`. The code accesses fields by positional index (`x[4]` for close). If an exchange returns a different field order or extra fields, the indices would be wrong. ccxt standardises OHLCV format across all exchanges, so this is safe in practice. ✅

### Data alignment

All indicators use the same timeframe (`'1m'` by default) except:
- Support/resistance: `'1h'` timeframe, 24 candles
- 24h high/low: `'1m'` timeframe, 1440 candles (dead code)

**Finding I-16 (Medium):** RSI, MACD, StochRSI, and market direction all use `'1m'` candles. Short-term trend also uses `'1m'`. Support/resistance uses `'1h'`. These are fetched independently with no timestamp alignment check. In theory, the 1m candles and 1h candles could be from different time windows if the exchange has data gaps. In practice, ccxt returns the most recent candles for each timeframe, so alignment is approximate but consistent. No synchronisation mechanism exists.

### Missing data handling

**Finding I-17 (Low):** If `get_ohlcv_history()` returns fewer candles than requested (e.g. a new trading pair with limited history), each indicator checks `len(ohlcv) < minimum_required` and raises `ValueError` or returns `None`. The trade is skipped. ✅

The OHLCV cache in `SonarftApiManager` stores the full response. If a subsequent call requests fewer candles than the cached response, it returns a slice: `return cached[1][-limit:]`. ✅

---

## 3. Pandas & Pandas-TA Usage

### DataFrame operations

All indicators convert OHLCV lists to `pd.Series` before passing to pandas-ta:

```python
close_prices = pd.Series([x[4] for x in ohlcv])
rsi = pta.rsi(close_prices, length=moving_average_period)
```

This is the correct approach — pandas-ta expects a `pd.Series` input. ✅

**Finding I-18 (Low):** A new `pd.Series` is created for every indicator call, even when multiple indicators use the same OHLCV data. For example, `get_rsi()` and `get_market_direction()` both create `pd.Series([x[4] for x in ohlcv])` from the same data. The OHLCV data is cached at the API layer, but the `pd.Series` construction is repeated. For 14–45 candles this is negligible overhead.

### Pandas-ta function signatures

| Function | Call | Correct? |
|---|---|---|
| `pta.rsi(close, length=n)` | `pta.rsi(close_prices, length=moving_average_period)` | ✅ |
| `pta.macd(close, fast, slow, signal)` | `pta.macd(close_prices, short_period, long_period, signal_period)` | ✅ positional |
| `pta.stochrsi(close, length, rsi_length, k, d)` | `pta.stochrsi(close_prices, length=stoch_period, rsi_length=rsi_period, k=k_period, d=d_period)` | ✅ keyword |
| `pta.sma(close, length=n)` | `pta.sma(close_prices, length=moving_average_period)` | ✅ |
| `pta.ema(close, length=n)` | `pta.ema(close_prices, length=moving_average_period)` | ✅ |
| `pta.atr(high, low, close, length=n)` | `pta.atr(high, low, close, length=atr_period)` | ✅ (dead code) |

All pandas-ta calls use the correct signatures. ✅

**Finding I-19 (Low):** `pta.macd()` is called with positional arguments `(close_prices, short_period, long_period, signal_period)`. The pandas-ta `macd()` signature is `macd(close, fast=12, slow=26, signal=9, ...)`. Positional argument order matches. ✅ However, using keyword arguments would be more explicit and resilient to future pandas-ta API changes.

### Repeated calculations

**Finding I-20 (Medium):** In `weighted_adjust_prices()`, the following indicators are fetched for both buy and sell exchanges independently:
- RSI × 2 (buy + sell)
- StochRSI × 2
- Market direction × 2
- Short-term trend × 2
- Volatility × 2
- Order book × 2
- Market movement × 2 (unused — see I-13)

Then in `dynamic_volatility_adjustment()` (called twice, once per exchange):
- MACD × 2
- RSI × 2 (again!)

**RSI is fetched up to 4 times per `weighted_adjust_prices()` call** — twice in the main gather and twice in `dynamic_volatility_adjustment()`. The 60s indicator cache means the second pair of RSI calls will be served from cache if they use the same parameters. ✅ Cache key includes `(exchange, base/quote, period, timeframe)` — same parameters → cache hit. ✅

However, `dynamic_volatility_adjustment()` is called with `await asyncio.gather(...)` for both exchanges, and each call independently fetches RSI. The cache prevents redundant API calls but the cache lookup overhead is still incurred 4 times per cycle per symbol.

---

## 4. Indicator-to-Signal Pipeline

```
OHLCV (1m candles, exchange API)
    │
    ├─► get_rsi()           → float 0–100
    │       └─► market_rsi_buy / market_rsi_sell
    │               └─► market_strength = (rsi_buy + rsi_sell) / 2
    │               └─► overbought (≥70) / oversold (≤30) → position direction
    │               └─► dynamic_volatility_adjustment() input
    │
    ├─► get_stoch_rsi()     → (%K, %D) 0–100
    │       └─► market_stoch_rsi_buy_k/d, sell_k/d
    │               └─► %K > %D → momentum confirmation for position direction
    │
    ├─► get_market_direction() → 'bull'/'bear'/'neutral'
    │       └─► market_direction_buy / market_direction_sell
    │               └─► spread factor selection (market_making)
    │               └─► position direction gate (both must match)
    │               └─► dynamic_volatility_adjustment() input
    │
    ├─► get_short_term_market_trend() → 'bull'/'bear'/'neutral'
    │       └─► market_trend_buy / market_trend_sell
    │               └─► dynamic_volatility_adjustment() input
    │
    ├─► get_macd()          → (MACD, signal, histogram)
    │       └─► macd[0] used in dynamic_volatility_adjustment()
    │               └─► vol_adj_buy / vol_adj_sell (0.25–1.75)
    │                       └─► volatility_buy = volatility_raw × vol_adj
    │
    ├─► get_volatility()    → float (order book std dev)
    │       └─► volatility_buy_raw / volatility_sell_raw
    │               └─► weight = max(0, min(1, 1 - volatility × volatility_factor))
    │                       └─► adjusted_price = weight × target + (1-weight) × order_book_price
    │
    ├─► get_order_book()    → order book dict
    │       └─► buy_weighted_price / sell_weighted_price (VWAP depth=3)
    │               └─► price blend input
    │
    ├─► get_support_price() → float or None
    │       └─► adjusted_buy_price = max(adjusted_buy_price, support_price)
    │
    └─► get_resistance_price() → float or None
            └─► adjusted_sell_price = min(adjusted_sell_price, resistance_price)

Adjusted prices → calculate_trade() → profit_percentage
    │
    ├─► profit_percentage >= threshold → proceed
    │
    └─► indicators dict → Trade dataclass → _execute_single_trade()
            └─► market_direction + RSI + StochRSI → LONG or SHORT position
```

### Signal combination logic

The indicators combine in two distinct ways:

**1. Price adjustment** (continuous, affects adjusted prices):
- Volatility + market strength → weight (0–1) for VWAP blend
- Dynamic volatility adjustment → scales raw volatility
- Support/resistance → hard clamps on adjusted prices
- Spread factors (market_making only) → widens bid-ask spread

**2. Position direction** (discrete, gates execution):
- Both exchanges must show same direction (bull+bull or bear+bear)
- RSI + StochRSI crossover → LONG vs SHORT within the direction

**Finding I-21 (Medium):** The position direction gate requires **both** exchanges to show the same market direction. This is a strong filter — in cross-exchange arbitrage, the two exchanges often have slightly different market conditions. Requiring identical direction on both exchanges may cause the bot to skip valid arbitrage opportunities when one exchange is slightly ahead of the other in price discovery. A more nuanced approach would allow a small divergence (e.g. one exchange neutral, one bull → treat as bull).

---

## 5. Off-by-One Errors

### Candle indexing

All indicators use `iloc[-1]` to access the most recent value:

```python
rsi.iloc[-1]          # most recent RSI value
moving_average.iloc[-1]  # most recent MA value
macd[macd_col].iloc[-1]  # most recent MACD value
stoch_rsi.iloc[-1]    # most recent StochRSI row
```

OHLCV data from ccxt is returned in chronological order (oldest first, newest last). `iloc[-1]` correctly accesses the most recent candle. ✅

**Finding I-22 (Low):** `get_short_term_market_trend()` uses list slicing:
```python
current_prices  = [period[4] for period in ohlcv[-N:]]
previous_prices = [period[4] for period in ohlcv[-2*N:-N]]
```
With `N = limit // 2 = 3` and `limit = 6`:
- `ohlcv[-3:]` = candles 3, 4, 5 (most recent 3)
- `ohlcv[-6:-3]` = candles 0, 1, 2 (prior 3)

This is correct — comparing the most recent half against the prior half. ✅

### Lookback window correctness

| Indicator | Requested | Minimum needed | Buffer |
|---|---|---|---|
| RSI (14) | 16 | 15 | +1 ✅ |
| MACD (12/26/9) | 45 | 35 | +10 ✅ |
| StochRSI (14/14/3/3) | 32 | 28 | +4 ✅ |
| Market direction (SMA 14) | 16 | 15 | +1 ✅ |
| Short-term trend | 6 | 6 | 0 ✅ |
| Support/resistance | 24 | 24 | 0 ✅ |
| ATR (14) | 15 | 15 | 0 ✅ (dead code) |

All lookback windows include adequate buffer. ✅

---

## 6. Insufficient Lookback Windows

### First valid output analysis

| Indicator | First valid at candle # | Risk if insufficient data |
|---|---|---|
| RSI | 15 | Returns `None` → trade skipped ✅ |
| MACD | 35 | Returns `None` → trade skipped ✅ |
| StochRSI | 28 | Returns `None` → trade skipped ✅ |
| Market direction | 15 | Returns `None` → trade skipped ✅ |
| Short-term trend | 6 | Returns `None` → trade skipped ✅ |
| Support/resistance | 24 | Returns `None` → price not clamped ✅ |

**Finding I-23 (Low):** When `get_stoch_rsi()` returns `None` and `_indicator_active('stoch rsi')` is `True`, `weighted_adjust_prices()` returns `(0, 0, {})` and the trade is skipped:

```python
if self._indicator_active('stoch rsi') and (stoch_buy is None or stoch_sell is None):
    self.logger.warning(...)
    return 0, 0, {}
```

Similarly for RSI. This means that during the first few minutes of bot operation (before enough candles accumulate), **all trades are skipped**. This is correct and safe behaviour — the bot should not trade before indicators are ready. ✅

**Finding I-24 (Low):** There is no explicit "warm-up period" concept or logging that tells the operator "waiting for indicator data". The bot silently skips trades during warm-up. Adding a startup log message like "Waiting for indicator warm-up (need 45 candles for MACD)" would improve observability.

---

## 7. NaN & Invalid Data Handling

### NaN sources

| Source | When | Propagation path |
|---|---|---|
| pandas-ta RSI | Insufficient data (< period candles) | `rsi.iloc[-1]` → `pd.isna()` guard → `None` |
| pandas-ta MACD | Insufficient data | `macd[col].iloc[-1]` → `pd.isna()` guard → `None` |
| pandas-ta StochRSI | Insufficient data | `last_row.iloc[0/1]` → `pd.isna()` guard → `None` |
| pandas-ta SMA/EMA | Insufficient data | `moving_average.iloc[-1]` → `pd.isna()` guard → `'neutral'` |
| numpy std | Empty array | `np.std([])` → `nan` → `np.isnan()` guard → `0.0` |
| Zero mid-price | Corrupt order book | `mid_price == 0` guard → `0.0` |

### NaN propagation analysis

**Finding I-25 (Low):** In `weighted_adjust_prices()`, RSI defaults are applied when RSI is `None` but `_indicator_active('rsi')` is `False`:

```python
market_rsi_buy  = market_rsi_buy  if market_rsi_buy  is not None else 50.0
market_rsi_sell = market_rsi_sell if market_rsi_sell is not None else 50.0
```

The default of `50.0` (neutral RSI) is a reasonable fallback — it produces `market_strength = 50`, which gives a moderate weight. ✅

Similarly for StochRSI:
```python
market_stoch_rsi_buy_k  = stoch_buy[0]  if stoch_buy  else 50.0
market_stoch_rsi_buy_d  = stoch_buy[1]  if stoch_buy  else 50.0
```

**Finding I-26 (Medium):** The StochRSI default check uses `if stoch_buy` (truthiness) rather than `if stoch_buy is not None`. A tuple `(0.0, 0.0)` is falsy in Python — `bool((0.0, 0.0))` is `False`. If StochRSI returns `(0.0, 0.0)` (both %K and %D at zero, indicating extreme oversold), the code would treat it as `None` and use the `50.0` default instead. This would mask a genuine extreme oversold signal.

**Fix:**
```python
market_stoch_rsi_buy_k = stoch_buy[0] if stoch_buy is not None else 50.0
market_stoch_rsi_buy_d = stoch_buy[1] if stoch_buy is not None else 50.0
```

**Finding I-27 (Low):** `get_market_direction()` returns `None` on exception (not `'neutral'`). The caller in `weighted_adjust_prices()` does not check for `None` direction before using it in `_adjust_market_making()`:

```python
if market_direction_buy in ('bull', 'bear'):
    ...
```

`None in ('bull', 'bear')` is `False` — the spread adjustment is skipped. This is safe but silently degrades the market-making strategy when direction is unavailable. A log warning would improve observability.

---

## 8. Signal Generation Correctness

### RSI signal

| RSI value | Signal | Used for |
|---|---|---|
| ≥ 70 (execution) / ≥ 72 (pricing) | Overbought | SHORT position trigger; spread widening |
| ≤ 30 (execution) / ≤ 28 (pricing) | Oversold | LONG position trigger; spread widening |
| 30–70 | Neutral | Standard spread; direction-based position |

**Finding I-28 (Medium):** As noted in Prompt 03 (T-17), the RSI thresholds are inconsistent between the pricing layer (72/28) and the execution layer (70/30). This creates a 2-point gap where RSI = 71 is "overbought" at execution but not at pricing. The spread is not widened for a signal that triggers a SHORT position.

### StochRSI signal

| Condition | Signal | Used for |
|---|---|---|
| %K > %D | Bullish momentum | Confirms SHORT in overbought market |
| %K < %D | Bearish momentum | Confirms LONG in oversold market |

The StochRSI crossover is used as a **confirmation** signal, not a primary trigger. It refines the RSI-based position direction. ✅

**Finding I-29 (Low):** The StochRSI crossover `%K > %D` is a single-candle comparison. A more robust signal would require the crossover to have occurred within the last N candles (e.g. `%K crossed above %D in the last 3 candles`). A single-candle comparison can produce false signals when %K and %D are very close together (e.g. 50.01 vs 50.00).

### MACD signal

MACD is used only in `dynamic_volatility_adjustment()` — it adjusts the volatility scaling factor but does not directly trigger trades:

| Condition | Adjustment factor |
|---|---|
| bear direction + bull trend + MACD < 0 | 0.75 (reduce volatility weight) |
| bull direction + bear trend + RSI > 70 | 0.5 (reduce volatility weight) |
| bull direction + bull trend + MACD > 0 + RSI < 30 | 0.25 (strongly reduce volatility weight) |
| bear direction + bear trend + MACD < 0 + RSI > 70 | 1.75 (increase volatility weight) |
| All other cases | 1.0 (no adjustment) |

**Finding I-30 (Low):** The `bull+bull+MACD>0+RSI<30` condition (adjustment = 0.25) combines a bullish MACD with an oversold RSI. This is a contradictory signal — MACD > 0 suggests upward momentum while RSI < 30 suggests oversold conditions. The combination is theoretically possible (strong uptrend with a brief pullback) but the 0.25 adjustment factor (strongly reducing volatility weight) seems counterintuitive for this scenario. The logic may be intentional but is undocumented.

### Market direction signal

`get_market_direction()` compares the current close price to the SMA/EMA:
- `current > MA` → `'bull'`
- `current < MA` → `'bear'`
- `current == MA` → `'neutral'` (effectively dead code for floats)

This is a standard trend-following signal. The 14-period SMA on 1m candles represents a 14-minute moving average — a very short-term trend indicator. For cross-exchange arbitrage, this is appropriate. For market-making, a longer period (e.g. 50 or 200) would be more meaningful.

**Finding I-31 (Low):** The market direction is computed on 1m candles with a 14-period SMA. This means the "direction" can flip every few minutes. In a choppy market, the direction may alternate between bull and bear on consecutive cycles, causing the bot to alternate between LONG and SHORT positions. The position direction gate (both exchanges must match) provides some protection, but rapid direction changes could still cause inconsistent behaviour.

---

## 9. Indicator Analysis Table

| Indicator | Function | Lookback | First Valid | NaN Risk | False Positive Risk | Severity |
|---|---|---|---|---|---|---|
| RSI | `get_rsi()` | 16 candles | Candle 15 | Guarded ✅ | Low — standard formula | Low |
| MACD | `get_macd()` | 45 candles | Candle 35 | Guarded ✅ | Low — standard formula | Low |
| StochRSI | `get_stoch_rsi()` | 32 candles | Candle 28 | Guarded ✅ | Medium — single-candle crossover | Medium |
| Market direction (SMA) | `get_market_direction()` | 16 candles | Candle 15 | Guarded ✅ | Medium — 14m SMA flips in choppy market | Medium |
| Short-term trend | `get_short_term_market_trend()` | 6 candles | Candle 6 | Guarded ✅ | Medium — 3-candle average is noisy | Medium |
| Volatility (order book) | `get_volatility()` | Instantaneous | Immediate | Guarded ✅ | Medium — price-scale dependent (M-07) | Medium |
| Support price | `get_support_price()` | 24h candles | Candle 24 | Guarded ✅ | Low — simple min/max | Low |
| Resistance price | `get_resistance_price()` | 24h candles | Candle 24 | Guarded ✅ | Low — simple min/max | Low |
| Market movement | `market_movement()` | Instantaneous | Immediate | None needed | High — sums prices not volumes (T-07) | Medium |
| ATR | `get_atr()` | 15 candles | Candle 15 | Guarded ✅ | N/A — dead code | Low |
| 24h High | `get_24h_high()` | 1440 candles | Candle 1440 | Guarded ✅ | N/A — dead code | Low |
| 24h Low | `get_24h_low()` | 1440 candles | Candle 1440 | Guarded ✅ | N/A — dead code | Low |

---

## 10. Performance Analysis

### API call budget per `weighted_adjust_prices()` invocation

Each call to `weighted_adjust_prices()` triggers the following API calls (before cache):

| Call | Exchange | Timeframe | Candles | Cached? |
|---|---|---|---|---|
| `market_movement()` × 2 | buy + sell | order book | — | 2s TTL |
| `get_market_direction()` × 2 | buy + sell | 1m | 16 | 60s TTL |
| `get_rsi()` × 2 | buy + sell | 1m | 16 | 60s TTL |
| `get_stoch_rsi()` × 2 | buy + sell | 1m | 32 | 60s TTL |
| `get_short_term_market_trend()` × 2 | buy + sell | 1m | 6 | None (OHLCV cached) |
| `get_volatility()` × 2 | buy + sell | order book | — | 2s TTL |
| `get_order_book()` × 2 | buy + sell | order book | — | 2s TTL |
| `get_support_price()` × 1 | buy | 1h | 24 | 3600s TTL |
| `get_resistance_price()` × 1 | sell | 1h | 24 | 3600s TTL |
| `get_macd()` × 2 (in dynamic_vol_adj) | buy + sell | 1m | 45 | 60s TTL |
| `get_rsi()` × 2 (in dynamic_vol_adj) | buy + sell | 1m | 16 | 60s TTL (cache hit) |

**Total: 20 API calls per combination, of which ~16 are served from cache after the first cycle.**

**Finding I-32 (Medium):** On the **first cycle** (cold cache), all 20 calls hit the exchange API. With 2 exchanges and 1 symbol, this is 20 concurrent API calls within a single 30s timeout window. With 3 exchanges and 3 symbols, the number of combinations grows as O(exchanges² × symbols), and each combination triggers its own `weighted_adjust_prices()` call. The 30s timeout is shared across all 16 indicators in a single gather — if the exchange rate-limits any call, the entire gather times out.

**Finding I-33 (Low):** The indicator cache uses a simple dict with monotonic time TTL. The cache is per-`SonarftIndicators` instance (per-bot). With multiple bots trading the same symbol on the same exchange, each bot has its own cache and makes independent API calls. A shared cache across bots would reduce exchange API load.

### Computational cost

pandas-ta operations on 16–45 candles are fast (< 1ms each). The dominant cost is network I/O for OHLCV and order book fetches. The caching strategy correctly addresses this. ✅

**Finding I-34 (Low):** `get_short_term_market_trend()` has no indicator-level cache (only the underlying OHLCV is cached). The computation is trivial (list slicing + average), so adding an indicator cache would save only microseconds. Not worth the complexity.

---

## 11. Integration Testing Recommendations

### Existing test coverage

`tests/test_sonarft_indicators.py` exists. The scope of existing tests should be verified against the findings below.

### Recommended test cases

**RSI:**
- Exactly 14 candles → `None` (insufficient data)
- Exactly 15 candles → valid float
- All same close prices → RSI = 50 (no change)
- Monotonically increasing prices → RSI approaches 100
- Monotonically decreasing prices → RSI approaches 0

**MACD:**
- Fewer than 35 candles → `None`
- Column name validation with current pandas-ta version
- MACD > 0 with RSI < 30 → `dynamic_volatility_adjustment` returns 0.25

**StochRSI:**
- `(0.0, 0.0)` return → should NOT be treated as `None` (fix I-26)
- %K > %D → SHORT confirmation
- %K < %D → LONG confirmation
- Column order validation with `iloc[0]` / `iloc[1]`

**Market direction:**
- `current_price > MA` → `'bull'`
- `current_price < MA` → `'bear'`
- NaN MA → `'neutral'`
- Exception in API call → `None` (not `'neutral'`)

**Volatility:**
- Empty order book → `0.0`
- Single-level order book → `std([0]) = 0.0`
- Normal order book → positive float

**Support/resistance:**
- Fewer than 24 candles → `None`
- All same prices → support == resistance == price

**`weighted_adjust_prices()` integration:**
- StochRSI `(0.0, 0.0)` → should use actual values, not 50.0 default
- All indicators return `None` → returns `(0, 0, {})`
- Timeout → returns `(0, 0, {})`

---

## 12. Conclusion

### Overall indicator reliability: **7/10**

The indicator implementations are technically correct — all use standard pandas-ta formulas with appropriate lookback windows, NaN guards, and caching. The pipeline degrades gracefully when data is unavailable. The primary concerns are signal quality and efficiency rather than correctness.

### Critical issues

**None** — no indicator produces incorrect values under normal operating conditions.

### High priority

**None** — all issues are Medium or Low severity.

### Medium priority findings summary

| ID | Issue | Impact |
|---|---|---|
| I-08 | `get_short_term_market_trend()` has no indicator cache | Repeated computation (minor — OHLCV is cached) |
| I-13 | `market_movement()` called twice but results discarded | Wasted API quota and timeout budget |
| I-14 | No OHLCV data integrity validation | Silent degradation on malformed exchange data |
| I-16 | No timestamp alignment between 1m and 1h indicators | Approximate synchronisation only |
| I-20 | RSI fetched up to 4× per cycle (cache hits after first) | Cache lookup overhead |
| I-21 | Both exchanges must show identical direction | Valid arbitrage opportunities skipped in divergent markets |
| I-26 | StochRSI `(0.0, 0.0)` treated as `None` due to truthiness check | Extreme oversold signal masked |
| I-28 | RSI thresholds inconsistent: 72/28 (pricing) vs 70/30 (execution) | Inconsistent signal interpretation |
| I-32 | Cold cache: 20 API calls per combination in first cycle | Rate limit risk on first cycle |

### Recommendations

1. **Fix I-26 immediately** — `if stoch_buy is not None` instead of `if stoch_buy`. This is a correctness bug that masks extreme market signals.

2. **Remove `market_movement()` from the indicator gather (I-13)** — the results are discarded. This saves 2 API calls per combination and reduces the 30s timeout pressure.

3. **Remove dead code** — `get_atr()`, `get_24h_high()`, `get_24h_low()` are never called. Remove or integrate them.

4. **Unify RSI thresholds (I-28)** — extract `RSI_OVERBOUGHT = 70` and `RSI_OVERSOLD = 30` to `models.py` and use in both `sonarft_prices.py` and `sonarft_execution.py`.

5. **Add OHLCV validation (I-14)** — validate that close prices are positive floats before passing to pandas-ta. Log and skip malformed candles.

6. **Add warm-up period logging (I-24)** — log a clear message when indicators are not yet ready, rather than silently skipping trades.
