# Prompt 03 — Data Models & Validation Review

**Generated:** July 2025 | **Updated:** July 2025 (post-implementation)
**Reviewer:** Amazon Q (Senior Python / Pydantic v2 / Data Integrity)
**Status:** ✅ All high/medium findings resolved

---

## Executive Summary

All critical model gaps have been resolved. `TradeRecord` is now a 20-field model matching the bot's SQLite schema exactly and is wired as `response_model` on both history endpoints. `ParametersConfig` and `IndicatorsConfig` have `@field_validator` on all 5 dict fields rejecting shell injection and oversized keys. All WebSocket event models now use `Literal` discriminators and are used by the manager via `_push_model`. `WsConnectedEvent`, `WsErrorEvent`, and `WsPingEvent` have been added. `shared/types/api.ts` has been updated to match. The CI pipeline includes a `tsc` typecheck on `api.ts` to catch future drift.

---

## Model Inventory (Current)

| Model | Purpose | Status | Field Count |
|---|---|---|---|
| `BotCreateResponse` | Response: new bot ID | ✅ Used | 1 |
| `BotListResponse` | Response: bot ID list | ✅ Used | 1 |
| `BotActionRequest` | ⚠️ Unused | ℹ️ Kept for future use | 1 |
| `BotStatusResponse` | ⚠️ Unused | ℹ️ Kept for future use | 2 |
| `TradeRecord` | Order/trade history entry | ✅ Wired as `response_model` | **20** |
| `ParametersConfig` | Trading parameters | ✅ Key-validated | 2 |
| `IndicatorsConfig` | Indicator settings | ✅ Key-validated | 3 |
| `WsConnectedEvent` | WS: connection confirmed | ✅ New + used | 3 |
| `WsLogEvent` | WS: log line | ✅ `Literal` type | 4 |
| `WsBotCreatedEvent` | WS: bot created | ✅ `Literal` type + used | 3 |
| `WsBotRemovedEvent` | WS: bot removed | ✅ `Literal` type + used | 3 |
| `WsOrderSuccessEvent` | WS: order placed | ✅ `Literal` type | 2 |
| `WsTradeSuccessEvent` | WS: trade completed | ✅ `Literal` type | 2 |
| `WsErrorEvent` | WS: error | ✅ New + used | 3 |
| `WsPingEvent` | WS: keepalive | ✅ New + used | 2 |
| `WsTicketResponse` | WS ticket issuance | ✅ New | 2 |
| `MessageResponse` | Generic success | ✅ Used | 1 |
| `HealthResponse` | Health check | ✅ Used | 2 |

---

## TradeRecord — Current (20 fields)

```python
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
    sell_trade_amount: float      # ✅ Added
    executed_amount: float        # ✅ Added
    buy_value: float
    sell_value: float
    buy_fee_rate: float           # ✅ Added
    sell_fee_rate: float          # ✅ Added
    buy_fee_base: float           # ✅ Added
    buy_fee_quote: float          # ✅ Added
    sell_fee_quote: float         # ✅ Added
    profit: float
    profit_percentage: float
```

All 20 fields match exactly what `SonarftHelpers.save_order_history` persists to SQLite.

---

## Config Key Validation

```python
_CONFIG_KEY_RE = re.compile(r'^[\w\s/(). %,:-]{1,128}$')

class ParametersConfig(BaseModel):
    exchanges: dict[str, bool] = Field(default_factory=dict)
    symbols: dict[str, bool] = Field(default_factory=dict)

    @field_validator("exchanges")
    @classmethod
    def validate_exchanges(cls, v): return _validate_config_keys(v, "exchanges")

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v): return _validate_config_keys(v, "symbols")
```

Accepts: `"BTC/USDT"`, `"Relative Strength Index (14)"`, `"MACD Level (12, 26)"`, `"5min"`
Rejects: `"<script>"`, `"key;drop"`, null bytes, keys >128 chars

---

## WebSocket Event Models (Current)

All `type` fields use `Literal[...]` — full discriminator type safety:

```python
class WsConnectedEvent(BaseModel):
    type: Literal["connected"] = "connected"
    client_id: str
    ts: int

class WsErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str
    ts: int

class WsPingEvent(BaseModel):
    type: Literal["ping"] = "ping"
    ts: int
```

The `WebSocketManager` uses `_push_model(client_id, model)` which calls `model.model_dump()` before queuing — every emitted event is validated against its schema.

---

## Cross-Package Alignment (Current)

| TypeScript type | Python model | Status |
|---|---|---|
| `TradeRecord` (20 fields) | `TradeRecord` (20 fields) | ✅ Aligned |
| `ParametersConfig` | `ParametersConfig` | ✅ Aligned |
| `IndicatorsConfig` | `IndicatorsConfig` | ✅ Aligned |
| `WsConnectedEvent` | `WsConnectedEvent` | ✅ Aligned |
| `WsLogEvent` | `WsLogEvent` | ✅ Aligned |
| `WsBotCreatedEvent` | `WsBotCreatedEvent` | ✅ Aligned |
| `WsBotRemovedEvent` | `WsBotRemovedEvent` | ✅ Aligned |
| `WsErrorEvent` | `WsErrorEvent` | ✅ Aligned |
| `WsPingEvent` | `WsPingEvent` | ✅ Aligned |
| `WsTicketResponse` | `WsTicketResponse` | ✅ Aligned |
| `WsCommand` union | ❌ No Python model | ℹ️ Inbound commands validated by regex in manager |

CI pipeline runs `tsc --noEmit --strict` on `shared/types/api.ts` on every push.

---

## Remaining Minor Items

| # | Item | Status |
|---|---|---|
| `timestamp` as `str` not `datetime` | ℹ️ Acceptable — format set by bot layer |
| `position` not `Literal["LONG","SHORT"]` | ℹ️ Low priority |
| No `Field(gt=0)` on price fields | ℹ️ Low priority |
| No `Field(description=...)` | ℹ️ Low priority |
| `BotActionRequest` / `BotStatusResponse` unused | ℹ️ Kept for future use |

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 03_
_Previous: [Prompt 02 — Endpoints](../endpoints/02-api-endpoints-design.md)_
_Next: [Prompt 04 — Security](../security/04-authentication-security.md)_
