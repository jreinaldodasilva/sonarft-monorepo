"""
SonarFT Trade Validator Module
Pre-execution validation: liquidity depth and spread threshold checks.
"""
import asyncio
import logging

from sonarft_validators import SonarftValidators


class TradeValidator:
    """Validates trade requirements before execution dispatch."""

    def __init__(self, sonarft_validators: SonarftValidators, logger=None,
                 min_trading_volume_coefficient: float = 50.0):
        self.sonarft_validators = sonarft_validators
        self.logger = logger or logging.getLogger(__name__)
        self.min_trading_volume_coefficient = min_trading_volume_coefficient

    async def has_requirements_for_success_carrying_out(
        self,
        buy_exchange: str,
        sell_exchange: str,
        base: str,
        quote: str,
        buy_price: float,
        sell_price: float,
        trade_amount: float,
    ) -> bool:
        """Check liquidity and spread threshold before trade execution.
        All three checks run concurrently — they are independent and share
        cached order book / OHLCV data, so parallelism has no extra API cost.
        """
        result_01, result_02, spread_ok = await asyncio.gather(
            self.sonarft_validators.deeper_verify_liquidity(
                buy_exchange, base, quote, "buy", buy_price, trade_amount,
                self.min_trading_volume_coefficient,
            ),
            self.sonarft_validators.deeper_verify_liquidity(
                sell_exchange, base, quote, "ask", sell_price, trade_amount,
                self.min_trading_volume_coefficient,
            ),
            self.sonarft_validators.verify_spread_threshold(
                buy_exchange, sell_exchange, base, quote, buy_price, sell_price
            ),
        )
        return bool(result_01 and result_02 and spread_ok)
