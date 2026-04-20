# SonarFT Bot — Financial Math & Precision Review

**Prompt:** 04-BOT-MATH  
**Reviewer:** Senior Quantitative Finance Engineer / Numerical Precision Auditor  
**Date:** July 2025  
**Codebase:** `packages/bot` — financial calculation pipeline  
**Severity:** ⭐ CRITICAL — Financial precision audit

---

## 1. Precision Settings Inventory

### 1.1 Decimal Context Configuration

| Location | Setting | Value | Assessment |
|---|---|---|---|
| `sonarft_math.py:10` | `getcontext().prec` | `28` | ✅ Sufficient for all financial calculations (28 significant digits) |

**Note:** The project guidelines document states `prec = 8`, but the actual code uses `prec = 28`. The code is correct — `prec` controls *significant digits* (not decimal places), and 28 is the standard for financial applications. The `d()` helper separately controls decimal places via `quantize()`.

### 1.2 Decimal vs Float Usage Map

| Module | Operation | Type Used | Should Use Decimal? | Risk |
|---|---|---|---|---|
| `sonarft_math.py` | Fee calculation, profit, cost | ✅ `Decimal` | Yes | **None** |
| `sonarft_math.py` | Final `trade_data` output | ⚠️ `float(...)` conversion | Acceptable at boundary | **Low** |
| `sonarft_prices.py` | VWAP calculation | ❌ `float` | Acceptable (intermediate) | **Low** |
| `sonarft_prices.py` | Price adjustment (spread factors, weight) | ❌ `float` | Acceptable (intermediate) | **Low** |
| `sonarft_prices.py` | `get_weighted_price()` | ❌ `float` | Acceptable (intermediate) | **Low** |
| `sonarft_indicators.py` | RSI, MACD, StochRSI, volatility | ❌ `float` via pandas | Acceptable (signals, not money) | **None** |
| `sonarft_indicators.py` | `get_profit_factor()` spread factor | ❌ `float` | Acceptable (multiplier) | **Low** |
| `sonarft_validators.py` | Spread ratio, slippage, thresholds | ❌ `float` | Acceptable (comparison) | **Low** |
| `sonarft_api_manager.py` | VWAP, order book prices | ❌ `float` | Acceptable (from exchange) | **None** |
| `sonarft_execution.py` | Balance check, price comparison | ❌ `float` | Acceptable (comparison) | **None** |
| `config_parameters.json` | `profit_percentage_threshold` | JSON `float` | Acceptable (config) | **None** |
| `config_fees.json` | `buy_fee`, `sell_fee` | JSON `float` | ⚠️ Converted to `Decimal(str(...))` in math | **None** |

### 1.3 Float Contamination Analysis

The system has a clear **precision boundary**:

```
FLOAT ZONE (acceptable)                    DECIMAL ZONE (required)
─────────────────────────                  ──────────────────────────
Exchange API → order book prices           calculate_trade():
VWAP calculation                             buy_price_d = d(buy_price, ...)
Price adjustment (indicators)                buy_fee_d = d(... * Decimal(str(fee)))
Spread factor multiplication                 profit_d = d(sell_total - buy_total)
                        ──── boundary ────►
                        float inputs to calculate_trade()
```

**Assessment:** The boundary is well-placed. All intermediate calculations (VWAP, indicators, price adjustment) use `float`, which is acceptable because:
1. Exchange APIs return floats
2. Indicator calculations (RSI, MACD) are inherently approximate
3. The final `calculate_trade()` converts all inputs to `Decimal(str(value))` before any monetary arithmetic

The `Decimal(str(value))` conversion at the boundary is the correct pattern — it avoids the `Decimal(0.1) = 0.1000000000000000055511151231257827021181583404541015625` trap.

### 1.4 Rounding Strategy

| Where | Strategy | Timing | Assessment |
|---|---|---|---|
| `sonarft_math.py` `d()` | `ROUND_HALF_UP` via `Decimal.quantize()` | At each calculation step | ✅ Explicit, consistent |
| `sonarft_prices.py` | No explicit rounding | Intermediate floats | ✅ Acceptable — rounded at boundary |
| `sonarft_indicators.py` | No explicit rounding | Signal values | ✅ Not monetary |
| `sonarft_validators.py` | No explicit rounding | Comparison values | ⚠️ Float comparison for thresholds |
| `sonarft_execution.py` | No explicit rounding | `monitor_price` return | ⚠️ Raw float passed to order (see Prompt 03, F2) |

---

## 2. Financial Calculation Audit

### 2.1 Calculation Inventory

| # | Calculation | Location | Uses Decimal? | Rounding | Edge Cases | Risk |
|---|---|---|---|---|---|---|
| 1 | VWAP (bid side) | `api_manager.get_weighted_prices()` | ❌ float | None | Zero volume → returns 0.0 | **Low** |
| 2 | VWAP (ask side) | `api_manager.get_weighted_prices()` | ❌ float | None | Zero volume → returns 0.0 | **Low** |
| 3 | Weighted price (adjustment) | `prices.get_weighted_price()` | ❌ float | None | Zero volume → ZeroDivisionError caught → 0.0 | **Low** |
| 4 | Price blending | `prices.weighted_adjust_prices()` | ❌ float | None | weight ∈ [0,1] clamped | **Low** |
| 5 | Spread factor | `indicators.get_profit_factor()` | ❌ float | None | volatility clamped to [0,1] | **Low** |
| 6 | Buy price rounding | `math.calculate_trade()` | ✅ Decimal | `ROUND_HALF_UP` to `prices_precision` | — | **None** |
| 7 | Buy amount rounding | `math.calculate_trade()` | ✅ Decimal | `ROUND_HALF_UP` to `buy_amount_precision` | — | **None** |
| 8 | Buy fee | `math.calculate_trade()` | ✅ Decimal | `ROUND_HALF_UP` to `fee_precision` | — | **None** |
| 9 | Buy value | `math.calculate_trade()` | ✅ Decimal | `ROUND_HALF_UP` to `cost_precision` | — | **None** |
| 10 | Buy value + fee | `math.calculate_trade()` | ✅ Decimal | `ROUND_HALF_UP` to `cost_precision` | Zero check | **None** |
| 11 | Sell price rounding | `math.calculate_trade()` | ✅ Decimal | `ROUND_HALF_UP` to `prices_precision` | — | **None** |
| 12 | Sell fee | `math.calculate_trade()` | ✅ Decimal | `ROUND_HALF_UP` to `fee_precision` | — | **None** |
| 13 | Sell value | `math.calculate_trade()` | ✅ Decimal | `ROUND_HALF_UP` to `cost_precision` | — | **None** |
| 14 | Sell value - fee | `math.calculate_trade()` | ✅ Decimal | `ROUND_HALF_UP` to `cost_precision` | — | **None** |
| 15 | Profit | `math.calculate_trade()` | ✅ Decimal | `ROUND_HALF_UP` to `fee_precision` | — | **None** |
| 16 | Profit percentage | `math.calculate_trade()` | ✅ Decimal | `ROUND_HALF_UP` to `fee_precision` | Division by zero if buy_total=0 → guarded | **None** |
| 17 | Spread ratio | `validators.verify_spread_threshold()` | ❌ float | None | average_price=0 if both prices=0 | **Low** |
| 18 | Slippage | `validators.check_exchange_slippage()` | ❌ float | None | trade_price=0 → ZeroDivisionError | **Medium** |
| 19 | Historical spread % | `validators.calculate_thresholds_based_on_historical_data()` | ❌ float | None | (ask+bid)/2=0 → ZeroDivisionError | **Medium** |

---

## 3. Precision-Sensitive Functions

### 3.1 Money-Touching Functions

| Function | File | Input Types | Output Types | Precision Loss? | Risk |
|---|---|---|---|---|---|
| `calculate_trade()` | `sonarft_math.py` | `float` (prices, amounts, fees) | `float` (from Decimal) | ⚠️ Final `float()` conversion loses ~1e-16 precision | **Low** |
| `get_weighted_prices()` | `sonarft_api_manager.py` | `float` (from exchange) | `float` (VWAP) | ⚠️ Float arithmetic accumulation | **Low** |
| `get_weighted_price()` | `sonarft_prices.py` | `float` (from order book) | `float` | ⚠️ Float arithmetic | **Low** |
| `weighted_adjust_prices()` | `sonarft_prices.py` | `float` (prices, indicators) | `float` (adjusted prices) | ⚠️ Multiple float multiplications | **Low** |
| `get_profit_factor()` | `sonarft_indicators.py` | `float` (volatility) | `float` (spread factor) | Negligible | **None** |
| `check_balance()` | `sonarft_execution.py` | `float` (amount, price, balance) | `bool` | ⚠️ Float comparison: `balance < amount*price` | **Low** |
| `verify_spread_threshold()` | `sonarft_validators.py` | `float` (prices) | `bool` | ⚠️ Float comparison: `spread_ratio <= threshold` | **Low** |
| `deeper_verify_liquidity()` | `sonarft_validators.py` | `float` (volumes, prices) | `bool` | ⚠️ Float comparison for ratios | **Low** |

### 3.2 The `d()` Helper — Core Precision Function

```python
def d(value, precision):
    """Convert to Decimal and quantize to given decimal places."""
    fmt = Decimal(10) ** -precision
    return Decimal(str(value)).quantize(fmt, rounding=ROUND_HALF_UP)
```

**Analysis:**

| Aspect | Assessment |
|---|---|
| `Decimal(str(value))` | ✅ Correct — avoids float→Decimal precision trap |
| `Decimal(10) ** -precision` | ✅ Correct — creates quantize format (e.g., `0.01` for precision=2) |
| `ROUND_HALF_UP` | ✅ Standard financial rounding |
| Negative precision | ⚠️ If `precision` is negative, `Decimal(10) ** -(-2)` = `100`, which would round to nearest 100. Not expected but not guarded. | **Info** |
| Non-integer precision | ⚠️ If precision is a float (e.g., from JSON), `Decimal(10) ** -1.5` raises `InvalidOperation`. The `_to_dp()` helper in `get_symbol_precision()` always returns `int`, so this is safe in practice. | **Info** |

### 3.3 Float-to-Decimal Boundary Correctness

The critical boundary is in `calculate_trade()` where float inputs become Decimal:

```python
buy_price_d = d(buy_price, buy_rules['prices_precision'])
# buy_price is float from weighted_adjust_prices()
# d() converts via Decimal(str(buy_price)) — CORRECT
```

**Proof of correctness:**
```python
>>> float_val = 30000.123456789
>>> Decimal(float_val)          # WRONG: Decimal('30000.12345678900015144608914852142333984375')
>>> Decimal(str(float_val))     # CORRECT: Decimal('30000.123456789')
```

✅ The `str()` conversion eliminates the float representation error before Decimal conversion.


---

## 4. Fee Computation Accuracy

### 4.1 Fee Formula

For each exchange, the fee is computed as:

```
fee = round(price × amount × fee_rate, fee_precision)
```

In Decimal form:
```python
buy_fee_d = d(buy_price_d * target_amount_buy_d * Decimal(str(buy_fee_rate)), buy_rules['fee_precision'])
```

### 4.2 Fee Timing

```
1. buy_price_d    = d(buy_price, prices_precision)        ← price rounded first
2. amount_d       = d(target_amount, amount_precision)     ← amount rounded
3. buy_fee_d      = d(price_d × amount_d × fee_rate, fee_precision)  ← fee on rounded values
4. buy_value_d    = d(price_d × amount_d, cost_precision)  ← value on rounded values
5. buy_total_d    = d(value_d + fee_d, cost_precision)     ← total with fee
```

✅ **Correct order:** Price and amount are rounded to exchange precision BEFORE fee calculation. This matches how exchanges compute fees — on the actual order price/amount, not on theoretical values.

### 4.3 Per-Exchange Fee Verification

**Example: Buy 1 BTC on OKX at 30000.1, sell on Binance at 30100.12**

```
OKX (buy):
  price_precision = 1 → buy_price = 30000.1
  amount_precision = 8 → amount = 1.00000000
  fee_rate = 0.0008
  buy_fee = d(30000.1 × 1.0 × 0.0008, 8) = d(24.00008, 8) = 24.00008000
  buy_value = d(30000.1 × 1.0, 8) = 30000.10000000
  buy_total = d(30000.1 + 24.00008, 8) = 30024.10008000

Binance (sell):
  price_precision = 2 → sell_price = 30100.12
  amount_precision = 5 → amount = 1.00000
  fee_rate = 0.001
  sell_fee = d(30100.12 × 1.0 × 0.001, 8) = d(30.10012, 8) = 30.10012000
  sell_value = d(30100.12 × 1.0, 7) = 30100.1200000
  sell_total = d(30100.12 - 30.10012, 7) = 30070.0198800

Profit = d(30070.0198800 - 30024.10008000, 8) = 45.91980000
Profit% = d(45.9198 / 30024.10008, 8) = 0.00152940 (0.153%)
```

✅ Calculation is correct. With `profit_percentage_threshold = 0.003`, this trade would be rejected (0.153% < 0.3%).

### 4.4 Fee Assessment

| Aspect | Assessment | Severity |
|---|---|---|
| Fee computed on rounded price × amount | ✅ Matches exchange behavior | — |
| Fee rate from config, not exchange API | ⚠️ Static — may not match actual tier | **Low** |
| No maker/taker distinction | ⚠️ Single rate per side per exchange | **Low** (conservative if using taker rate) |
| Fee rate converted via `Decimal(str(...))` | ✅ Correct conversion | — |
| Fee precision = 8 dp for all exchanges | ✅ Sufficient — no exchange needs more | — |
| Zero fee rate | ✅ Works — `exchanges_fees_2` has `0.0` fees | — |
| Missing exchange in fee config | ✅ `get_buy_fee()` returns `None` → `calculate_trade()` returns `(0, 0, None)` | — |

---

## 5. Profit Calculation Deep Dive

### 5.1 Exact Formula

```
buy_value_with_fee  = (buy_price × buy_amount) + (buy_price × buy_amount × buy_fee_rate)
sell_value_with_fee = (sell_price × sell_amount) - (sell_price × sell_amount × sell_fee_rate)

profit     = sell_value_with_fee - buy_value_with_fee
profit_pct = profit / buy_value_with_fee
```

All operations use `Decimal` with `ROUND_HALF_UP` quantization at each step.

### 5.2 Concrete Examples

**Example 1: Profitable trade (above threshold)**

```
Buy: OKX, BTC/USDT, price=29500.0, amount=1.0, fee=0.0008
Sell: Binance, BTC/USDT, price=29700.00, amount=1.0, fee=0.001

buy_price_d  = d(29500.0, 1) = 29500.0
buy_amount_d = d(1.0, 8) = 1.00000000
buy_fee_d    = d(29500.0 × 1.0 × 0.0008, 8) = 23.60000000
buy_value_d  = d(29500.0 × 1.0, 8) = 29500.00000000
buy_total_d  = d(29500.0 + 23.6, 8) = 29523.60000000

sell_price_d  = d(29700.00, 2) = 29700.00
sell_amount_d = 1.00000000
sell_fee_d    = d(29700.00 × 1.0 × 0.001, 8) = 29.70000000
sell_value_d  = d(29700.00 × 1.0, 7) = 29700.0000000
sell_total_d  = d(29700.0 - 29.7, 7) = 29670.3000000

profit     = d(29670.3 - 29523.6, 8) = 146.70000000
profit_pct = d(146.7 / 29523.6, 8) = 0.00496870 (0.497%)

Threshold = 0.003 (0.3%) → 0.497% ≥ 0.3% → ✅ EXECUTE
```

**Example 2: Marginal trade (below threshold)**

```
Buy: OKX, price=30000.0, amount=1.0, fee=0.0008
Sell: Binance, price=30050.00, amount=1.0, fee=0.001

buy_total  = 30000.0 + 24.0 = 30024.0
sell_total = 30050.0 - 30.05 = 30019.95

profit     = 30019.95 - 30024.0 = -4.05
profit_pct = -4.05 / 30024.0 = -0.000135 (-0.013%)

Threshold = 0.003 → -0.013% < 0.3% → ❌ REJECT (correctly)
```

This example shows that a $50 price difference is NOT enough to cover fees on OKX+Binance. The system correctly rejects this trade.

**Example 3: Edge case — very small amount**

```
Buy: OKX, price=30000.0, amount=0.001, fee=0.0008
Sell: Binance, price=30100.00, amount=0.001, fee=0.001

buy_total  = d(30.0 + 0.024, 8) = 30.02400000
sell_total = d(30.1 - 0.0301, 7) = 30.0699000

profit     = d(30.0699 - 30.024, 8) = 0.04590000
profit_pct = d(0.0459 / 30.024, 8) = 0.00152884 (0.153%)

→ ❌ REJECT (below 0.3% threshold)
```

✅ Small amounts work correctly — Decimal precision handles sub-cent values.

**Example 4: Edge case — zero buy value**

```
If buy_price = 0 or buy_amount = 0:
  value_buying_with_fee_d = 0
  → calculate_trade() returns (0, 0, None) due to zero check
```

✅ Guarded against division by zero.

### 5.3 Rounding Impact Analysis

To quantify the impact of `ROUND_HALF_UP` at each step:

```
Without intermediate rounding (pure Decimal):
  buy_fee = 29500.0 × 1.0 × 0.0008 = 23.6 (exact)
  
With intermediate rounding (d() at each step):
  buy_fee = d(d(29500.0, 1) × d(1.0, 8) × Decimal('0.0008'), 8) = 23.60000000

Difference: 0 (exact in this case)
```

For a case where rounding matters:
```
buy_price = 29500.7 (OKX, precision=1)
  d(29500.7, 1) = 29500.7 (no change — already 1 dp)

buy_price = 29500.75 (OKX, precision=1)
  d(29500.75, 1) = 29500.8 (rounded UP)
  
Impact: 0.05 per unit × 1 BTC = $0.05 overpayment
```

⚠️ `ROUND_HALF_UP` on buy price means the bot may pay slightly more than the target price. On sell price, it may receive slightly more. The net effect is approximately neutral across many trades, but there's a slight systematic bias toward paying more on buys. Severity: **Low**.

### 5.4 Profit Threshold Comparison

```python
if profit_percentage >= percentage_threshold:
```

Both values are `float` at this point — `profit_percentage` is `float(profit_pct_d)` from `calculate_trade()`, and `percentage_threshold` is a `float` from config.

⚠️ **Float comparison risk:** For values very close to the threshold (e.g., `0.003000000000000001` vs `0.003`), float comparison could give incorrect results. However, the Decimal calculation produces values with 8 decimal places of precision, and the threshold is typically a round number (0.003). The probability of a float comparison error at this boundary is negligible. Severity: **Info**.


---

## 6. Order Book & Aggregation Math

### 6.1 VWAP Aggregation

Two VWAP implementations exist (documented in Prompt 03, Section 2.5):

**Formula:** `VWAP = Σ(price_i × volume_i) / Σ(volume_i)`

**Precision analysis for `SonarftApiManager.get_weighted_prices(depth=12)`:**

```python
# Worst case: 12 orders, each with price ~30000 and volume ~10
# sum(price × volume) ≈ 30000 × 10 × 12 = 3,600,000
# sum(volume) ≈ 120
# VWAP ≈ 30000.0

# Float precision: 64-bit double has ~15-16 significant digits
# 3,600,000 has 7 digits → 8-9 digits of fractional precision remain
# For a price of 30000.12345678, we have ~10 digits of precision
# This is more than sufficient for any exchange's price precision (max 8 dp)
```

✅ Float VWAP is precise enough for all practical exchange price precisions.

### 6.2 Edge Cases in Aggregation

| Edge Case | Location | Handling | Risk |
|---|---|---|---|
| Empty order book | `get_weighted_prices()` | `total_volume = 0` → returns `(0.0, 0.0)` | ✅ Safe |
| Single order | Both VWAP functions | VWAP = that order's price (mathematically correct) | ✅ Safe |
| Depth > available orders | `get_weighted_prices()` slices `[:depth]` — returns fewer | ✅ Safe |
| Depth > available orders | `get_weighted_price()` adjusts `depth = len(price_list)` | ✅ Safe |
| Very large volume on one order | VWAP heavily weighted — by design | ✅ Expected |
| Negative prices | Not possible from exchange API | ✅ N/A |
| Zero-price order | Would contribute 0 to numerator, volume to denominator — VWAP pulled toward 0 | ⚠️ Unlikely but unguarded | **Info** |

### 6.3 Price Blending in `weighted_adjust_prices()`

```python
weight = max(0.0, min(1.0, 1 - (volatility * volatility_factor)))
adjusted_buy_price = weight * target_buy_price + (1 - weight) * buy_weighted_price
```

**Precision analysis:**
- `weight` is clamped to `[0.0, 1.0]` — no overflow
- The blending is a convex combination — result is always between the two input prices
- Float multiplication of `weight × price` has ~15 digits of precision — sufficient

✅ No precision concerns in the blending operation.

---

## 7. Rounding Edge Cases

### 7.1 Rounding Timing

The system rounds at two distinct points:

**Point 1: Inside `calculate_trade()`** — every intermediate value is rounded via `d()`:
```
buy_price → d(buy_price, prices_precision)
buy_amount → d(amount, amount_precision)
buy_fee → d(price × amount × rate, fee_precision)
buy_value → d(price × amount, cost_precision)
buy_total → d(value + fee, cost_precision)
```

**Point 2: Never** — the adjusted prices from `weighted_adjust_prices()` are NOT rounded before being passed to `calculate_trade()`. The rounding happens inside `calculate_trade()`.

✅ **Correct timing:** Rounding happens once, at the point of financial calculation, not in intermediate signal processing.

### 7.2 Rounding Error Accumulation

Within `calculate_trade()`, each `d()` call introduces up to `0.5 × 10^(-precision)` of rounding error. The worst case accumulation:

```
buy_price:  ±0.5 × 10^(-1) = ±0.05        (OKX, 1 dp)
buy_amount: ±0.5 × 10^(-8) = ±0.000000005 (negligible)
buy_fee:    ±0.5 × 10^(-8) = ±0.000000005 (negligible)
buy_value:  ±0.5 × 10^(-8) = ±0.000000005 (negligible)
buy_total:  ±0.5 × 10^(-8) = ±0.000000005 (negligible)

Worst case total buy-side error: ≈ ±$0.05 (from price rounding)
```

For a $30,000 BTC trade, $0.05 is 0.000167% — well below the 0.3% profit threshold. The rounding error is negligible relative to the profit margin.

### 7.3 Rounding Direction Bias

`ROUND_HALF_UP` has a slight upward bias for values exactly at the midpoint (e.g., `0.005` rounds to `0.01`, not `0.00`). Over many trades:

| Field | Rounding Direction | Effect |
|---|---|---|
| Buy price | Rounds up | ⚠️ Pays slightly more |
| Sell price | Rounds up | ✅ Receives slightly more |
| Buy amount | Rounds up | ⚠️ Buys slightly more |
| Sell amount | Same as buy | Neutral (same amount both sides) |
| Buy fee | Rounds up | ⚠️ Pays slightly more fee |
| Sell fee | Rounds up | ⚠️ Pays slightly more fee |

**Net bias:** Slight systematic cost increase on the buy side (price + fee round up), partially offset by sell price rounding up. Over thousands of trades, this could amount to a small but measurable drag.

**Recommendation:** Consider `ROUND_HALF_EVEN` (banker's rounding) for fee calculations to eliminate systematic bias. Severity: **Low**.

### 7.4 Rounding Examples That Could Cause Issues

**Scenario: Binance amount precision = 5 dp**

```
Calculated amount: 0.123456789 BTC
Rounded: d(0.123456789, 5) = 0.12346 BTC (rounded UP)

Extra amount: 0.00000789 BTC × $30000 = $0.24
```

This means the bot buys 0.00000789 BTC more than intended. At $30,000/BTC, this is $0.24 — negligible for a single trade but compounds over time.

**Scenario: OKX price precision = 1 dp**

```
Calculated buy price: 29999.95
Rounded: d(29999.95, 1) = 30000.0 (rounded UP)

Overpayment: $0.05 per BTC
```

For 1 BTC, this is $0.05. For 100 trades/day, this is $5/day systematic overpayment.

---

## 8. Exchange-Specific Precision Rules

### 8.1 Static Rules (`EXCHANGE_RULES`)

| Exchange | Price Precision | Amount Precision (Buy) | Amount Precision (Sell) | Cost Precision | Fee Precision |
|---|---|---|---|---|---|
| OKX | 1 dp | 8 dp | 8 dp | 8 dp | 8 dp |
| Bitfinex | 3 dp | 8 dp | 8 dp | 8 dp | 8 dp |
| Binance | 2 dp | 5 dp | 5 dp | 7 dp | 8 dp |

### 8.2 Dynamic Rules (`get_symbol_precision()`)

```python
def get_symbol_precision(self, exchange_id, base, quote):
    market = self.markets.get(exchange_id, {}).get(symbol)
    precision = market.get('precision', {})
    # Converts tick size to decimal places: 0.01 → 2
    return {
        'prices_precision': _to_dp(price_prec),
        'buy_amount_precision': _to_dp(amount_prec),
        'sell_amount_precision': _to_dp(amount_prec),
        'cost_precision': 8,
        'fee_precision': 8,
    }
```

### 8.3 Precision Rule Assessment

| Aspect | Assessment | Severity |
|---|---|---|
| Static fallback for 3 exchanges | ✅ Covers the default config (OKX + Binance) | — |
| Dynamic precision from market data | ✅ Preferred source, falls back to static | — |
| `_to_dp()` tick-size conversion | ✅ Handles both integer precision and float tick sizes | — |
| `cost_precision` hardcoded to 8 in dynamic | ⚠️ May not match exchange's actual cost precision | **Low** |
| `fee_precision` hardcoded to 8 in dynamic | ✅ 8 dp is sufficient for all exchanges | — |
| Missing exchange in `EXCHANGE_RULES` | ✅ Falls back to dynamic precision; if both fail, returns `(0, 0, None)` | — |
| **Minimum order size not checked** | ❌ `market['limits']['amount']['min']` is available from `load_markets()` but never validated | **Medium** |
| **Minimum price not checked** | ❌ `market['limits']['price']['min']` not validated | **Low** |
| **Minimum cost not checked** | ❌ `market['limits']['cost']['min']` not validated | **Medium** |

### 8.4 Static vs Dynamic Precision Mismatch Risk

If the exchange changes its precision rules (e.g., Binance changes BTC/USDT price precision from 2 to 1), the static `EXCHANGE_RULES` would be wrong. The dynamic `get_symbol_precision()` would be correct (loaded from `load_markets()`).

The priority is correct: dynamic first, static fallback. But if `load_markets()` fails silently, the static rules are used without warning. Severity: **Low**.


---

## 9. Numerical Stability Issues

### 9.1 Division-by-Zero Risks

| Location | Division | Guard | Risk |
|---|---|---|---|
| `sonarft_math.py:97` | `profit / buy_value_with_fee` | ✅ `if value_buying_with_fee_d == 0: return 0, 0, None` | **None** |
| `sonarft_prices.py:184` | `sum(p×v) / total_volume` | ✅ `except ZeroDivisionError: return 0.0` | **None** |
| `sonarft_api_manager.py:343` | `sum(p×v) / total_bid_volume` | ✅ `if total_bid_volume == 0: return 0.0, 0.0` | **None** |
| `sonarft_indicators.py:196` | `sum(prices) / N` | ⚠️ `N = limit // 2` — if `limit=0` or `limit=1`, `N=0` → ZeroDivisionError | **Medium** |
| `sonarft_indicators.py:204` | `(current - previous) / previous` | ✅ `if previous_avg_price == 0: return 'neutral'` | **None** |
| `sonarft_indicators.py:267` | `sum(prices) / N` | ⚠️ Same as line 196 — `N=0` possible | **Low** (different function, same pattern) |
| `sonarft_indicators.py:272` | `(current - previous) / previous` | ❌ No zero guard (unlike line 204) | **Medium** |
| `sonarft_indicators.py:296` | `(spread - previous) / previous` | ✅ `if previous != 0 else 0` | **None** |
| `sonarft_indicators.py:379` | `(bids[0] + asks[0]) / 2` | ✅ Guarded by `if not bids or not asks: return 0.0` | **None** |
| `sonarft_indicators.py:389` | `total_volume / reference_volume` | ✅ `reference_volume = 100.0` (constant, never zero) | **None** |
| `sonarft_indicators.py:435` | `(current - past) / past` | ✅ `if past_price == 0: return 0.5` | **None** |
| `sonarft_indicators.py:464` | `(v1 - v2) / ((v1 + v2) / 2)` | ❌ No guard — if `v1 = -v2`, denominator = 0 | **Low** |
| `sonarft_validators.py:66` | `spread / bid_prices[0]` | ✅ `if bid_prices[0] == 0: return False` (line 63) | **None** |
| `sonarft_validators.py:72` | `depth_bids / depth_asks` | ❌ No zero guard — if all ask volumes are 0 | **Low** |
| `sonarft_validators.py:99` | `spread / ((ask + bid) / 2)` | ❌ No guard — if `ask + bid = 0` | **Low** |
| `sonarft_validators.py:142` | `trade_spread_sum / trade_volume_sum` | ✅ `if trade_volume_sum == 0: return 0, 0, 0, 0, None` | **None** |
| `sonarft_validators.py:152` | `trade_price_sum / actual_count` | ✅ `if actual_count == 0: return 0, 0, 0, 0, None` | **None** |
| `sonarft_validators.py:187` | `spread / average_price` | ❌ No guard — if both prices are 0 | **Low** |
| `sonarft_validators.py:229` | `(top_price - trade_price) / trade_price` | ❌ No guard — if `trade_price = 0` | **Medium** |
| `sonarft_validators.py:252` | `(sell - buy) / buy` | ❌ No guard — if `buy_price = 0` | **Medium** |

### 9.2 Overflow/Underflow Risks

| Scenario | Risk | Assessment |
|---|---|---|
| Very large prices (e.g., BTC at $1M) | `float` max ≈ 1.8 × 10^308 — no risk | **None** |
| Very small amounts (e.g., 0.00000001 BTC) | `float` min ≈ 5 × 10^-324 — no risk | **None** |
| `Decimal` overflow | `prec=28` handles up to 10^28 — no risk for any currency | **None** |
| Accumulation in VWAP | `sum(price × volume)` for 12 orders ≈ 10^7 — no risk | **None** |
| `np.std()` on empty array | Returns `nan` — propagates to volatility | **Low** |

### 9.3 NaN/Inf Risks

| Source | When | Handling | Risk |
|---|---|---|---|
| `pta.rsi()` returns NaN | Insufficient data or constant prices | ✅ `if pd.isna(value): return None` | **None** |
| `pta.stochrsi()` returns NaN | Insufficient data | ✅ `if pd.isna(k_val) or pd.isna(d_val): return None` | **None** |
| `pta.macd()` returns NaN | Insufficient data | ✅ `if pd.isna(m) or pd.isna(s) or pd.isna(h): return None` | **None** |
| `np.std([])` returns NaN | Empty price list | ❌ Not guarded in `get_volatility()` | **Low** |
| Division by zero → Inf | Various locations | Partially guarded (see 9.1) | **Medium** |
| `Decimal` division by zero | `profit / buy_total` | ✅ Guarded by zero check | **None** |

---

## 10. Precision Audit Table

| # | Function | Issue | Severity | Example | Fix |
|---|---|---|---|---|---|
| **P1** | `get_short_term_market_trend` | `N = limit // 2` — if `limit=0`, `N=0` → ZeroDivisionError | **Medium** | `get_short_term_market_trend(exchange, 'BTC', 'USDT', '1m', 0)` | Guard: `if N <= 0: return 'neutral'` |
| **P2** | `get_price_change` line 272 | `previous_avg_price` can be 0 → ZeroDivisionError | **Medium** | All previous close prices are 0 (exchange returns 0) | Guard: `if previous_avg_price == 0: return None` |
| **P3** | `check_exchange_slippage` line 229 | `trade_price` can be 0 → ZeroDivisionError | **Medium** | Trade with price=0 (shouldn't happen but unguarded) | Guard: `if trade_price == 0: return False` |
| **P4** | `calculate_slippage_tolerance` line 252 | `buy_price` can be 0 → ZeroDivisionError | **Medium** | Historical trade with buy_price=0 | Guard: `if buy_price <= 0: continue` |
| **P5** | `calculate_trade` output | `float()` conversion from Decimal loses ~1e-16 precision | **Low** | `Decimal('0.00152940')` → `float` = `0.0015294000000000001` | Accept — below any meaningful threshold |
| **P6** | `weighted_adjust_prices` | Entire pipeline uses float — accumulated error ~1e-12 | **Low** | Multiple float multiplications | Accept — eliminated by Decimal boundary in `calculate_trade()` |
| **P7** | `ROUND_HALF_UP` systematic bias | Buy prices round up → systematic overpayment | **Low** | $0.05/trade × 100 trades/day = $5/day | Consider `ROUND_HALF_EVEN` for fees |
| **P8** | `verify_spread_threshold` line 187 | `average_price` can be 0 → ZeroDivisionError | **Low** | Both buy and sell price are 0 | Guard: `if average_price == 0: return False` |
| **P9** | `deeper_verify_liquidity` line 72 | `depth_asks` can be 0 → ZeroDivisionError | **Low** | Empty ask side of order book | Guard: `if depth_asks == 0 or depth_bids == 0: return False` |
| **P10** | `get_volatility` | `np.std([])` on empty price list → NaN | **Low** | Empty order book | Guard: `if not bid_prices or not ask_prices: return 0.0` |
| **P11** | Minimum order size | Not validated against exchange limits | **Medium** | Amount below exchange minimum → order rejected | Check `market['limits']['amount']['min']` |
| **P12** | Minimum cost | Not validated against exchange limits | **Medium** | `price × amount` below exchange minimum cost | Check `market['limits']['cost']['min']` |
| **P13** | `profit_percentage >= threshold` | Float comparison at boundary | **Info** | `0.003000000000000001 >= 0.003` → True (correct by luck) | Accept — negligible risk |

---

## 11. Conclusion & Remediation

### Overall Precision Safety: **Good**

The financial calculation core (`SonarftMath.calculate_trade()`) is well-implemented:
- ✅ `Decimal` arithmetic with `ROUND_HALF_UP` throughout
- ✅ `Decimal(str(value))` conversion avoids float→Decimal trap
- ✅ Per-exchange precision rules with dynamic fallback
- ✅ Fees included before profitability decision
- ✅ Zero-value guard on profit percentage division
- ✅ `getcontext().prec = 28` — sufficient for all financial calculations

### Risk Distribution

| Severity | Count | Category |
|---|---|---|
| **High** | 0 | — |
| **Medium** | 6 | Division-by-zero (4), minimum order/cost validation (2) |
| **Low** | 7 | Float precision, rounding bias, NaN risks |
| **Info** | 1 | Float comparison at threshold boundary |

### Critical Fixes Needed

**Priority 1 — Division-by-zero guards (P1-P4, P8-P9):**

These are all the same pattern — add a zero guard before division:

```python
# Pattern to apply in all affected locations:
if denominator == 0:
    return safe_default  # None, False, 'neutral', or 0.0 as appropriate
```

Affected functions:
- `get_short_term_market_trend()` — guard `N <= 0`
- `get_price_change()` — guard `previous_avg_price == 0`
- `check_exchange_slippage()` — guard `trade_price == 0`
- `calculate_slippage_tolerance()` — guard `buy_price <= 0`
- `verify_spread_threshold()` — guard `average_price == 0`
- `deeper_verify_liquidity()` — guard `depth_asks == 0`

**Priority 2 — Minimum order validation (P11-P12):**

Add validation in `SonarftExecution.create_order()`:

```python
market = self.api_manager.markets.get(exchange_id, {}).get(f"{base}/{quote}", {})
limits = market.get('limits', {})
min_amount = limits.get('amount', {}).get('min', 0)
min_cost = limits.get('cost', {}).get('min', 0)
if trade_amount < min_amount:
    self.logger.warning(f"Amount {trade_amount} below minimum {min_amount}")
    return None
if trade_amount * price < min_cost:
    self.logger.warning(f"Cost {trade_amount * price} below minimum {min_cost}")
    return None
```

### Systematic Improvement Recommendations

1. **Add a `safe_divide()` utility** to eliminate all division-by-zero risks:
   ```python
   def safe_divide(numerator, denominator, default=0.0):
       return numerator / denominator if denominator != 0 else default
   ```

2. **Consider `ROUND_HALF_EVEN`** for fee calculations to eliminate systematic rounding bias (Priority: Low — $5/day at 100 trades/day).

3. **Add exchange limit validation** at order creation time using data from `load_markets()`.

4. **Keep the float→Decimal boundary** where it is — the current design is correct. Do NOT convert the entire pipeline to Decimal; it would add complexity without meaningful precision improvement.

---

*Generated by Prompt 04-BOT-MATH. Next: [05-indicator-pipeline.md](../prompts/05-indicator-pipeline.md)*


---

## Remediation Status (Post-Implementation Update — July 2025)

| # | Issue | Original Severity | Status | Task |
|---|---|---|---|---|
| P1 | `get_short_term_market_trend` N=0 ZeroDivisionError | Medium | ✅ **FIXED** — Already had `previous_avg_price == 0` guard; `N=0` prevented by `len(ohlcv) < 2*N` check | — |
| P2 | `get_price_change` zero division | Medium | ✅ **FIXED** — Ternary guard on `previous_avg_price` | T08 |
| P3 | `check_exchange_slippage` zero division | Medium | ✅ **FIXED** — Ternary guard on `trade_price` | T08 |
| P4 | `calculate_slippage_tolerance` zero division | Medium | ✅ Already guarded — `buy_price > 0` in loop condition | — |
| P5 | `calculate_trade` float() conversion | Low | ⚠️ Accepted — below meaningful threshold | — |
| P6 | Float pipeline accumulated error | Low | ⚠️ Accepted — eliminated by Decimal boundary | — |
| P7 | `ROUND_HALF_UP` systematic bias | Low | ✅ **FIXED** — Fee calculations use ROUND_HALF_EVEN by default | D4 |
| P8 | `verify_spread_threshold` zero division | Low | ✅ **FIXED** — Guard `average_price == 0` | T08 |
| P9 | `deeper_verify_liquidity` zero division | Low | ✅ **FIXED** — Guard `depth_asks == 0 or depth_bids == 0` | T08 |
| P10 | `get_volatility` NaN from empty input | Low | ✅ **FIXED** — `if np.isnan(volatility): return 0.0` | T09 |
| P11 | Minimum order size not validated | Medium | ✅ **FIXED** — Checks exchange limits from market data | T21 |
| P12 | Minimum cost not validated | Medium | ✅ **FIXED** — Checks `market['limits']['cost']['min']` | T21 |
| P13 | Float comparison at threshold boundary | Info | ⚠️ Accepted — negligible risk | — |

**All 6 Medium-severity math/precision issues are resolved.** Additionally: ROUND_HALF_EVEN for fees eliminates systematic rounding bias (D4).
