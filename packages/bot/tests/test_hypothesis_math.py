"""
Property-based tests for SonarftMath.calculate_trade() using hypothesis.
Covers TD-08 — catches edge cases in financial math that unit tests miss.
"""
from unittest.mock import MagicMock

from hypothesis import assume, given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_math(buy_fee=0.001, sell_fee=0.001, precision=None):
    from sonarft_math import SonarftMath
    api = MagicMock()
    api.get_buy_fee.return_value = buy_fee
    api.get_sell_fee.return_value = sell_fee
    api.get_symbol_precision.return_value = precision
    return SonarftMath(api)


def _price_list(exchange, price):
    return (exchange, price, price + 10, price + 5, 'BTC/USDT')


# ---------------------------------------------------------------------------
# Property: profit sign is consistent with price relationship
# ---------------------------------------------------------------------------

@given(
    buy_price=st.floats(min_value=100.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
    spread_pct=st.floats(min_value=0.005, max_value=0.05, allow_nan=False),
    amount=st.floats(min_value=0.001, max_value=10.0, allow_nan=False, allow_infinity=False),
    fee=st.floats(min_value=0.0, max_value=0.005, allow_nan=False),
)
@settings(max_examples=200, deadline=5000)
def test_profit_sign_consistent_with_spread(buy_price, spread_pct, amount, fee):
    """If sell_price > buy_price by enough to cover fees, profit must be positive."""
    assume(buy_price > 0 and amount > 0)
    sell_price = buy_price * (1 + spread_pct)
    math = _make_math(buy_fee=fee, sell_fee=fee)
    profit, pct, data = math.calculate_trade(
        buy_price, sell_price,
        _price_list('binance', buy_price),
        _price_list('okx', sell_price),
        amount, 'BTC', 'USDT',
    )
    if data is None:
        return  # exchange not in EXCHANGE_RULES — skip
    # If spread covers 2× fee with a generous buffer for rounding, profit must be positive
    if spread_pct > 2 * fee + 0.005:
        assert profit > 0, f"Expected profit > 0 for spread={spread_pct:.4f}, fee={fee:.4f}, buy={buy_price}"
    # Profit sign must match percentage sign
    assert (profit >= 0) == (pct >= 0), f"Sign mismatch: profit={profit}, pct={pct}"


# ---------------------------------------------------------------------------
# Property: profit percentage is bounded
# ---------------------------------------------------------------------------

@given(
    buy_price=st.floats(min_value=1.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
    sell_price=st.floats(min_value=1.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
    amount=st.floats(min_value=0.001, max_value=10.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=5000)
def test_profit_never_nan_or_inf(buy_price, sell_price, amount):
    """calculate_trade() must never return NaN or Inf for any valid inputs."""
    assume(buy_price > 0 and sell_price > 0 and amount > 0)
    import math as _math
    math = _make_math()
    profit, pct, data = math.calculate_trade(
        buy_price, sell_price,
        _price_list('binance', buy_price),
        _price_list('okx', sell_price),
        amount, 'BTC', 'USDT',
    )
    if data is None:
        return
    assert not _math.isnan(profit), f"profit is NaN for buy={buy_price}, sell={sell_price}"
    assert not _math.isinf(profit), f"profit is Inf for buy={buy_price}, sell={sell_price}"
    assert not _math.isnan(pct), "pct is NaN"
    assert not _math.isinf(pct), "pct is Inf"
    # Profit sign must always match percentage sign
    assert (profit >= 0) == (pct >= 0), f"Sign mismatch: profit={profit}, pct={pct}"


# ---------------------------------------------------------------------------
# Property: zero amount always returns None data
# ---------------------------------------------------------------------------

@given(
    buy_price=st.floats(min_value=1.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
    sell_price=st.floats(min_value=1.0, max_value=100_000.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=50, deadline=5000)
def test_zero_amount_always_returns_none(buy_price, sell_price):
    """Zero trade amount must always return None data regardless of prices."""
    math = _make_math()
    _, _, data = math.calculate_trade(
        buy_price, sell_price,
        _price_list('binance', buy_price),
        _price_list('okx', sell_price),
        0.0, 'BTC', 'USDT',
    )
    assert data is None


# ---------------------------------------------------------------------------
# Property: higher fees always reduce profit
# ---------------------------------------------------------------------------

@given(
    buy_price=st.floats(min_value=100.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    spread_pct=st.floats(min_value=0.005, max_value=0.02, allow_nan=False),
    amount=st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
    low_fee=st.floats(min_value=0.0, max_value=0.005, allow_nan=False),
    high_fee=st.floats(min_value=0.005, max_value=0.01, allow_nan=False),
)
@settings(max_examples=100, deadline=5000)
def test_higher_fees_reduce_profit(buy_price, spread_pct, amount, low_fee, high_fee):
    """Higher fees must always produce lower (or equal) profit than lower fees."""
    assume(buy_price > 0 and amount > 0 and high_fee > low_fee)
    sell_price = buy_price * (1 + spread_pct)
    math_low  = _make_math(buy_fee=low_fee,  sell_fee=low_fee)
    math_high = _make_math(buy_fee=high_fee, sell_fee=high_fee)
    profit_low,  _, data_low  = math_low.calculate_trade(
        buy_price, sell_price,
        _price_list('binance', buy_price), _price_list('okx', sell_price),
        amount, 'BTC', 'USDT',
    )
    profit_high, _, data_high = math_high.calculate_trade(
        buy_price, sell_price,
        _price_list('binance', buy_price), _price_list('okx', sell_price),
        amount, 'BTC', 'USDT',
    )
    if data_low is None or data_high is None:
        return
    assert profit_low >= profit_high, (
        f"Expected low_fee profit ({profit_low}) >= high_fee profit ({profit_high})"
    )
