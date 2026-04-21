"""
SonarFT Trade Validator Module
Pre-execution validation: liquidity depth and spread threshold checks.
"""
import asyncio
import logging

from sonarft_validators import SonarftValidators


class TradeValidator:
    """Validates trade requirements before execution dispatch."""

    def __init__(self, sonarft_validators: SonarftValidators, logger=None):
        self.sonarft_validators = sonarft_validators
        self.logger = logger or logging.getLogger(__name__)

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
        """Check liquidity and spread threshold before trade execution."""
        result_01, result_02 = await asyncio.gather(
            self.sonarft_validators.deeper_verify_liquidity(
                buy_exchange, base, quote, "buy", buy_price, trade_amount, 50
            ),
            self.sonarft_validators.deeper_verify_liquidity(
                sell_exchange, base, quote, "ask", sell_price, trade_amount, 50
            ),
        )
        if result_01 is False or result_02 is False:
            return False

        if not await self.sonarft_validators.verify_spread_threshold(
            buy_exchange, sell_exchange, base, quote, buy_price, sell_price
        ):
            return False

        return True
