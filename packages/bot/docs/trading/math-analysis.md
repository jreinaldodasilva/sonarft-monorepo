# SonarFT Bot — Financial Math & Precision Review

**Prompt:** 04-BOT-MATH  
**Reviewer role:** Expert financial math auditor / quantitative systems reviewer  
**Date:** July 2025  
**Status:** Complete  
**Prerequisites:** [01-BOT-ARCH](../architecture/bot-overview.md), [03-BOT-ENGINE](engine-review.md)

---

## 1. Precision Settings Inventory

### Decimal context setup

| File | `getcontext().prec` | Location |
|---|---|---|
| `sonarft_math.py` | `28` | Module level (top of file) ✅ |
| All other files | Not set | — |

`getcontext().prec = 28` in `sonarft_math.py` sets the precision for the process-wide `Decimal` context. Since Python's `decimal` module uses a thread-local context, this setting applies to all `Decimal` operations in the same thread. For an asyncio single-threaded event loop this is effectively global. ✅

**Finding M-01 (Low):** The guidelines (`memory-bank/guidelines.md`) specify `getcontext().prec = 8` at the top of every file performing financial calculations. The actual code uses `prec = 28` in `sonarft_math.py` only. `prec = 28` is more appropriate for financial calculations (matches IEEE 754 decimal128). The discrepancy between the guideline (8) and the implementation (28) should be resolved in the guidelines — 28 is the correct value.

### Decimal vs float boundary

| Layer | Type used | Justification |
|---|---|---|
| VWAP calculation (`models.py`) | `float` | Price estimation — not settlement |
| Price blending (`sonarft_prices.py`) | `float` | Price estimation — not settlement |
| Indicator calculations (`sonarft_indicators.py`) | `float` (via pandas/numpy) | Statistical analysis — not settlement |
| Spread threshold (`sonarft_validators.py`) | `float` (via numpy) | Statistical threshold — not settlement |
| **Profit/fee calculation (`sonarft_math.py`)** | **`Decimal`** | **Settlement — authoritative** ✅ |
| Order amount/price in `execute_order()` | `float` (passed to ccxt) | ccxt requires float; rounded before passing |

The Decimal boundary is correctly placed at `calculate_trade()`. All upstream calculations use `float` for estimation; only the final profit/fee settlement uses `Decimal`. This is the correct design. ✅

### Float contamination risk

**Finding M-02 (Medium):** `calculate_trade()` converts all inputs via `Decimal(str(value))` — using `str()` conversion avoids the classic `Decimal(float)` contamination problem (e.g. `Decimal(0.1)` → `Decimal('0.1000000000000000055511151231257827021181583404541015625')`). ✅

However, the output of `calculate_trade()` converts back to `float` for storage in `trade_data`:

```python
'profit': float(profit_d),
'profit_percentage': float(profit_pct_d),
```

These `float` values are then used in `execute_trade()` to return `{"profit": trade.get("profit", 0.0)}` for daily loss tracking. The conversion from `Decimal` → `float` at this boundary introduces a small rounding error. For a profit of `Decimal('0.00012345')`, `float(profit_d)` is accurate to ~15 significant digits — negligible for P&L tracking purposes. ✅

### Rounding strategy summary

| Operation | Rounding mode | Location |
|---|---|---|
| Price quantization | `ROUND_HALF_UP` | `d()` in `sonarft_math.py` |
| Fee quantization | `ROUND_HALF_EVEN` (default) or `ROUND_HALF_UP` (env) | `d_fee()` in `sonarft_math.py` |
| Monitored price rounding | Python `round()` (banker's rounding) | `sonarft_execution.py` |
| VWAP | No explicit rounding | `models.py` |
| Indicator values | No explicit rounding (pandas/numpy) | `sonarft_indicators.py` |

**Finding M-03 (Low):** Price quantization uses `ROUND_HALF_UP` while fee quantization uses `ROUND_HALF_EVEN`. This is intentional — `ROUND_HALF_EVEN` eliminates systematic bias in fee calculations over many trades. However, the inconsistency between price rounding (`ROUND_HALF_UP`) and fee rounding (`ROUND_HALF_EVEN`) means the two operations use different rounding semantics. This is documented via the `_FEE_ROUNDING` constant and the env var override. ✅

---

## 2. Financial Calculation Audit

| Calculation | Location | Uses Decimal? | Rounding Strategy | Edge Cases Handled | Risk |
|---|---|---|---|---|---|
| VWAP (order book) | `models.vwap()` | No — `float` | None | Zero volume → 0.0 ✅; empty list → 0.0 ✅; depth > list length ✅ | Low |
| Price blend | `sonarft_prices.weighted_adjust_prices()` | No — `float` | None | NaN volatility → skip ✅; zero weighted price → skip ✅ | Low |
| Support/resistance | `sonarft_indicators.get_support/resistance_price()` | No — `float` | None | Insufficient data → None ✅ | Low |
| Volatility (order book std) | `sonarft_indicators.get_volatility()` | No — `float` (numpy) | None | NaN → 0.0 ✅; None order book → 0.0 ✅ | Low |
| Spread threshold | `sonarft_validators.calculate_thresholds_based_on_historical_data()` | No — `float` (numpy) | None | Empty data → `{low:0, medium:0, high:0}` ✅ | Low |
| **Buy fee** | `sonarft_math.calculate_trade()` | **Yes** | `ROUND_HALF_EVEN` | Zero fee rate → 0 fee ✅ | None |
| **Sell fee** | `sonarft_math.calculate_trade()` | **Yes** | `ROUND_HALF_EVEN` | Zero fee rate → 0 fee ✅ | None |
| **Buy cost** | `sonarft_math.calculate_trade()` | **Yes** | `ROUND_HALF_UP` | Zero buy cost → early return ✅ | None |
| **Sell value** | `sonarft_math.calculate_trade()` | **Yes** | `ROUND_HALF_UP` | — | None |
| **Net profit** | `sonarft_math.calculate_trade()` | **Yes** | `ROUND_HALF_UP` | — | None |
| **Profit %** | `sonarft_math.calculate_trade()` | **Yes** | `ROUND_HALF_UP` | Zero buy cost → guarded ✅ | None |
| Order amount | `sonarft_math.calculate_trade()` | **Yes** | `ROUND_HALF_UP` | — | None |
| Minimum order check | `sonarft_execution.create_order()` | No — `float` | None | None market data → skip check | Medium |
| Slippage tolerance | `sonarft_validators.calculate_slippage_tolerance()` | No — `float` (numpy) | None | Empty history → None ✅ | Low |
| Daily loss accumulation | `sonarft_search.record_trade_result()` | No — `float` | None | Negative profit only | Low |

### Key observation

The Decimal boundary is clean and correctly placed. All settlement-critical calculations (fees, costs, profit) use `Decimal` with explicit quantization. All estimation calculations (VWAP, indicators, thresholds) use `float`. This is the correct architecture. ✅

---

## 3. Precision-Sensitive Functions

### `SonarftMath.calculate_trade()` — `sonarft_math.py`

The most precision-critical function in the codebase.

**Inputs:** `buy_price: float`, `sell_price: float`, `target_amount: float` — all converted via `Decimal(str(x))` immediately.  
**Outputs:** `(float, float, dict)` — converted back from `Decimal` at the end.  
**Rounding:** Explicit `ROUND_HALF_UP` for prices/amounts/costs; `ROUND_HALF_EVEN` for fees.  
**Precision loss:** `Decimal` → `float` conversion at output boundary — negligible (~15 sig figs).

**Finding M-04 (Medium):** The `d()` helper quantizes intermediate results at each step:

```python
buy_price_d          = d(buy_price, buy_rules['prices_precision'])
target_amount_buy_d  = d(target_amount, buy_rules['buy_amount_precision'])
buy_fee_d            = d_fee(buy_price_d * target_amount_buy_d * Decimal(str(buy_fee_rate)), ...)
value_buying_d       = d(buy_price_d * target_amount_buy_d, buy_rules['cost_precision'])
value_buying_with_fee_d = d(value_buying_d + buy_fee_d, buy_rules['cost_precision'])
```

Each intermediate result is quantized before being used in the next step. This is **early rounding** — each quantization step introduces a small error that compounds into the final result. The alternative (late rounding — compute everything at full precision, quantize only the final result) would be more accurate. However, early rounding is required here because the exchange will apply the same rounding to the actual order, so the calculation must match what the exchange will compute. ✅ This is correct for exchange-matching purposes.

### `models.vwap()` — `models.py`

**Inputs:** `list[tuple[float, float]]`, `int`  
**Outputs:** `float`  
**Precision:** Pure `float` arithmetic — no rounding.

**Finding M-05 (Low):** `vwap()` uses a generator expression for both the volume sum and the weighted sum. These are computed in two separate passes over the same slice. For very large order books (depth > 100), this is two O(n) passes. A single-pass accumulation would be more efficient but the current approach is cleaner and the performance difference is negligible for typical depths of 3–12.

### `SonarftPrices.weighted_adjust_prices()` — `sonarft_prices.py`

**Inputs:** All `float`  
**Outputs:** `(float, float, dict)`  
**Precision:** Pure `float` throughout.

**Finding M-06 (Medium):** The weight calculation:

```python
weight = max(0.0, min(1.0, 1 - (volatility * volatility_factor)))
```

Where `volatility_factor = volatility_risk_factor * market_strength` and `market_strength = (rsi_buy + rsi_sell) / 2`.

RSI values range 0–100. `market_strength` ranges 0–100. `volatility_risk_factor` defaults to `0.001`. So `volatility_factor` ranges 0–0.1. With typical order book volatility (e.g. 0.5), `volatility * volatility_factor` = 0.05, giving `weight = 0.95`. The `max(0.0, min(1.0, ...))` clamp prevents weight from going outside [0, 1]. ✅

However, if `market_strength = 0` (both RSI = 0, theoretically impossible but defensively possible), `volatility_factor = 0` and `weight = 1.0` — the adjusted price equals the target VWAP with no order book influence. This is a degenerate but safe case.

### `SonarftIndicators.get_volatility()` — `sonarft_indicators.py`

**Finding M-07 (Low):** Volatility is computed as the standard deviation of price deviations from the mid-price:

```python
mid_price = (max(bid_prices) + min(ask_prices)) / 2
price_changes = [abs(price - mid_price) for price in bid_prices + ask_prices]
volatility = np.std(price_changes)
```

This is not a standard financial volatility measure (which would typically be the standard deviation of returns). It is an order book spread dispersion metric. The result is in price units (e.g. USD), not percentage. When used in `weighted_adjust_prices()` as `volatility_risk_factor * volatility`, the units are mixed — `volatility_risk_factor` is dimensionless (0.001) and `volatility` is in price units. For BTC/USDT at $60,000, a typical order book spread dispersion might be $10–$50, giving `volatility * 0.001 = 0.01–0.05`. This is then multiplied by `market_strength` (0–100), giving `volatility_factor = 0–5`. The `weight = 1 - (volatility * volatility_factor)` could go negative for high-volatility assets, but is clamped to 0. The clamping is correct but the formula is sensitive to asset price scale — a $60,000 BTC will produce very different weights than a $0.001 altcoin.

**Finding M-08 (Medium):** For very low-price assets (e.g. SHIB/USDT at $0.00001), `mid_price` is near zero and `price_changes` will be near-zero values. `np.std()` of near-zero values returns near-zero, giving `volatility ≈ 0` and `weight ≈ 1.0`. The price blend will be dominated by the target VWAP with minimal order book influence. This is not incorrect but may not reflect actual market conditions for micro-cap assets.

---

## 4. Fee Computation Accuracy

### Taker vs maker fee handling

`SonarftApiManager.get_buy_fee()` and `get_sell_fee()` support both maker and taker fees:

```python
if order_type == "limit" and "maker_buy_fee" in exchange_fee:
    return exchange_fee["maker_buy_fee"]
return exchange_fee["buy_fee"]
```

Limit orders use maker fees when available. This is correct — limit orders are typically maker orders (they add liquidity). ✅

**Finding M-09 (Medium):** The `order_type` parameter defaults to `"limit"` in both `get_buy_fee()` and `get_sell_fee()`. `calculate_trade()` calls these without specifying `order_type`, so it always uses maker fees. If an order is executed as a taker (e.g. if the limit price crosses the spread and fills immediately), the actual fee will be the taker fee, which is typically higher. The profit calculation will overestimate profit in this scenario.

For the arbitrage strategy, limit orders placed at the VWAP-adjusted price are likely to be maker orders. However, in fast-moving markets, a limit order may fill as a taker. There is no mechanism to detect or account for this.

### Fee calculation example — Binance BTC/USDT

Assumptions:
- Buy price: $60,000.00 (2 dp precision)
- Sell price: $60,100.00
- Amount: 0.00100 BTC (5 dp precision)
- Buy maker fee: 0.001 (0.1%)
- Sell maker fee: 0.001 (0.1%)

```
buy_price_d          = Decimal('60000.00')
amount_d             = Decimal('0.00100')
buy_fee_d            = ROUND_HALF_EVEN(60000.00 × 0.00100 × 0.001, 8)
                     = ROUND_HALF_EVEN(0.06, 8) = Decimal('0.06000000')
value_buying_d       = ROUND_HALF_UP(60000.00 × 0.00100, 7)
                     = ROUND_HALF_UP(60.0, 7) = Decimal('60.0000000')
value_buying_with_fee= ROUND_HALF_UP(60.0000000 + 0.06000000, 7)
                     = Decimal('60.0600000')

sell_price_d         = Decimal('60100.00')
sell_fee_d           = ROUND_HALF_EVEN(60100.00 × 0.00100 × 0.001, 8)
                     = ROUND_HALF_EVEN(0.0601, 8) = Decimal('0.06010000')
value_selling_d      = ROUND_HALF_UP(60100.00 × 0.00100, 7)
                     = ROUND_HALF_UP(60.1, 7) = Decimal('60.1000000')
value_selling_with_fee = ROUND_HALF_UP(60.1000000 - 0.06010000, 7)
                       = Decimal('60.0399000')

profit_d             = ROUND_HALF_UP(60.0399000 - 60.0600000, 8)
                     = Decimal('-0.02010000')   ← LOSS

profit_pct_d         = ROUND_HALF_UP(-0.02010000 / 60.0600000, 8)
                     = Decimal('-0.00033466')
```

**Result:** A $100 spread on 0.001 BTC produces a **loss** of $0.0201 after fees (−0.033%). This confirms that at 0.1% fees per side, the minimum profitable spread must exceed 0.2% of the buy price. The profit threshold of 0.01% is correctly applied to the net-of-fees result, so this trade would be correctly rejected. ✅

### Fee timing

Fees are computed in `calculate_trade()` **before** the profitability decision. The `profit_percentage >= threshold` check uses the net-of-fees profit. ✅

---

## 5. Profit Calculation Deep Dive

### Formula

```
profit = (sell_price × amount − sell_fee) − (buy_price × amount + buy_fee)

where:
  buy_fee  = buy_price  × amount × buy_fee_rate   [rounded HALF_EVEN]
  sell_fee = sell_price × amount × sell_fee_rate  [rounded HALF_EVEN]

profit_percentage = profit / (buy_price × amount + buy_fee)
```

### Profitable example — OKX ETH/USDT

Assumptions:
- Buy exchange: OKX, buy price: $3,000.0 (1 dp), maker fee: 0.0008 (0.08%)
- Sell exchange: Bitfinex, sell price: $3,010.000 (3 dp), maker fee: 0.001 (0.1%)
- Amount: 1.00000000 ETH

```
buy_price_d   = Decimal('3000.0')
amount_d      = Decimal('1.00000000')
buy_fee_d     = HALF_EVEN(3000.0 × 1.00000000 × 0.0008, 8) = Decimal('2.40000000')
buy_cost_d    = HALF_UP(3000.0 × 1.00000000, 8) = Decimal('3000.00000000')
buy_total_d   = HALF_UP(3000.00000000 + 2.40000000, 8) = Decimal('3002.40000000')

sell_price_d  = Decimal('3010.000')
sell_fee_d    = HALF_EVEN(3010.000 × 1.00000000 × 0.001, 8) = Decimal('3.01000000')
sell_value_d  = HALF_UP(3010.000 × 1.00000000, 8) = Decimal('3010.00000000')
sell_net_d    = HALF_UP(3010.00000000 - 3.01000000, 8) = Decimal('3006.99000000')

profit_d      = HALF_UP(3006.99000000 - 3002.40000000, 8) = Decimal('4.59000000')
profit_pct_d  = HALF_UP(4.59000000 / 3002.40000000, 8) = Decimal('0.00152878')
```

**Result:** $4.59 profit, 0.153% return. Above the 0.01% threshold → trade proceeds. ✅

### Edge cases

**Very small amount (0.00001 ETH at $3,000):**
```
buy_cost = 3000.0 × 0.00001 = 0.03
buy_fee  = 0.03 × 0.0008 = 0.000024 → rounds to 0.00002400
```
At this scale, fee precision (8 dp) is adequate. The minimum order check in `create_order()` would likely reject this before it reaches execution. ✅

**Very tight spread (0.001% = $0.003 on $3,000):**
```
sell_price = 3000.003
profit before fees ≈ 0.003
buy_fee + sell_fee ≈ 3000 × 0.0008 + 3000 × 0.001 = 2.4 + 3.0 = 5.4
net profit = 0.003 - 5.4 = -5.397  ← correctly rejected
```
✅

**High fees (0.5% per side):**
```
buy_fee + sell_fee ≈ 3000 × 0.005 + 3000 × 0.005 = 30
Required spread for 0.01% profit: 3000 × 0.0001 + 30 = 30.3
Required spread percentage: 30.3 / 3000 = 1.01%
```
The bot correctly requires a 1.01% spread to be profitable at 0.5% fees. ✅

### Finding M-10 (Medium) — profit_percentage precision

`profit_pct_d` is quantized to `sell_rules['fee_precision']` (8 dp). The threshold comparison:

```python
if profit_percentage >= percentage_threshold:
```

uses `float(profit_pct_d)` compared to `float(percentage_threshold)` (loaded from JSON as a Python float). Both are `float` at comparison time. For a threshold of `0.0001`, the float representation is exact (`0.0001` is representable in IEEE 754 to ~15 sig figs). The comparison is safe. ✅

**Finding M-11 (Low):** `profit_percentage` is stored in `trade_data` as `float(profit_pct_d)`. The `Decimal` precision (8 dp) is preserved through the `float` conversion for values in the range 0.00000001 to 0.99999999. For very small profits (e.g. `0.00000001` = 0.000001%), the `float` representation is accurate. ✅

---

## 6. Order Book & Aggregation Math

### VWAP aggregation

`models.vwap()` computes volume-weighted average price — not a simple average. This is the correct formula for order book price estimation. ✅

`SonarftPrices.get_weighted_price()` delegates to `vwap()` with `depth=3` for the order book blend in `weighted_adjust_prices()`. Using only the top 3 levels for the blend weight is intentional — it reflects the most liquid part of the order book.

`SonarftApiManager.get_latest_prices()` uses `weight=12` (passed from `process_symbol()`). This is the depth for the initial price discovery VWAP.

**Finding M-12 (Low):** Two different depth values are used for VWAP in the same pipeline: `12` for initial price discovery and `3` for the order book blend in price adjustment. The inconsistency is intentional (different purposes) but undocumented. A comment explaining the rationale for each depth value would improve maintainability.

### Spread threshold aggregation

`get_trade_dynamic_spread_threshold_avg()` computes a volume-weighted average spread:

```python
trade_spread_sum = sum(
    (ask_price - bid_price) * min(ask_volume, bid_volume)
    for (bid_price, bid_volume) in buy_order_book['bids'][:10]
    for (ask_price, ask_volume) in sell_order_book['asks'][:10]
)
trade_volume_sum = sum(
    min(ask_volume, bid_volume)
    for (_, bid_volume) in buy_order_book['bids'][:10]
    for (_, ask_volume) in sell_order_book['asks'][:10]
)
trade_spread_avg = trade_spread_sum / trade_volume_sum
```

**Finding M-13 (Medium):** This is an O(n²) cross-product over 10×10 = 100 pairs. The spread is computed as `ask_price - bid_price` for every combination of bid level from exchange A and ask level from exchange B. This is a cross-exchange spread, not a single-exchange bid-ask spread. The volume weighting uses `min(ask_volume, bid_volume)` — the minimum of the two sides, representing the tradeable volume at that price combination. This is a reasonable approximation for cross-exchange arbitrage spread estimation.

However, the O(n²) computation is unnecessary. The comment in the code notes that the price average was already optimised to O(n), but the spread sum was not. For 10 levels this is 100 iterations — negligible in practice but inconsistent with the stated optimisation goal.

### Historical spread calculation

`calculate_thresholds_based_on_historical_data()` computes spread from OHLCV close prices:

```python
spread_pct = (sell_close - buy_close) / mid * 100
```

Where `mid = (buy_close + sell_close) / 2`.

**Finding M-14 (Low):** Using `mid = (buy_close + sell_close) / 2` as the denominator is the correct formula for percentage spread (avoids the asymmetry of using either price alone as the base). ✅

---

## 7. Rounding Edge Cases

### Early vs late rounding

As noted in Section 3, `calculate_trade()` applies early rounding — each intermediate result is quantized before use in the next step. This matches exchange behaviour (exchanges round each field independently) but introduces compounding rounding errors.

**Concrete example of compounding rounding:**

```
buy_price = 60000.005  →  rounds to 60000.01 (ROUND_HALF_UP, 2 dp)
amount    = 0.000015   →  rounds to 0.00002  (ROUND_HALF_UP, 5 dp)

buy_cost (rounded) = 60000.01 × 0.00002 = 1.2000002 → rounds to 1.2000002 (7 dp)
buy_cost (exact)   = 60000.005 × 0.000015 = 0.900000075

Difference: 1.2000002 - 0.900000075 = 0.300000125
```

This is an extreme example (price at a rounding boundary, very small amount). In practice, the rounding error is proportional to the last digit of precision and is bounded by `0.5 × 10^(-precision)` per step. For typical trades, the compounding error is well below the profit threshold. ✅

### Rounding direction bias

`ROUND_HALF_UP` for prices and amounts means that `.5` cases always round up. Over many trades, this introduces a small systematic upward bias in buy prices and amounts. The effect is:
- Buy cost slightly overestimated → profit slightly underestimated → conservative (safe)
- Sell value slightly overestimated → profit slightly overestimated → aggressive (minor risk)

The net effect depends on which rounding boundary is hit more often. For random price inputs, the bias is negligible. ✅

### Profit threshold comparison precision

**Finding M-15 (Low):** The profit threshold `0.0001` is loaded from JSON as a Python `float`. JSON numbers are parsed as IEEE 754 doubles. `0.0001` in IEEE 754 is `0.000100000000000000004792173602385929598312941...` — slightly above the mathematical value. This means the threshold is very slightly stricter than intended. The effect is negligible (< 1 ULP difference). ✅

---

## 8. Exchange-Specific Precision Rules

### Hardcoded rules in `EXCHANGE_RULES`

| Exchange | Price precision | Amount precision | Cost precision | Fee precision |
|---|---|---|---|---|
| OKX | 1 dp | 8 dp | 8 dp | 8 dp |
| Bitfinex | 3 dp | 8 dp | 8 dp | 8 dp |
| Binance | 2 dp | 5 dp | 7 dp | 8 dp |

**Finding M-16 (High):** These hardcoded precision values are **exchange-wide defaults**, not symbol-specific. In reality, precision varies by trading pair:
- Binance BTC/USDT: price precision = 2 dp ✅
- Binance ETH/BTC: price precision = 6 dp ❌ (hardcoded as 2)
- Binance SHIB/USDT: price precision = 8 dp ❌ (hardcoded as 2)

Using the wrong price precision causes `calculate_trade()` to round prices to the wrong number of decimal places. For high-precision pairs (e.g. SHIB/USDT), rounding to 2 dp would produce a price of `$0.00` — the trade would be rejected by the exchange.

The code does try `get_symbol_precision()` first (which reads from loaded market data), falling back to `EXCHANGE_RULES` only if market data is unavailable. If `load_all_markets()` succeeds at startup, the live precision is used. ✅ The hardcoded rules are only a risk if market data fails to load.

**Finding M-17 (Medium):** `get_symbol_precision()` converts tick-size precision (e.g. `0.01` → 2 dp) using a string-based decimal place counter:

```python
def _to_dp(v):
    if isinstance(v, int): return v
    s = f"{v:.10f}".rstrip("0")
    return len(s.split(".")[-1]) if "." in s else 0
```

For `v = 1e-8` (common for crypto), `f"{1e-8:.10f}"` = `"0.0000000100"` → rstrip("0") = `"0.00000001"` → 8 dp. ✅  
For `v = 0.5`, `f"{0.5:.10f}"` = `"0.5000000000"` → rstrip("0") = `"0.5"` → 1 dp. ✅  
For `v = 1` (integer tick size), returns `0` dp. ✅

The conversion is correct for all common cases. ✅

### Minimum order enforcement

`create_order()` checks `min_amount` and `min_cost` from loaded market data. If market data is not loaded (e.g. `load_markets()` failed), `self.api_manager.markets` is empty and the minimum check is skipped entirely:

```python
market = (self.api_manager.markets or {}).get(exchange_id, {}).get(symbol, {})
if isinstance(market, dict):
    limits = market.get("limits") or {}
    ...
```

**Finding M-18 (Medium):** If `load_markets()` fails at startup (network error, exchange down), `markets` is empty. The minimum order check is silently skipped. The bot may then attempt to place orders below the exchange minimum, which will be rejected by the exchange with an error. This is handled gracefully (order returns `None`, trade is skipped), but the root cause (failed market load) is not surfaced as a critical startup error.

---

## 9. Numerical Stability Issues

### Zero-division risks

| Location | Expression | Guard | Risk |
|---|---|---|---|
| `models.vwap()` | `/ total_volume` | `if total_volume == 0: return 0.0` ✅ | None |
| `sonarft_math.calculate_trade()` | `/ value_buying_with_fee_d` | `if value_buying_with_fee_d == 0: return 0, 0, None` ✅ | None |
| `sonarft_indicators.get_short_term_market_trend()` | `/ previous_avg_price` | `if previous_avg_price == 0: return 'neutral'` ✅ | None |
| `sonarft_indicators.get_price_change()` | `/ previous_avg_price` | `if previous_avg_price != 0 else 0` ✅ | None |
| `sonarft_indicators.market_movement()` | `/ previous` | `if previous != 0 else 0` ✅ | None |
| `sonarft_validators.verify_spread_threshold()` | `/ average_price` | `if average_price == 0: return False` ✅ | None |
| `sonarft_validators.get_trade_dynamic_spread_threshold_avg()` | `/ trade_volume_sum` | `if trade_volume_sum == 0: return 0,0,0,0,None` ✅ | None |
| `sonarft_validators.get_trade_dynamic_spread_threshold_avg()` | `/ trade_price_avg` | `if trade_price_avg == 0: return 0,0,0,0,None` ✅ | None |
| `sonarft_validators.check_exchange_slippage()` | `/ trade_price` | `if trade_price != 0 else 0` ✅ | None |
| `sonarft_indicators.get_liquidity()` | `/ mid_price` | `if mid_price == 0: return 0.0` ✅ | None |
| `sonarft_prices.weighted_adjust_prices()` | `/ 2` (market_strength) | No guard — but RSI is always 0–100, sum always ≥ 0 | None |

Zero-division is comprehensively guarded throughout the codebase. ✅

**Finding M-19 (Low):** `sonarft_validators.calculate_thresholds_based_on_historical_data()` computes:

```python
spread_pct = (sell_close - buy_close) / mid * 100
```

Where `mid = (buy_close + sell_close) / 2`. If both `buy_close` and `sell_close` are `0.0` (theoretically impossible for a traded asset but possible with corrupt data), `mid = 0` and this raises `ZeroDivisionError`. The outer `if not historical_spread_percentage` guard catches the case where the list is empty, but not the case where individual `mid` values are zero.

**Fix:**
```python
if mid == 0:
    continue
spread_pct = (sell_close - buy_close) / mid * 100
```

### NaN/Inf risks

**Finding M-20 (Medium):** `sonarft_prices.weighted_adjust_prices()` checks:

```python
if math.isnan(volatility_buy) or math.isnan(volatility_sell):
    self.logger.warning(...)
    return 0, 0, {}
```

This guards against NaN volatility. However, `volatility_buy = volatility_buy_raw * vol_adj_buy`. If `vol_adj_buy` is `Inf` (theoretically possible if `dynamic_volatility_adjustment()` returns a very large value), `volatility_buy` would be `Inf`, not `NaN`. `math.isnan(Inf)` returns `False`, so the guard would not catch this. The subsequent `weight = max(0.0, min(1.0, 1 - (volatility * volatility_factor)))` would clamp `weight` to `0.0` if `volatility` is `Inf`. The clamping provides a safety net, but the `Inf` case is not explicitly logged.

In practice, `dynamic_volatility_adjustment()` returns values from `{0.25, 0.5, 0.75, 1.0, 1.75}` — all finite. The `Inf` risk is theoretical. ✅

**Finding M-21 (Low):** `np.std([])` returns `nan` for an empty array. `sonarft_indicators.get_volatility()` computes `np.std(price_changes)` where `price_changes` is built from `bid_prices + ask_prices`. If the order book has no bids or asks, `price_changes` is empty and `np.std([])` returns `nan`. The guard `if np.isnan(volatility): return 0.0` catches this. ✅

**Finding M-22 (Low):** `sonarft_validators.calculate_slippage_tolerance()` computes:

```python
price_changes_std = np.std(price_changes)
risk_factor = base_risk_factor * (1 + price_changes_std)
```

If `price_changes` is empty (no valid trades in history), `np.std([])` = `nan`, and `risk_factor = base_risk_factor * (1 + nan) = nan`. The subsequent `slippage_tolerance = median_slippage + (risk_factor * iqr_slippage)` would be `nan`. However, the `if len(slippage_list) == 0: return None` guard runs before this computation, so `price_changes` is only computed when `slippage_list` is non-empty. If `slippage_list` is non-empty but `price_changes` is empty (possible if all `buy_price` or `sell_price` values are 0), the NaN would propagate. This is an edge case with corrupt trade history data.

### Overflow risks

No overflow risks identified. Python integers are arbitrary precision. `Decimal` with `prec=28` handles values up to `10^28`. The largest realistic trade value (e.g. 1000 BTC at $100,000 = $100,000,000) is well within `float64` range (~1.8 × 10^308). ✅

### Underflow risks

**Finding M-23 (Low):** For very small amounts (e.g. `0.00000001` BTC = 1 satoshi), `buy_price × amount` at $60,000 = `0.0006`. After rounding to 7 dp (Binance cost precision), this is `0.0006000`. The fee at 0.1% = `0.0000006` → rounds to `0.00000060` (8 dp). These values are representable in both `Decimal` (28 dp) and `float64`. No underflow risk at realistic trade sizes. ✅

---

## 10. Precision Audit Table

| ID | Function | Issue | Severity | Example | Fix |
|---|---|---|---|---|---|
| M-16 | `SonarftMath.EXCHANGE_RULES` | Hardcoded precision is exchange-wide, not symbol-specific — wrong for non-standard pairs | **High** | SHIB/USDT on Binance: price rounds to `$0.00` instead of `$0.00001234` | Always use `get_symbol_precision()` first; fail loudly if unavailable rather than falling back to wrong defaults |
| M-09 | `SonarftApiManager.get_buy/sell_fee()` | Always uses maker fee; taker fee not accounted for when limit order fills as taker | **Medium** | Fast market: limit order crosses spread → taker fee applied → profit overestimated | Add taker fee to `config_fees.json`; use taker fee when `order_type == "taker"` |
| M-08 | `SonarftIndicators.get_volatility()` | Volatility metric is price-scale-dependent — produces different weight values for different asset price ranges | **Medium** | SHIB at $0.00001 → near-zero volatility → weight ≈ 1.0 regardless of actual market conditions | Normalise volatility as percentage of mid-price: `volatility / mid_price` |
| M-18 | `SonarftExecution.create_order()` | Minimum order check silently skipped if `load_markets()` failed | **Medium** | Market load fails → no minimum check → exchange rejects order | Treat failed market load as a startup error; block trading until markets are loaded |
| M-17 | `SonarftApiManager.get_symbol_precision()` | `_to_dp()` tick-size conversion — correct for common cases but untested for exotic formats | **Medium** | Exchange returns precision as string `"0.001"` → handled; as `None` → returns 8 (default) | Add unit tests for `_to_dp()` with all ccxt precision formats |
| M-13 | `SonarftValidators.get_trade_dynamic_spread_threshold_avg()` | O(n²) cross-product spread sum over 10×10 order book levels | **Medium** | 100 iterations per validation call | Optimise to O(n) using pre-computed per-side averages |
| M-04 | `SonarftMath.calculate_trade()` | Early rounding at each step — compounding rounding error | **Low** | Extreme boundary case: error up to ~$0.30 on $60,000 trade | Acceptable — matches exchange behaviour; document explicitly |
| M-06 | `SonarftPrices.weighted_adjust_prices()` | Weight formula uses raw RSI (0–100) as market_strength — large scale factor | **Low** | RSI=100 → market_strength=100 → volatility_factor=0.1 → weight may clamp to 0 | Normalise RSI to 0–1 range before use in weight formula |
| M-19 | `SonarftValidators.calculate_thresholds_based_on_historical_data()` | No zero-division guard for `mid = 0` in spread_pct calculation | **Low** | Corrupt OHLCV data with zero close prices → `ZeroDivisionError` | Add `if mid == 0: continue` guard |
| M-20 | `SonarftPrices.weighted_adjust_prices()` | `math.isnan()` guard does not catch `Inf` volatility | **Low** | Theoretical only — `dynamic_volatility_adjustment()` returns finite values | Add `math.isinf()` check alongside `math.isnan()` |
| M-07 | `SonarftIndicators.get_volatility()` | Volatility in price units, not percentage — mixed units in weight formula | **Low** | BTC at $60,000 → volatility ~$10–50; USDT stablecoin → volatility ~$0.0001 | Normalise: `volatility = np.std(price_changes) / mid_price` |
| M-03 | `SonarftMath.calculate_trade()` | Price uses `ROUND_HALF_UP`, fee uses `ROUND_HALF_EVEN` — different rounding semantics | **Low** | Documented and intentional | Add comment explaining the rationale |
| M-01 | `memory-bank/guidelines.md` | Guidelines specify `prec=8`; implementation uses `prec=28` | **Low** | Guidelines are wrong | Update guidelines to specify `prec=28` |
| M-12 | `TradeProcessor.process_symbol()` | VWAP depth hardcoded at 12 for price discovery, 3 for blend — undocumented | **Low** | — | Add inline comments explaining depth choices |
| M-22 | `SonarftValidators.calculate_slippage_tolerance()` | NaN propagation if `price_changes` empty with non-empty `slippage_list` | **Low** | Corrupt trade history with all-zero prices | Add `if not price_changes: return None` guard |

---

## 11. Conclusion & Remediation

### Overall precision safety: **8/10**

The financial calculation architecture is well-designed. The Decimal boundary is correctly placed at `calculate_trade()`, all inputs are converted via `str()` to avoid float contamination, fee rounding uses banker's rounding to eliminate systematic bias, and zero-division is comprehensively guarded throughout.

### Critical fixes

**None** — no calculation produces incorrect results under normal operating conditions.

### High priority

**M-16 — Symbol-specific precision:** The hardcoded `EXCHANGE_RULES` fallback uses exchange-wide precision that is wrong for non-standard trading pairs. While `get_symbol_precision()` is tried first, a failed market load silently falls back to wrong precision. This should be a hard failure, not a silent fallback.

### Medium priority

| Fix | Impact |
|---|---|
| Normalise volatility to percentage of mid-price (M-07, M-08) | Consistent weight calculation across all asset price ranges |
| Add taker fee support (M-09) | Accurate profit estimation when limit orders fill as taker |
| Treat failed market load as blocking error (M-18) | Prevents order rejection due to missing minimum checks |
| Optimise O(n²) spread sum to O(n) (M-13) | Minor performance improvement |

### Systematic improvement recommendations

1. **Add a `PrecisionValidator` startup check** — verify that all configured exchanges have symbol-specific precision loaded from market data before allowing trading to start.

2. **Normalise the volatility metric** — divide order book spread dispersion by mid-price to make the weight formula scale-independent across all asset price ranges.

3. **Add taker fee fields to `config_fees.json`** — and use them when order monitoring detects immediate fills (indicating taker execution).

4. **Add unit tests for `calculate_trade()`** — covering: zero fees, equal prices, partial fill amounts, all three exchanges, and boundary precision values. The existing test suite covers this module but additional edge case coverage would increase confidence.
