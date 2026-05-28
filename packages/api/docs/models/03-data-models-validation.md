# Data Models & Validation Review

**Prompt ID:** 03-API-MODELS  
**Package:** `packages/api`  
**Output:** `docs/models/03-data-models-validation.md`  
**Reviewed:** July 2025  
**Status:** Complete

---

## Executive Summary

All API models are defined in a single file (`src/models/schemas.py`) using Pydantic v2 correctly throughout. The model set is lean and purposeful — 17 models covering bot lifecycle, config, WebSocket events, and generic responses. The cross-package contract between `schemas.py` (Python) and `shared/types/api.ts` (TypeScript) is well-maintained and accurate, with one notable gap: the TypeScript `WsCommand` union does not include a `stop` command, while the Python WebSocket handler accepts `{"key": "stop"}`. The most significant validation gap is `TradeRecord`: it is a response-only model that accepts any string for `timestamp` and any float for financial fields, with no bounds, sign, or format constraints. Since `TradeRecord` is populated directly from SQLite rows via `SonarftHelpers._async_query()`, the absence of validation means malformed database rows are silently forwarded to clients. The config models (`ClientParametersConfig`, `IndicatorsConfig`) have solid key-safety validation but are structurally shallow — they do not validate the *values* of the `exchanges`, `symbols`, `periods`, `oscillators`, or `movingaverages` dicts beyond confirming they are `dict[str, bool]`.

---

## Model Inventory

| Model | Purpose | Used By | Field Count | Request | Response |
|---|---|---|---|---|---|
| `BotCreateResponse` | Bot creation result | `clients.py`, `bots.py` | 1 | — | ✅ |
| `BotListResponse` | List of bot IDs | `clients.py`, `bots.py` | 1 | — | ✅ |
| `TradeRecord` | Single order/trade row | `clients.py`, `bots.py` | 20 | — | ✅ |
| `ClientParametersConfig` | Client trading parameters | `clients.py`, `config.py` | 4 | ✅ | ✅ |
| `IndicatorsConfig` | Client indicator settings | `clients.py`, `config.py` | 4 | ✅ | ✅ |
| `WsBaseEvent` | Base WS event | All WS event models | 1 | — | ✅ |
| `WsConnectedEvent` | Session established | `manager.py` | 3 | — | ✅ |
| `WsLogEvent` | Bot log line | `manager.py` (via dict) | 4 | — | ✅ |
| `WsBotCreatedEvent` | Bot created lifecycle | `manager.py` | 3 | — | ✅ |
| `WsBotRemovedEvent` | Bot removed lifecycle | `manager.py` | 3 | — | ✅ |
| `WsBotStoppedEvent` | Bot stopped lifecycle | `manager.py` | 3 | — | ✅ |
| `WsOrderSuccessEvent` | Order filled signal | `manager.py` (via dict) | 2 | — | ✅ |
| `WsTradeSuccessEvent` | Trade completed signal | `manager.py` (via dict) | 2 | — | ✅ |
| `WsErrorEvent` | Command error | `manager.py` | 3 | — | ✅ |
| `WsPingEvent` | Keepalive | `manager.py` | 2 | — | ✅ |
| `WsTicketResponse` | WS auth ticket | `ws_ticket.py` | 2 | — | ✅ |
| `MessageResponse` | Generic success message | All mutation endpoints | 1 | — | ✅ |
| `HealthResponse` | Health check | `health.py` | 2 | — | ✅ |

---

## Model Relationships Diagram

```mermaid
graph TD
    subgraph "Bot Lifecycle"
        BLR[BotListResponse\nbotids: list[str]]
        BCR[BotCreateResponse\nbotid: str]
    end

    subgraph "Trade History"
        TR[TradeRecord\n20 fields]
    end

    subgraph "Configuration — Request + Response"
        CPC[ClientParametersConfig\nversion, exchanges, symbols, strategy]
        IC[IndicatorsConfig\nversion, periods, oscillators, movingaverages]
    end

    subgraph "WebSocket Events — Server → Client"
        WBE[WsBaseEvent\nts: int]
        WCE[WsConnectedEvent] --> WBE
        WLE[WsLogEvent] --> WBE
        WBCE[WsBotCreatedEvent] --> WBE
        WBRE[WsBotRemovedEvent] --> WBE
        WBSE[WsBotStoppedEvent] --> WBE
        WOSE[WsOrderSuccessEvent] --> WBE
        WTSE[WsTradeSuccessEvent] --> WBE
        WEE[WsErrorEvent] --> WBE
        WPE[WsPingEvent] --> WBE
    end

    subgraph "Infrastructure"
        MR[MessageResponse\nmessage: str]
        HR[HealthResponse\nstatus, version]
        WTR[WsTicketResponse\nticket, ttl_seconds]
    end

    subgraph "Endpoints"
        CL[clients.py]
        BO[bots.py]
        CF[config.py]
        HE[health.py]
        WS[websocket.py]
        TK[ws_ticket.py]
    end

    CL --> BLR & BCR & TR & CPC & IC & MR
    BO --> BLR & BCR & TR & MR
    CF --> CPC & IC & MR
    HE --> HR
    WS --> WCE & WLE & WBCE & WBRE & WBSE & WEE & WPE
    TK --> WTR
```

---

## 1. Pydantic V2 Compliance

| Feature | Status | Detail |
|---|---|---|
| `BaseModel` subclassing | ✅ | All models use `pydantic.BaseModel` |
| `@field_validator` (v2 style) | ✅ | Used in `ClientParametersConfig` and `IndicatorsConfig` |
| `@model_validator` | ❌ Not used | No cross-field validation in API models (used correctly in bot's `config_schemas.py`) |
| `ConfigDict` | ✅ Partial | `TradeRecord` uses `ConfigDict(extra="ignore")` — others use default |
| `Field()` with constraints | ✅ Partial | Used in `ClientParametersConfig.version` (`ge=1`); absent from `TradeRecord` |
| `model_dump()` | ✅ | Used in `config_service.py` for serialisation |
| `Literal` types | ✅ | `strategy`, `type` discriminators on all WS events |
| Aliases | ❌ Not used | No field aliases — not needed given consistent naming |
| `model_config` inheritance | ❌ | `WsBaseEvent` subclasses do not inherit a shared `ConfigDict` |

All validators use the correct v2 `@classmethod` + `@field_validator` pattern. No v1 `@validator` decorators are present.

---

## 2. Field-by-Field Validation Audit

### `TradeRecord` (`schemas.py:22-42`)

The most validation-sparse model in the codebase. It is populated from raw SQLite rows and forwarded directly to clients.

| Field | Type | Constraints | Assessment |
|---|---|---|---|
| `timestamp` | `str` | None | ⚠️ No format validation — accepts any string |
| `position` | `str` | None | ⚠️ Should be `Literal["LONG", "SHORT"]` |
| `base` | `str` | None | ⚠️ No min_length |
| `quote` | `str` | None | ⚠️ No min_length |
| `buy_exchange` | `str` | None | ⚠️ No min_length |
| `sell_exchange` | `str` | None | ⚠️ No min_length |
| `buy_price` | `float` | None | ⚠️ No `gt=0` — negative price is nonsensical |
| `sell_price` | `float` | None | ⚠️ No `gt=0` |
| `buy_trade_amount` | `float` | None | ⚠️ No `gt=0` |
| `sell_trade_amount` | `float` | None | ⚠️ No `gt=0` |
| `executed_amount` | `float` | None | ⚠️ No `ge=0` |
| `buy_value` | `float` | None | ⚠️ No `ge=0` |
| `sell_value` | `float` | None | ⚠️ No `ge=0` |
| `buy_fee_rate` | `float` | None | ⚠️ No `ge=0, lt=1` |
| `sell_fee_rate` | `float` | None | ⚠️ No `ge=0, lt=1` |
| `buy_fee_base` | `float` | None | ⚠️ No `ge=0` |
| `buy_fee_quote` | `float` | None | ⚠️ No `ge=0` |
| `sell_fee_quote` | `float` | None | ⚠️ No `ge=0` |
| `profit` | `float` | None | ✅ Can legitimately be negative |
| `profit_percentage` | `float` | None | ✅ Can legitimately be negative |

`ConfigDict(extra="ignore")` is correctly set — extra SQLite columns (e.g. `botid`, `rowid`) are silently dropped. This is the right behaviour for a response model populated from a wider database row.

### `ClientParametersConfig` (`schemas.py:72-88`)

| Field | Type | Constraints | Assessment |
|---|---|---|---|
| `version` | `int` | `ge=1` | ✅ |
| `exchanges` | `dict[str, bool]` | Key regex + max 50 entries | ✅ Keys validated; values are always `bool` |
| `symbols` | `dict[str, bool]` | Key regex + max 50 entries | ✅ |
| `strategy` | `Literal["arbitrage", "market_making"]` | Enum | ✅ |

**Gap:** The `exchanges` and `symbols` dicts validate key format but not key *content*. A client can submit `{"exchanges": {"NotARealExchange": true}}` and it will be accepted and written to disk. The bot will then attempt to connect to a non-existent exchange at startup.

**Gap:** No `@model_validator` to check that at least one exchange and one symbol are enabled (`True`) before writing. An all-`False` config is valid per the schema but will cause the bot to find no trading opportunities.

### `IndicatorsConfig` (`schemas.py:92-110`)

| Field | Type | Constraints | Assessment |
|---|---|---|---|
| `version` | `int` | `ge=1` | ✅ |
| `periods` | `dict[str, bool]` | Key regex + max 50 entries | ✅ |
| `oscillators` | `dict[str, bool]` | Key regex + max 50 entries | ✅ |
| `movingaverages` | `dict[str, bool]` | Key regex + max 50 entries | ✅ |

Same gap as `ClientParametersConfig`: key content is not validated against a known allowlist of valid indicator names.

### `_CONFIG_KEY_RE` regex (`schemas.py:50`)

```python
_CONFIG_KEY_RE = re.compile(r'^[\w\s/(). %,:-]{1,128}$')
```

This regex allows: word chars, spaces, `/().,:%- `. It correctly blocks `<script>`, null bytes, and path traversal sequences. However, it also allows some characters that could be problematic in certain contexts:

- `:` — allowed, could appear in `"key:value"` style injection attempts in some downstream parsers
- `%` — allowed for percent-encoded values like `%20`, though this is intentional for indicator names like `"Stochastic %K (14, 3, 3)"`

The regex is fit for purpose given the documented use case.

### WebSocket event models (`schemas.py:114-162`)

All WS event models use `Literal` type discriminators on the `type` field, which is the correct Pydantic v2 pattern for discriminated unions. The `ts` field is `int` (Unix timestamp in seconds) — consistent across all events.

`WsLogEvent.level` is `Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]` — correctly expanded from the original `INFO`-only version to match Python's full logging level set.

`WsBotCreatedEvent.botid` and `WsBotRemovedEvent.botid` are `str | None`. This is correct — creation can fail (returning `None` botid) and the event is still emitted. `WsBotStoppedEvent.botid` is `str` (non-optional) — correct, since stop is always called with a known botid.

---

## 3. Cross-Package Model Alignment

### `schemas.py` (Python) vs `shared/types/api.ts` (TypeScript)

| Python Model | TypeScript Interface | Aligned? | Notes |
|---|---|---|---|
| `TradeRecord` | `TradeRecord` | ✅ | All 20 fields match exactly |
| `ClientParametersConfig` | `ParametersConfig` | ✅ | Fields match; TS name differs (no `Client` prefix) |
| `IndicatorsConfig` | `IndicatorsConfig` | ✅ | Exact match |
| `BotListResponse` | `BotListResponse` | ✅ | Exact match |
| `BotCreateResponse` | `BotCreateResponse` | ✅ | Exact match |
| `MessageResponse` | `MessageResponse` | ✅ | Exact match |
| `HealthResponse` | `HealthResponse` | ✅ | Exact match |
| `WsTicketResponse` | `WsTicketResponse` | ✅ | Exact match |
| `WsBaseEvent` | `WsBaseEvent` | ✅ | `ts: int` / `ts: number` — compatible |
| `WsConnectedEvent` | `WsConnectedEvent` | ✅ | Exact match |
| `WsLogEvent` | `WsLogEvent` | ✅ | Level literals match |
| `WsBotCreatedEvent` | `WsBotCreatedEvent` | ✅ | `botid: str \| None` / `botid: string \| null` — compatible |
| `WsBotRemovedEvent` | `WsBotRemovedEvent` | ✅ | Exact match |
| `WsBotStoppedEvent` | `WsBotStoppedEvent` | ✅ | Exact match |
| `WsOrderSuccessEvent` | `WsOrderSuccessEvent` | ✅ | Exact match |
| `WsTradeSuccessEvent` | `WsTradeSuccessEvent` | ✅ | Exact match |
| `WsErrorEvent` | `WsErrorEvent` | ✅ | Exact match |
| `WsPingEvent` | `WsPingEvent` | ✅ | Exact match |

### WebSocket command contract gap

The TypeScript `WsCommand` union (`api.ts:130-145`) defines four commands: `create`, `run`, `remove`, `set_simulation`. The Python `_receive_loop` in `manager.py` handles five: `create`, `run`, `remove`, `stop`, `set_simulation`.

The `stop` command is **missing from the TypeScript contract**. The web frontend cannot issue a `stop` command via the typed `WsCommand` union without a type assertion. This is a contract gap — the Python handler accepts it, but the TypeScript types do not expose it.

### `schemas.py` vs `packages/bot/models.py` (`Trade` dataclass)

The `Trade` dataclass in `models.py` has 27 fields (19 core + 8 optional indicator fields). `TradeRecord` in `schemas.py` has 20 fields — the 19 core fields plus `timestamp`. The 8 indicator fields (`market_direction_buy`, `market_rsi_buy`, etc.) are internal to the bot and are correctly absent from the API response model. `ConfigDict(extra="ignore")` handles any additional fields that might appear in the SQLite row.

### `ClientParametersConfig` vs `packages/bot/config_schemas.py` (`ParametersConfig`)

These are intentionally different models serving different purposes:

| Aspect | `ClientParametersConfig` (API) | `ParametersConfig` (Bot) |
|---|---|---|
| Purpose | UI config — which exchanges/symbols are enabled | Trading engine config — numeric thresholds |
| Fields | `exchanges`, `symbols`, `strategy`, `version` | 18 numeric/flag trading parameters |
| Validation | Key format regex | Numeric bounds, cross-field validators |
| Written by | API `ConfigService` | Read-only at bot startup |

These are not the same config and are not expected to be aligned. The API manages the UI-facing config; the bot manages the trading-parameter config. This separation is correct.

---

## 4. Serialisation Analysis

| Model | Serialisation Method | Notes |
|---|---|---|
| All response models | FastAPI auto-serialisation via `ORJSONResponse` | ✅ Fast, correct |
| `ClientParametersConfig` | `model_dump()` in `config_service.py:update_parameters` | ✅ Correct v2 method |
| `IndicatorsConfig` | `model_dump()` in `config_service.py:update_indicators` | ✅ |
| WS event models | `model_dump()` in `manager.py` + `orjson.dumps()` | ✅ |
| WS log/order/trade events | Raw `dict` constructed in `WsLogHandler.emit()` | ⚠️ Not using Pydantic models — see below |

`WsLogEvent`, `WsOrderSuccessEvent`, and `WsTradeSuccessEvent` are defined as Pydantic models in `schemas.py` but are **not used** when emitting events in `WsLogHandler.emit()` (`manager.py:62-74`). Instead, raw dicts are constructed and pushed to the queue directly:

```python
# manager.py:65-70 — raw dict, not WsLogEvent model
self._queue.put_nowait({
    "type": "log",
    "level": record.levelname,
    "message": msg,
    "ts": int(record.created),
})
```

This means:
1. The `WsLogEvent` Pydantic model is defined but never instantiated in the hot path
2. The `level` field is not validated against the `Literal` constraint at emit time
3. If the model's field names ever change, the raw dict will silently diverge

---

## 5. Type Annotation Completeness

All models have complete type annotations. No `Any` types are used. Optional fields use `str | None` (Python 3.10+ union syntax) consistently.

One minor inconsistency: `WsTicketResponse.ttl_seconds` has a default value of `30` in the model definition, but the `issue_ws_ticket` endpoint in `ws_ticket.py` also hardcodes `ttl_seconds=30` when constructing the response. The actual TTL is `_TICKET_TTL_SECONDS = 30` in `tickets.py`. Three places define the same constant — they are currently in sync but could drift.

---

## Concerns & Recommendations

### High

| # | Concern | Location | Detail |
|---|---|---|---|
| H1 | **`TradeRecord` financial fields have no bounds validation** | `schemas.py:27-41` | `buy_price`, `sell_price`, `buy_trade_amount`, etc. accept any float including negative values and `NaN`/`Inf`. A corrupted SQLite row with a negative price would be forwarded to the frontend without error. |

### Medium

| # | Concern | Location | Detail |
|---|---|---|---|
| M1 | **`WsLogEvent` model is not used in the hot path** | `manager.py:62-74` | `WsLogHandler.emit()` constructs raw dicts instead of `WsLogEvent` instances. The model exists but provides no runtime validation for the most frequent event type. |
| M2 | **`stop` command missing from TypeScript `WsCommand` union** | `shared/types/api.ts:130` | The Python handler accepts `{"key": "stop"}` but the TS type contract does not include it. Frontend code issuing a stop command must bypass the type system. |
| M3 | **`ClientParametersConfig` does not validate exchange/symbol values against a known allowlist** | `schemas.py:72-88` | Any string key passes validation. A client can write `{"exchanges": {"FakeExchange": true}}` and the bot will attempt to connect to it at startup. |
| M4 | **`ttl_seconds` constant is defined in three places** | `tickets.py:8`, `schemas.py:153`, `ws_ticket.py:30` | `_TICKET_TTL_SECONDS`, `WsTicketResponse.ttl_seconds` default, and the `WsTicketResponse(ttl_seconds=30)` constructor call. A change to the TTL requires three edits. |

### Low

| # | Concern | Location | Detail |
|---|---|---|---|
| L1 | **`TradeRecord.position` should be a `Literal`** | `schemas.py:24` | Valid values are `"LONG"` and `"SHORT"`. Using `str` allows any value from the database. |
| L2 | **`TradeRecord.timestamp` has no format constraint** | `schemas.py:23` | As noted in Prompt 02 — two different formats appear in test fixtures. |
| L3 | **`WsBaseEvent` subclasses do not share a `ConfigDict`** | `schemas.py:114-162` | No `model_config` is set on `WsBaseEvent` or its subclasses. If `extra="forbid"` were ever needed (e.g. to catch protocol drift), it would need to be added to each subclass individually. |
| L4 | **`HealthResponse.version` is hardcoded** | `schemas.py:163` | `version: str = "1.0.0"` — not read from `Settings.api_version`. Noted in Prompt 01 as well. |

---

## Recommendations

### Priority 1

**R1 (H1): Add basic bounds to `TradeRecord` financial fields**

```python
class TradeRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: str
    position: Literal["LONG", "SHORT"]
    base: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    buy_exchange: str = Field(min_length=1)
    sell_exchange: str = Field(min_length=1)
    buy_price: float = Field(gt=0)
    sell_price: float = Field(gt=0)
    buy_trade_amount: float = Field(gt=0)
    sell_trade_amount: float = Field(gt=0)
    executed_amount: float = Field(ge=0)
    buy_value: float = Field(ge=0)
    sell_value: float = Field(ge=0)
    buy_fee_rate: float = Field(ge=0, lt=1)
    sell_fee_rate: float = Field(ge=0, lt=1)
    buy_fee_base: float = Field(ge=0)
    buy_fee_quote: float = Field(ge=0)
    sell_fee_quote: float = Field(ge=0)
    profit: float
    profit_percentage: float
```

---

### Priority 2

**R2 (M1): Use `WsLogEvent` model in `WsLogHandler.emit()`**

```python
# manager.py — replace raw dict construction
from ..models.schemas import WsLogEvent

def emit(self, record: logging.LogRecord) -> None:
    try:
        event = WsLogEvent(
            ts=int(record.created),
            level=record.levelname,  # type: ignore[arg-type] — validated by Literal
            message=self.format(record),
        )
        self._queue.put_nowait(event.model_dump())
        ...
```

**R3 (M2): Add `WsStopCommand` to `shared/types/api.ts`**

```typescript
export interface WsStopCommand {
    type: "keypress";
    key: "stop";
    botid: string;
}

export type WsCommand =
    | WsCreateCommand
    | WsRunCommand
    | WsStopCommand      // add this
    | WsRemoveCommand
    | WsSetSimulationCommand;
```

**R4 (M4): Centralise the ticket TTL constant**

```python
# websocket/tickets.py — single source of truth
TICKET_TTL_SECONDS: int = 30

# ws_ticket.py — read from tickets module
from ....websocket.tickets import TICKET_TTL_SECONDS, get_ticket_store

return WsTicketResponse(ticket=ticket, ttl_seconds=TICKET_TTL_SECONDS)

# schemas.py — remove hardcoded default or import constant
```

---

### Priority 3

**R5 (M3): Add an exchange/symbol allowlist validator to `ClientParametersConfig`**

This requires the API to know the valid exchange and symbol names — either loaded from `sonarftdata/config_exchanges.json` and `config_symbols.json` at startup, or passed as a dependency. A simpler approach is a format-only check (e.g. `BTC/USDT` pattern for symbols) rather than a full allowlist.

**R6 (L3): Add shared `ConfigDict` to `WsBaseEvent`**

```python
class WsBaseEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ts: int
```

Subclasses inherit the config, ensuring consistent behaviour if the policy ever changes.

---

_Generated by Amazon Q Developer — SonarFT API Code Review Prompt Suite, Prompt 03_
