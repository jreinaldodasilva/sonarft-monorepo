# Bot Package — Financial Math & Precision Review

**Prompt ID:** 04-BOT-MATH  
**Generated:** July 2025  
**Source:** `packages/bot/` — full static analysis  
**Output File:** `docs/trading/math-analysis.md`  
**Depends On:** `docs/architecture/bot-overview.md` (01), `docs/trading/engine-review.md` (03)

---

## 1. Precision Settings Inventory

### Decimal context

```python
# sonarft_math.py line 11
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, getcontext
getcontext().prec = 28
```

`getcontext().prec = 28` sets the **thread-local** default Decimal context to 28 significant figures. This is set at module import time in `sonarft_math.py`.

**Finding — thread-local context risk:** Python's `decimal` module uses a thread-local context. `getcontext().prec = 28` applies only to the thread that imports `sonarft_math`. In an `asyncio` application all coroutines run on the same OS thread, so this is safe. However, if `asyncio.to_thread` is ever used to run Decimal calculations in a worker thread, that thread will use the default precision (28) only if it imports `sonarft_math` first. Currently no Decimal calculations run in worker threads, so this is a Low risk.

### Rounding strategy

Two rounding modes are used:

| Mode | Applied to | Rationale |
|---|---|---|
| `ROUND_HALF_UP` | Prices, amounts, costs, profit | Standard financial rounding |
| `ROUND_HALF_EVEN` (banker's) | Fees only (default) | Eliminates systematic bias across many trades |
| `ROUND_HALF_UP` for fees | Optional via `SONARFT_FEE_ROUNDING=HALF_UP` env var | Operator override |

The dual-rounding strategy is well-considered. Banker's rounding for fees is correct — over thousands of trades, ROUND_HALF_UP would systematically overstate fees by a small amount.

### Float vs Decimal boundary map

```
Exchange API (float/string)
    │
    ▼
SonarftApiManager  ──── all float ────────────────────────────────────────────┐
    │                                                                          │
    ▼                                                                          │
SonarftPrices      ──── all float (VWAP, blend, adjustment) ─────────────────┤
    │                                                                          │
    ▼                                                                          │
TradeProcessor     ──── float inputs to calculate_trade ─────────────────────┤
    │                                                                          │
    ▼                                                                          │
SonarftMath.calculate_trade                                                    │
    │  float → Decimal(str(value)) ← correct conversion                       │
    │  all arithmetic in Decimal (28 sig figs)                                 │
    │  Decimal → float() at output ← precision boundary                       │
    ▼                                                                          │
trade_data dict    ──── all float ───────────────────────────────────────────┤
    │                                                                          │
    ▼                                                                          │
Trade dataclass    ──── all float ───────────────────────────────────────────┤
    │                                                                          │
    ▼                                                                          │
SonarftExecution   ──── all float (order placement, monitoring) ─────────────┘
```

**Decimal is used only inside `calculate_trade`.** Everything before and after is native Python `float`. This is a deliberate design choice — the profit/fee calculation is the only place where precision is critical for the go/no-go decision.

### Float contamination risk

The main contamination risk is the `float → Decimal(str(value))` conversion at the entry to `calculate_trade`. Using `Decimal(str(value))` (not `Decimal(value)`) is the **correct** approach — it avoids inheriting the float's binary representation error. For example:

```python
Decimal(0.1)          # → Decimal('0.1000000000000000055511151231257827021181583404541015625')
Decimal(str(0.1))     # → Decimal('0.1')  ✅
```

All float inputs to `calculate_trade` go through `Decimal(str(...))`. ✅

---

## 2. Financial Calculation Audit

| Calculation | Location | Uses Decimal? | Rounding Strategy | Edge Cases Handled | Risk |
|---|---|---|---|---|---|
| VWAP (order book) | `models.vwap` | No — float | None (native division) | Zero volume → 0.0 ✅; empty list → 0.0 ✅; zero-price entries not filtered ⚠️ | Low |
| VWAP blend weight | `sonarft_prices.weighted_adjust_prices` | No — float | None | NaN volatility checked ✅; zero weight clamped to [0,1] ✅ | Low |
| Price adjustment blend | `sonarft_prices.weighted_adjust_prices` | No — float | None | Zero adjusted price checked ✅ | Low |
| Spread % (cross-exchange) | `sonarft_validators.verify_spread_threshold` | No — float | None | Zero average price checked ✅ | Low |
| Spread threshold (historical) | `sonarft_validators.calculate_thresholds_based_on_historical_data` | No — float (numpy) | None | Empty data → `{low:0, medium:0, high:0}` ✅; threshold can go negative ⚠️ | Medium |
| Buy cost | `sonarft_math.calculate_trade` | Yes — Decimal | ROUND_HALF_UP | Zero buy value → early return ✅ | None |
| Buy fee | `sonarft_math.calculate_trade` | Yes — Decimal | ROUND_HALF_EVEN (default) | Fee rate from float → `Decimal(str(...))` ✅ | None |
| Sell revenue | `sonarft_math.calculate_trade` | Yes — Decimal | ROUND_HALF_UP | — | None |
| Sell fee | `sonarft_math.calculate_trade` | Yes — Decimal | ROUND_HALF_EVEN (default) | — | None |
| Profit | `sonarft_math.calculate_trade` | Yes — Decimal | ROUND_HALF_UP | — | None |
| Profit % | `sonarft_math.calculate_trade` | Yes — Decimal | ROUND_HALF_UP | Zero denominator not explicitly checked ⚠️ | Low |
| Profit threshold comparison | `trade_processor.process_trade_combination` | No — float | None (direct `>=`) | Comparing two floats from Decimal output — safe for this magnitude | Low |
| Price rounding (monitored) | `sonarft_execution.create_order` | No — `round(float, n)` | IEEE 754 banker's | No fallback if precision unavailable | Low |
| Amount rounding | `sonarft_math.calculate_trade` | Yes — Decimal | ROUND_HALF_UP | — | None |
| Slippage % | `sonarft_execution.create_order` | No — float | None | Zero price guard missing ⚠️ | Low |
| Daily loss accumulation | `sonarft_search.record_trade_result` | No — float | None | Absolute value of negative profit ✅ | Low |
| Volatility (order book std) | `sonarft_indicators.get_volatility` | No — numpy float | None | Zero mid-price checked ✅; NaN → 0.0 ✅ | None |
| Liquidity score | `sonarft_indicators.get_liquidity` | No — float | None | Zero mid-price checked ✅ | None |
| Percentage difference | `models.percentage_difference` | No — float | None | Zero inputs → 0.0 ✅; equal values → 0.0 ✅ | None |

---

## 3. Precision-Sensitive Functions

### `SonarftMath.calculate_trade` — the precision core

```
Inputs:  buy_price (float), sell_price (float), buy_price_list (tuple),
         sell_price_list (tuple), target_amount (float), base (str), quote (str)
Outputs: profit (float), profit_pct (float), trade_data (dict of floats)
```

All intermediate calculations use `Decimal`. Inputs are converted via `Decimal(str(value))`. Outputs are converted back to `float` via `float(decimal_value)`.

**Precision loss at output:** The final `float()` conversion loses the Decimal precision. For a profit of `Decimal('0.00000001')` (1e-8), `float()` preserves this exactly (IEEE 754 double has ~15-17 significant decimal digits, well above 8). For amounts in the range of typical crypto trades (0.001–100 BTC, prices 1–100,000 USDT), the float representation is adequate for the threshold comparison.

### `models.vwap`

```
Inputs:  price_volume_list (list of [price, volume] pairs), depth (int)
Outputs: float
```

Pure float arithmetic. No Decimal. For order book VWAP this is acceptable — the result feeds into a price blend, not a fee calculation. The precision requirement is lower here.

### `models.percentage_difference`

```
Inputs:  value1 (float), value2 (float)
Outputs: float
```

```python
abs((value1 - value2) / ((value1 + value2) / 2)) * 100
```

Float arithmetic. Used in `SonarftHelpers` and `SonarftIndicators` for informational comparisons, not for trade decisions. Acceptable.

### `SonarftIndicators.get_profit_factor`

```
Inputs:  volatility (float), min_spread (float), max_spread (float)
Outputs: float
```

Linear interpolation between `min_spread` (0.99912) and `max_spread` (0.99972). This function is defined but **never called** in the current pipeline — it is dead code. No precision risk.

### `SonarftValidators.calculate_thresholds_based_on_historical_data`

```
Inputs:  historical_data_buy (list), historical_data_sell (list)
Outputs: dict {low: float, medium: float, high: float}
```

Uses `numpy.mean` and `numpy.std` on a list of spread percentages. NumPy uses 64-bit float (same as Python `float`). No precision concern for spread percentages.


---

## 4. Fee Computation Accuracy

### Fee selection logic

```python
# sonarft_api_manager.py
def get_buy_fee(self, exchange_id, order_type="limit"):
    for fee in self.exchanges_fees:
        if fee["exchange"] == exchange_id:
            if order_type == "limit" and "maker_buy_fee" in fee:
                return fee["maker_buy_fee"]
            return fee["buy_fee"]
    return None
```

- Limit orders → maker fee ✅ (correct — limit orders are typically maker orders)
- Market orders → taker fee ✅
- Unknown exchange → `None` (causes `calculate_trade` to return `(0, 0, None)` and skip the trade) ✅

### Fee application timing

Fees are applied **inside `calculate_trade`**, which is called **before** the profitability threshold check. The sequence is:

```
calculate_trade() → profit_after_fees → threshold check → execution
```

This is the correct order. The bot never executes a trade based on gross profit. ✅

### Fee calculation with concrete example

**Setup:** ETH/USDT, buy on OKX, sell on Binance  
**Config:** OKX maker fee = 0.0008 (0.08%), Binance maker fee = 0.001 (0.1%)  
**Prices:** buy = 2000.00 USDT, sell = 2004.00 USDT  
**Amount:** 0.01 ETH  
**Precision rules (OKX):** prices=1dp, amount=8dp, cost=8dp, fee=8dp  
**Precision rules (Binance):** prices=2dp, amount=5dp, cost=7dp, fee=8dp  

```
BUY LEG (OKX):
  buy_price_d          = Decimal('2000.0')          [1 dp]
  target_amount_buy_d  = Decimal('0.01000000')       [8 dp]
  buy_cost             = 2000.0 × 0.01 = 20.00000000 [8 dp]
  buy_fee              = 20.0 × 0.0008 = 0.01600000  [8 dp, ROUND_HALF_EVEN]
  total_buy            = 20.00000000 + 0.01600000
                       = 20.01600000

SELL LEG (Binance):
  sell_price_d         = Decimal('2004.00')          [2 dp]
  target_amount_sell_d = Decimal('0.01000')          [5 dp]  ← Binance 5dp amount
  sell_revenue         = 2004.00 × 0.01000 = 20.0400000 [7 dp]
  sell_fee             = 20.04 × 0.001 = 0.02004000  [8 dp, ROUND_HALF_EVEN]
  net_sell             = 20.0400000 - 0.02004000
                       = 20.0199600  [7 dp]

PROFIT:
  profit     = 20.0199600 - 20.0160000 = 0.00396000  [8 dp]
  profit_pct = 0.00396000 / 20.0160000 = 0.00019784  [8 dp]

THRESHOLD CHECK:
  effective_threshold = 0.0001 + 0.0002 = 0.0003
  0.00019784 < 0.0003 → SKIP (not profitable enough after slippage buffer)
```

**Observation:** With a 0.2 USDT spread on a 2000 USDT asset (0.1%), the trade is skipped because the effective threshold (0.03%) plus fees (0.18% round-trip) consumes the entire spread. This confirms the threshold is correctly calibrated to reject marginal trades.

**Finding — amount precision mismatch between buy and sell legs:** The buy amount is quantized to OKX's 8dp (`0.01000000`) but the sell amount is quantized to Binance's 5dp (`0.01000`). Both represent 0.01 ETH exactly, so there is no discrepancy here. However, for amounts that are not exact multiples of the precision step (e.g. `0.01234567` ETH), the sell amount would be truncated to `0.01234` (5dp), creating a 0.00000567 ETH imbalance between buy and sell legs. This imbalance is not accounted for in the profit calculation — the profit assumes `sell_amount = buy_amount` exactly.

**Finding — `sell_amount_decimal_precision` key is defined but never used:** `EXCHANGE_RULES` contains `'sell_amount_decimal_precision': '0.00000'` (a string format) alongside `'sell_amount_precision': 5` (an integer). The string format key is never referenced in `calculate_trade` — only the integer key is used. The string key is dead configuration.

### Fee refresh accuracy

`refresh_fees` uses `min(maker_fees)` across all symbols. For Binance, the standard maker fee is 0.001 (0.1%) for most pairs, but VIP tiers and BNB discounts can reduce this to 0.0 for some users. The minimum-fee approach is conservative (uses the lowest available rate), which means the bot may underestimate fees for standard-tier accounts and overestimate profitability.

---

## 5. Profit Calculation Deep Dive

### Formula

```
profit = (sell_price × amount - sell_fee) - (buy_price × amount + buy_fee)

where:
  buy_fee  = buy_price  × amount × buy_fee_rate   [ROUND_HALF_EVEN]
  sell_fee = sell_price × amount × sell_fee_rate  [ROUND_HALF_EVEN]

profit_pct = profit / (buy_price × amount + buy_fee)
```

All values are `Decimal` with 28 significant figures during computation.

### Edge case: very small amounts

**Setup:** amount = 0.00000001 ETH (1 satoshi equivalent), buy = 2000 USDT, sell = 2010 USDT

```
buy_cost  = 2000 × 0.00000001 = 0.00002000 USDT
buy_fee   = 0.00002000 × 0.001 = 0.00000002 USDT  [rounds to 0.00000002 at 8dp]
total_buy = 0.00002002 USDT

sell_rev  = 2010 × 0.00000001 = 0.00002010 USDT
sell_fee  = 0.00002010 × 0.001 = 0.00000002 USDT  [rounds to 0.00000002 at 8dp]
net_sell  = 0.00002008 USDT

profit    = 0.00002008 - 0.00002002 = 0.00000006 USDT
profit_pct = 0.00000006 / 0.00002002 = 0.002997...  (0.3%)
```

At this scale, fee rounding (0.00000002 vs the exact 0.00000002000) is exact. The calculation is correct. However, this amount (0.00000001 ETH) is far below any exchange minimum order size and would be rejected at the `min_amount` check in `create_order`.

### Edge case: zero profit denominator

```python
profit_pct_d = d(
    (value_selling_with_fee_d - value_buying_with_fee_d) / value_buying_with_fee_d,
    sell_rules['fee_precision']
)
```

`value_buying_with_fee_d` is checked for zero earlier:

```python
if value_buying_with_fee_d == 0:
    return 0, 0, None
```

This guard prevents `ZeroDivisionError`. ✅

### Edge case: negative profit

When `sell_price < buy_price + fees`, `profit_d` is negative. `profit_pct_d` is also negative. The threshold check `profit_percentage >= effective_threshold` (where threshold > 0) correctly rejects negative-profit trades. ✅

### Edge case: equal buy and sell exchange

`process_symbol` skips combinations where `buy_price_list[0] == sell_price_list[0]` (same exchange). This prevents same-exchange "arbitrage" with zero spread. ✅

### Profit percentage precision at threshold

The threshold comparison is:
```python
if profit_percentage >= effective_threshold:
```

Both values are Python `float` (converted from Decimal). The comparison is exact for values of this magnitude (0.0001–0.001 range). IEEE 754 double has ~15 significant decimal digits, far more than needed for a 4-decimal-place threshold comparison. ✅

---

## 6. Order Book & Aggregation Math

### VWAP formula correctness

```python
def vwap(price_volume_list, depth):
    entries = price_volume_list[:depth]
    total_volume = sum(volume for _, volume in entries)
    if total_volume == 0:
        return 0.0
    return sum(price * volume for price, volume in entries) / total_volume
```

Mathematically correct: `Σ(pᵢ × vᵢ) / Σ(vᵢ)`. ✅

### Depth inconsistency

| Usage | Depth | Effect |
|---|---|---|
| `get_latest_prices` (initial price list) | 12 | Averages top 12 order book levels |
| `get_weighted_price` (indicator blend) | 3 | Averages top 3 levels only |

Using depth=3 for the indicator blend means the adjusted price is more sensitive to the top-of-book spread and less representative of actual execution price for larger orders. For `trade_amount=0.01 ETH`, the top 3 levels are almost always sufficient. For larger amounts, depth=3 may underestimate slippage.

### Order book data types

ccxt returns order book entries as `[price, volume]` where both are Python `float`. The VWAP function receives these directly. No type conversion is needed.

**Finding — no validation of order book entry structure:** `vwap` assumes each entry is a 2-element sequence `[price, volume]`. If ccxt returns a malformed entry (e.g. `[price]` with no volume), the unpacking `for _, volume in entries` raises `ValueError`. This is unlikely with ccxt but not guarded.

### Aggregation precision

VWAP uses native Python `float` division. For order book prices in the range 0.001–100,000 USDT and volumes in the range 0.001–1,000,000, the float representation is adequate. The maximum relative error from float arithmetic is ~2.2e-16 per operation, negligible for price calculations.

---

## 7. Rounding Edge Cases

### Rounding timeline

```
1. buy_price (float from exchange)
        ↓ Decimal(str(buy_price))
2. buy_price_d = quantize to prices_precision (ROUND_HALF_UP)
        ↓ multiply
3. buy_cost = buy_price_d × amount_d (exact Decimal multiply)
        ↓ quantize
4. buy_cost_d = quantize to cost_precision (ROUND_HALF_UP)
        ↓ multiply
5. buy_fee_d = buy_cost × fee_rate (ROUND_HALF_EVEN)
        ↓ add
6. total_buy = buy_cost_d + buy_fee_d (exact Decimal add)
        ↓ quantize
7. total_buy_d = quantize to cost_precision (ROUND_HALF_UP)
        ↓ subtract
8. profit = net_sell - total_buy (exact Decimal subtract)
        ↓ quantize
9. profit_d = quantize to fee_precision (ROUND_HALF_UP)
        ↓ float()
10. profit (float) — precision boundary
```

**Finding — double quantization of buy cost:** `value_buying_d` is quantized at step 4, then `value_buying_with_fee_d` is quantized again at step 7 after adding the fee. Each quantization introduces up to 0.5 ULP of rounding error. Two quantizations on the same value can accumulate up to 1 ULP of error. For 8dp precision, 1 ULP = 1e-8 USDT — negligible for any realistic trade size.

**Finding — price quantized before multiplication:** `buy_price_d` is quantized to `prices_precision` (e.g. 1dp for OKX = nearest 0.1 USDT) before multiplying by amount. This means a buy price of 2000.05 USDT becomes 2000.1 USDT (rounded up), increasing the calculated buy cost by 0.05 × amount. For `amount=0.01`, this is 0.0005 USDT — small but systematic. The exchange will use the actual order price, not the rounded price, so the profit calculation may slightly understate actual profit (conservative). ✅

### Rounding direction bias

- Prices: `ROUND_HALF_UP` — rounds 0.5 up. Slightly overstates buy cost and understates sell revenue → conservative (underestimates profit). ✅
- Fees: `ROUND_HALF_EVEN` — no systematic bias. ✅
- Profit: `ROUND_HALF_UP` — rounds 0.5 up. For positive profit, slightly overstates; for negative profit, slightly understates (rounds toward zero). Negligible effect.

Overall rounding bias is conservative — the bot slightly underestimates profit, which means it may skip some marginally profitable trades but will not execute trades that are actually unprofitable due to rounding. ✅

### Impact of rounding on profitability

For a typical trade (0.01 ETH, 2000 USDT, 0.1% fees):
- Maximum rounding error per calculation step: 0.5 × 10⁻⁸ USDT
- Steps with rounding: ~6
- Maximum cumulative error: ~3 × 10⁻⁸ USDT
- As fraction of trade value (20 USDT): ~1.5 × 10⁻⁹ (0.00000015%)

This is far below the profit threshold (0.01%) and has no practical impact. ✅


---

## 8. Exchange-Specific Precision Rules

### Hardcoded fallback rules (`EXCHANGE_RULES` in `sonarft_math.py`)

| Exchange | Price dp | Amount dp | Cost dp | Fee dp | Notes |
|---|---|---|---|---|---|
| `okx` | 1 | 8 | 8 | 8 | 1dp price = nearest 0.1 USDT — too coarse for low-price assets |
| `bitfinex` | 3 | 8 | 8 | 8 | 3dp price = nearest 0.001 USDT |
| `binance` | 2 | 5 | 7 | 8 | 5dp amount, 7dp cost |

**Finding — OKX 1dp price precision is too coarse for low-price assets:** OKX's hardcoded `prices_precision=1` means all prices are rounded to the nearest 0.1 USDT. For ETH/USDT at ~2000 USDT this is fine (0.005% rounding). For low-price assets like SHIB/USDT at ~0.00001 USDT, rounding to 1dp would produce 0.0 — the entire price is lost. The live precision lookup via `get_symbol_precision` would return the correct per-symbol precision, but the hardcoded fallback is dangerously wrong for non-standard pairs.

**Finding — only 3 exchanges have hardcoded rules:** Any exchange not in `EXCHANGE_RULES` (`okx`, `bitfinex`, `binance`) causes `calculate_trade` to return `(0, 0, None)` and skip the trade silently. If `get_symbol_precision` also returns `None` (markets not loaded), trades on all other exchanges are silently skipped with only a warning log. This affects `binanceus`, `bybit`, `kraken`, and all other exchanges in `config_fees.json`.

### Live precision lookup (`get_symbol_precision` in `sonarft_api_manager.py`)

```python
def _to_dp(v):
    if v is None: return 8
    if isinstance(v, int): return v
    s = f"{v:.10f}".rstrip("0")
    return len(s.split(".")[-1]) if "." in s else 0
```

This converts a tick size (e.g. `0.01`) to decimal places (e.g. `2`). The conversion is correct for standard tick sizes. Edge cases:

- `v = 0.001` → `"0.0010000000"` → strip → `"0.001"` → 3dp ✅
- `v = 1` (integer) → returns `1` directly ✅
- `v = 0.0` → `"0.0000000000"` → strip → `"0"` → no `.` → 0dp ⚠️ (zero tick size treated as 0dp = integer precision)
- `v = 1e-8` → `"0.0000000100"` → strip → `"0.00000001"` → 8dp ✅

**Finding — zero tick size returns 0dp:** If an exchange returns `precision.price = 0.0` (which some exchanges use to indicate "no restriction"), `_to_dp` returns 0, meaning prices are rounded to the nearest integer. This would severely distort profit calculations for assets priced below 1 USDT.

### Code enforcement of exchange minimums

Minimum order size and cost are checked in `SonarftExecution.create_order`:

```python
min_amount = ((limits.get("amount") or {}).get("min")) or 0
min_cost   = ((limits.get("cost") or {}).get("min")) or 0
if min_amount and trade_amount < min_amount: return None
if min_cost and trade_amount * price < min_cost: return None
```

This uses live market data. ✅ The `or 0` pattern treats `None` as 0 (no minimum), which is correct.

**Finding — minimum checks use `trade_amount * price` for cost, not the Decimal-rounded cost:** The cost check multiplies the raw float `trade_amount` by the raw float `price`, not the Decimal-quantized values from `calculate_trade`. For most cases these are identical, but for amounts near the minimum, the float multiplication may differ from the Decimal calculation by 1 ULP, potentially causing a trade to pass the minimum check but fail at the exchange.

---

## 9. Numerical Stability Issues

### Division risks

| Location | Expression | Zero guard |
|---|---|---|
| `models.vwap` | `sum(p×v) / total_volume` | `if total_volume == 0: return 0.0` ✅ |
| `sonarft_math.calculate_trade` profit_pct | `profit / value_buying_with_fee_d` | `if value_buying_with_fee_d == 0: return 0,0,None` ✅ |
| `sonarft_validators.verify_spread_threshold` | `spread / average_price` | `if average_price == 0: return False` ✅ |
| `sonarft_validators.get_trade_dynamic_spread_threshold_avg` | `trade_spread_avg / trade_price_avg` | `if trade_price_avg == 0: return 0,0,0,0,None` ✅ |
| `sonarft_validators.deeper_verify_liquidity` | `spread / bid_prices[0]` | `if bid_prices[0] == 0: return False` ✅ |
| `sonarft_validators.deeper_verify_liquidity` | `depth_bids / depth_asks` | `if depth_bids == 0 or depth_asks == 0: return False` ✅ |
| `sonarft_indicators.get_volatility` | `np.std(...) / mid_price` | `if mid_price == 0: return 0.0` ✅ |
| `sonarft_indicators.get_liquidity` | `total_volume / reference_volume` | `if mid_price == 0: return 0.0` ✅ |
| `sonarft_indicators.get_short_term_market_trend` | `(current - prev) / prev` | `if previous_avg_price == 0: return 'neutral'` ✅ |
| `sonarft_execution.create_order` slippage | `abs(latest - price) / price` | No zero guard ⚠️ |
| `sonarft_execution._determine_position` flash crash | `abs(sell - buy) / buy_price` | `if buy_price > 0 and sell_price > 0` ✅ |
| `sonarft_validators.check_exchange_slippage` | `(top_price - trade_price) / trade_price` | `if trade_price != 0` ✅ |

**Finding — slippage calculation in `create_order` has no zero-price guard:**

```python
slippage = abs(latest_price - price) / price if price else 0.0
```

Wait — this does have a guard: `if price else 0.0`. However, `if price` is falsy for `price=0.0` but also for `price=None`. If `price` is `None` (which should not happen but is not type-checked), this returns `0.0` silently instead of raising. Low risk in practice.

### NaN/Inf risks

| Location | Risk | Guard |
|---|---|---|
| `sonarft_prices.weighted_adjust_prices` | `volatility_buy * vol_adj_buy` could produce NaN if either is NaN | `if math.isnan(volatility_buy) or math.isnan(volatility_sell): return 0,0,{}` ✅ |
| `sonarft_indicators.get_volatility` | `np.std([]) / mid_price` | `if np.isnan(volatility): return 0.0` ✅ |
| `sonarft_math.calculate_trade` | Decimal arithmetic cannot produce NaN or Inf | N/A ✅ |
| `sonarft_indicators.get_rsi` | `pta.rsi` can return NaN for insufficient data | `if pd.isna(value): return None` ✅ |
| `sonarft_indicators.get_macd` | `pta.macd` can return NaN | `if pd.isna(m) or pd.isna(s) or pd.isna(h): return None` ✅ |
| `sonarft_indicators.get_stoch_rsi` | `pta.stochrsi` can return NaN | `if pd.isna(k_val) or pd.isna(d_val): return None` ✅ |

NaN handling is thorough throughout. ✅

### Overflow risks

Python `int` and `Decimal` have arbitrary precision — no integer overflow. Python `float` (IEEE 754 double) overflows at ~1.8 × 10³⁰⁸. For crypto prices (max ~10⁶ USDT) and amounts (max ~10⁶ units), the maximum product is ~10¹² — far below float overflow. No overflow risk. ✅

### Underflow risks

The smallest positive float is ~5 × 10⁻³²⁴. For fee calculations at 8dp precision, the smallest meaningful value is 10⁻⁸. No underflow risk for realistic trade sizes. ✅

---

## 10. Precision Audit Table

| Function | Issue | Severity | Example | Fix |
|---|---|---|---|---|
| `EXCHANGE_RULES['okx']['prices_precision'] = 1` | 1dp price rounds SHIB/USDT (0.00001) to 0.0 | **High** | SHIB at 0.000012 → rounds to 0.0 → profit calc broken | Use live precision from `get_symbol_precision`; remove hardcoded fallback for non-standard pairs |
| `calculate_trade` output | All Decimal values converted to `float` at output | Low | `Decimal('0.00000001')` → `float` loses no precision at this scale | Acceptable for current trade sizes; document the boundary |
| `create_order` price rounding | `round(float, n)` instead of Decimal quantize | Low | `round(2000.005, 2)` may return 2000.0 or 2000.01 depending on float repr | Use `Decimal(str(price)).quantize(Decimal(10)**-n, ROUND_HALF_UP)` |
| `_to_dp(0.0)` | Zero tick size returns 0dp (integer precision) | Medium | Exchange returns `precision.price=0.0` → prices rounded to nearest integer | Treat 0 tick size as "no restriction" (return None or max precision) |
| `sell_amount_decimal_precision` key | Defined in `EXCHANGE_RULES` but never used | Low | Dead config — no effect | Remove or use it in `calculate_trade` |
| `min_cost` check uses raw float multiply | `trade_amount * price` not Decimal-quantized | Low | Near-minimum amounts may differ by 1 ULP | Use Decimal-quantized cost from `calculate_trade` for the check |
| `vwap` zero-price entries | Price=0 entries included in VWAP | Low | Malformed order book entry pulls VWAP toward 0 | Add `if price > 0` guard inside VWAP |
| `calculate_thresholds` negative threshold | `mean - std` can be negative | Medium | Low-volatility market → threshold_low < 0 → any spread passes | `max(0.0, mean - std)` |
| `getcontext().prec = 28` thread-local | Worker threads don't inherit context | Low | `asyncio.to_thread` with Decimal math would use default prec | Set context in thread initializer if Decimal ever moves to threads |
| `exchanges_fees_2` zero fees | Zero fees make all trades appear profitable | **High** | Accidentally used in live mode → real losses | Remove or add Pydantic validator rejecting zero fees |

---

## 11. Conclusion & Remediation

### Overall precision safety

The financial math core (`sonarft_math.calculate_trade`) is **well-implemented**:
- Decimal with 28 significant figures ✅
- Correct `Decimal(str(float))` conversion ✅
- Fees applied before profitability decision ✅
- Banker's rounding for fees (no systematic bias) ✅
- Zero-denominator guard ✅
- Conservative rounding direction (underestimates profit) ✅

The main precision risks are **outside** the core calculation:

### Critical fixes

| Priority | Fix |
|---|---|
| **High** | Remove `exchanges_fees_2` (zero fees) from production config, or add Pydantic validator |
| **High** | Fix OKX hardcoded `prices_precision=1` — it is wrong for any asset priced below 1 USDT |

### Medium fixes

| Priority | Fix |
|---|---|
| **Medium** | Clamp `threshold_low = max(0.0, mean - std)` in `calculate_thresholds_based_on_historical_data` |
| **Medium** | Handle `_to_dp(0.0)` — zero tick size should not produce 0dp integer precision |

### Low fixes (best practice)

| Priority | Fix |
|---|---|
| **Low** | Replace `round(float, n)` with Decimal quantize in `create_order` price rounding |
| **Low** | Add `if price > 0` guard in `vwap` function |
| **Low** | Remove dead `sell_amount_decimal_precision` key from `EXCHANGE_RULES` |
| **Low** | Use Decimal-quantized cost for `min_cost` check in `create_order` |

### Systematic improvement recommendation

The current architecture correctly isolates Decimal arithmetic to `calculate_trade`. This boundary is clean and should be maintained. The recommended improvement is to extend the Decimal boundary slightly:

1. Keep `calculate_trade` as the Decimal core.
2. Add a `quantize_price(price, exchange, base, quote)` helper that uses Decimal for the `create_order` price rounding.
3. Add a `quantize_amount(amount, exchange, base, quote)` helper for the second-leg amount re-quantization.

This would eliminate the two remaining float-rounding issues at order placement without restructuring the entire pipeline.
