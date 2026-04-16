"""
SonarFT API Models
Pydantic schemas for all request and response bodies.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


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
    buy_trade_amount: float
    buy_exchange: str
    buy_price: float
    buy_value: float
    sell_exchange: str
    sell_price: float
    sell_value: float
    profit: float
    profit_percentage: float


# ### Parameters models ###

class ParametersConfig(BaseModel):
    exchanges: dict[str, bool] = Field(default_factory=dict)
    symbols: dict[str, bool] = Field(default_factory=dict)


# ### Indicators models ###

class IndicatorsConfig(BaseModel):
    periods: dict[str, bool] = Field(default_factory=dict)
    oscillators: dict[str, bool] = Field(default_factory=dict)
    movingaverages: dict[str, bool] = Field(default_factory=dict)


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
