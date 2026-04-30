"""
SonarFT Models Module
Domain data classes shared across modules.
"""
from dataclasses import dataclass

# RSI signal thresholds — shared across pricing and execution layers.
# Using a single source of truth prevents the 72/28 vs 70/30 inconsistency.
RSI_OVERBOUGHT: int = 70
RSI_OVERSOLD: int = 30


@dataclass
class Trade:
    position: str
    base: str
    quote: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    buy_trade_amount: float
    sell_trade_amount: float
    executed_amount: float
    buy_value: float
    sell_value: float
    buy_fee_rate: float
    sell_fee_rate: float
    buy_fee_base: float
    buy_fee_quote: float
    sell_fee_quote: float
    profit: float
    profit_percentage: float
    # Pre-computed indicators passed from price adjustment to avoid re-fetch at execution
    market_direction_buy: str = None
    market_direction_sell: str = None
    market_rsi_buy: float = None
    market_rsi_sell: float = None
    market_stoch_rsi_buy_k: float = None
    market_stoch_rsi_buy_d: float = None
    market_stoch_rsi_sell_k: float = None
    market_stoch_rsi_sell_d: float = None


def vwap(price_volume_list: list, depth: int) -> float:
    """Calculate volume-weighted average price for a list of [price, volume] pairs.
    Returns 0.0 if total volume is zero or list is empty."""
    if not price_volume_list:
        return 0.0
    if len(price_volume_list) < depth:
        depth = len(price_volume_list)
    entries = price_volume_list[:depth]
    total_volume = sum(volume for _, volume in entries)
    if total_volume == 0:
        return 0.0
    return sum(price * volume for price, volume in entries) / total_volume
