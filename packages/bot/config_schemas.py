"""
SonarFT Config Schemas Module
Pydantic models for validating all configuration sections at load time.

Validation happens in load_configurations() before any trading parameters
are applied, surfacing type errors and missing fields with clear messages
rather than cryptic KeyError/TypeError at the point of use.
"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ParametersConfig(BaseModel):
    """Trading parameters loaded from config_parameters.json."""

    strategy: Literal["arbitrage", "market_making"] = "arbitrage"
    profit_percentage_threshold: float = Field(..., gt=0, lt=1)
    trade_amount: float = Field(..., gt=0)
    is_simulating_trade: Literal[0, 1]
    max_daily_loss: float = Field(default=0.0, ge=0)
    max_trade_amount: float = Field(default=0.0, ge=0)
    max_orders_per_minute: int = Field(default=0, ge=0)
    spread_increase_factor: float = Field(default=1.00020)
    spread_decrease_factor: float = Field(default=0.99980)
    slippage_buffer: float = Field(default=0.0, ge=0)
    flash_crash_threshold: float = Field(default=0.02, gt=0, lt=1)
    max_daily_trades: int = Field(default=0, ge=0)
    max_total_exposure: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def validate_spread_factors_for_market_making(self) -> "ParametersConfig":
        if self.strategy == "market_making":
            if not (1.0 < self.spread_increase_factor < 1.01):
                raise ValueError(
                    f"spread_increase_factor must be between 1.0 and 1.01 "
                    f"for market_making, got {self.spread_increase_factor}"
                )
            if not (0.99 < self.spread_decrease_factor < 1.0):
                raise ValueError(
                    f"spread_decrease_factor must be between 0.99 and 1.0 "
                    f"for market_making, got {self.spread_decrease_factor}"
                )
        return self


class SymbolConfig(BaseModel):
    """A single trading pair entry from config_symbols.json."""

    base: str = Field(..., min_length=1)
    quotes: list[str] = Field(..., min_length=1)

    @field_validator("quotes")
    @classmethod
    def quotes_not_empty_strings(cls, v: list[str]) -> list[str]:
        for q in v:
            if not q.strip():
                raise ValueError("quote currency must not be an empty string")
        return v


class FeeConfig(BaseModel):
    """A single exchange fee entry from config_fees.json."""

    exchange: str = Field(..., min_length=1)
    buy_fee: float = Field(..., ge=0)
    sell_fee: float = Field(..., ge=0)
    maker_buy_fee: float = Field(default=None, ge=0)
    maker_sell_fee: float = Field(default=None, ge=0)

    @model_validator(mode="after")
    def no_zero_fees(self) -> "FeeConfig":
        """Reject entries where both buy_fee and sell_fee are zero.

        A zero-fee config causes the profit calculation to omit all fee
        deductions, making every trade appear profitable regardless of
        actual exchange costs. This is a live trading trap.
        """
        if self.buy_fee == 0.0 and self.sell_fee == 0.0:
            raise ValueError(
                f"Exchange '{self.exchange}' has buy_fee=0 and sell_fee=0. "
                "Zero fees cause incorrect profit calculations. "
                "Set realistic fee rates or remove this entry."
            )
        return self
