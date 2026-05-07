"""
SonarFT API Models
Pydantic schemas for all request and response bodies.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ### Bot models ###

class BotCreateResponse(BaseModel):
    botid: str

class BotListResponse(BaseModel):
    botids: list[str]


# ### Trade / Order models ###

class TradeRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

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


# Maximum number of entries allowed in any config dict.
# Prevents unbounded file writes from malicious or buggy clients.
_MAX_CONFIG_DICT_SIZE = 50


def _validate_config_keys(mapping: dict[str, bool], field_name: str) -> dict[str, bool]:
    """Raise ValueError if any key contains unsafe characters or the dict is too large."""
    if len(mapping) > _MAX_CONFIG_DICT_SIZE:
        raise ValueError(
            f"'{field_name}' must not exceed {_MAX_CONFIG_DICT_SIZE} entries, "
            f"got {len(mapping)}"
        )
    for key in mapping:
        if not _CONFIG_KEY_RE.match(key):
            raise ValueError(
                f"Invalid key in '{field_name}': {key!r}. "
                f"Keys must be 1-128 chars and contain only "
                f"alphanumeric characters, spaces, and: / ( ) . % -"
            )
    return mapping


# ### Parameters models ###

class ClientParametersConfig(BaseModel):
    version: int = Field(default=1, ge=1, description="Schema version — increment on breaking changes")
    exchanges: dict[str, bool] = Field(default_factory=dict)
    symbols: dict[str, bool] = Field(default_factory=dict)
    strategy: Literal["arbitrage", "market_making"] = "arbitrage"

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
    version: int = Field(default=1, ge=1, description="Schema version — increment on breaking changes")
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

class WsBaseEvent(BaseModel):
    """Base class for all server-to-client WebSocket events.
    Mirrors the WsBaseEvent interface in shared/types/api.ts.
    """
    ts: int


class WsConnectedEvent(WsBaseEvent):
    type: Literal["connected"] = "connected"
    client_id: str


class WsLogEvent(WsBaseEvent):
    type: Literal["log"] = "log"
    # Expanded to match the full Python logging level set.
    # TypeScript consumers should handle all five levels.
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    message: str


class WsBotCreatedEvent(WsBaseEvent):
    type: Literal["bot_created"] = "bot_created"
    botid: str | None = None


class WsBotRemovedEvent(WsBaseEvent):
    type: Literal["bot_removed"] = "bot_removed"
    botid: str | None = None


class WsBotStoppedEvent(WsBaseEvent):
    type: Literal["bot_stopped"] = "bot_stopped"
    botid: str


class WsOrderSuccessEvent(WsBaseEvent):
    type: Literal["order_success"] = "order_success"


class WsTradeSuccessEvent(WsBaseEvent):
    type: Literal["trade_success"] = "trade_success"


class WsErrorEvent(WsBaseEvent):
    type: Literal["error"] = "error"
    message: str


class WsPingEvent(WsBaseEvent):
    type: Literal["ping"] = "ping"


# ### WebSocket ticket response ###

class WsTicketResponse(BaseModel):
    """Response from POST /ws/ticket — single-use WebSocket auth ticket."""
    ticket: str
    ttl_seconds: int = 30


# ### Generic responses ###

class MessageResponse(BaseModel):
    message: str

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
