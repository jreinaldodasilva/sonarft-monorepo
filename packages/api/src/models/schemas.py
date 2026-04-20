"""
SonarFT API Models
Pydantic schemas for all request and response bodies.
"""
from __future__ import annotations
import re
from typing import Annotated, Optional
from pydantic import BaseModel, Field, field_validator


# ### Bot models ###

class BotCreateResponse(BaseModel):
    botid: str

class BotListResponse(BaseModel):
    botids: list[str]

class BotActionRequest(BaseModel):
    botid: Optional[str] = None

class BotStatusResponse(BaseModel):
    botid: str
    status: str  # idle | running | error


# ### Trade / Order models ###

class TradeRecord(BaseModel):
    timestamp: str
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


# ### Config key validation ###
# Allows real-world keys like "BTC/USDT", "Relative Strength Index (14)", "5min",
# "MACD Level (12, 26)", "Stochastic %K (14, 3, 3)"
# Rejects path traversal, shell injection, and prototype pollution attempts.
_CONFIG_KEY_RE = re.compile(r'^[\w\s/(). %,:-]{1,128}$')


def _validate_config_keys(mapping: dict[str, bool], field_name: str) -> dict[str, bool]:
    """Raise ValueError if any key contains unsafe characters."""
    for key in mapping:
        if not _CONFIG_KEY_RE.match(key):
            raise ValueError(
                f"Invalid key in '{field_name}': {key!r}. "
                f"Keys must be 1-128 chars and contain only "
                f"alphanumeric characters, spaces, and: / ( ) . % -"
            )
    return mapping


# ### Parameters models ###

class ParametersConfig(BaseModel):
    exchanges: dict[str, bool] = Field(default_factory=dict)
    symbols: dict[str, bool] = Field(default_factory=dict)

    @field_validator("exchanges")
    @classmethod
    def validate_exchanges(cls, v: dict[str, bool]) -> dict[str, bool]:
        return _validate_config_keys(v, "exchanges")

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v: dict[str, bool]) -> dict[str, bool]:
        return _validate_config_keys(v, "symbols")


# ### Indicators models ###

class IndicatorsConfig(BaseModel):
    periods: dict[str, bool] = Field(default_factory=dict)
    oscillators: dict[str, bool] = Field(default_factory=dict)
    movingaverages: dict[str, bool] = Field(default_factory=dict)

    @field_validator("periods")
    @classmethod
    def validate_periods(cls, v: dict[str, bool]) -> dict[str, bool]:
        return _validate_config_keys(v, "periods")

    @field_validator("oscillators")
    @classmethod
    def validate_oscillators(cls, v: dict[str, bool]) -> dict[str, bool]:
        return _validate_config_keys(v, "oscillators")

    @field_validator("movingaverages")
    @classmethod
    def validate_movingaverages(cls, v: dict[str, bool]) -> dict[str, bool]:
        return _validate_config_keys(v, "movingaverages")


# ### WebSocket event models ###

class WsLogEvent(BaseModel):
    type: str = "log"
    level: str = "INFO"
    message: str
    ts: int

class WsBotCreatedEvent(BaseModel):
    type: str = "bot_created"
    botid: Optional[str] = None
    ts: int

class WsBotRemovedEvent(BaseModel):
    type: str = "bot_removed"
    botid: Optional[str] = None
    ts: int

class WsOrderSuccessEvent(BaseModel):
    type: str = "order_success"
    ts: int

class WsTradeSuccessEvent(BaseModel):
    type: str = "trade_success"
    ts: int


# ### Generic responses ###

class MessageResponse(BaseModel):
    message: str

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
