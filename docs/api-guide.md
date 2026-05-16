# API Guide

The SonarFT API is a FastAPI application serving REST endpoints and a WebSocket stream. All endpoints are prefixed with `/api/v1`.

Interactive documentation is available at: `http://localhost:8000/api/v1/docs`

---

## Base URL

```
http://localhost:8000/api/v1        # development
https://your-domain.com/api/v1     # production
```

---

## Authentication

The API supports two authentication modes. If neither is configured, auth is disabled (development only).

### Mode 1: Netlify Identity JWT

Set `NETLIFY_SITE_URL` in `packages/api/.env`. The API fetches the JWKS from `{NETLIFY_SITE_URL}/.netlify/identity/keys` and validates RS256 JWTs.

In this mode, the client identity (`client_id`) is derived from the JWT `sub` claim. The `client_id` query parameter is ignored — identity comes from the token.

```bash
curl -H "Authorization: Bearer <netlify-jwt>" \
     http://localhost:8000/api/v1/clients/me/bots
```

### Mode 2: Static Token

Set `SONARFT_API_TOKEN` in `packages/api/.env`. All requests must include this token as a Bearer token. Comparison uses `hmac.compare_digest` to prevent timing attacks.

In this mode, `client_id` must be provided as a query parameter.

```bash
curl -H "Authorization: Bearer your-secret-token" \
     "http://localhost:8000/api/v1/clients/my-client/bots"
```

### Mode 3: Auth Disabled (Development)

When neither `NETLIFY_SITE_URL` nor `SONARFT_API_TOKEN` is set, all endpoints are publicly accessible. The API logs a prominent warning at startup:

```
⚠️  AUTH DISABLED — neither NETLIFY_SITE_URL nor SONARFT_API_TOKEN is set.
```

> **Never deploy to production with auth disabled.**

---

## REST Endpoints

### Health

#### `GET /health`

Returns the API health status.

**Response:**
```json
{
    "status": "ok",
    "version": "1.0.0"
}
```

---

### Bots (Canonical Paths)

#### `GET /clients/{client_id}/bots`

List all bot IDs for a client.

**Response:**
```json
{
    "botids": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

#### `POST /clients/{client_id}/bots`

Create a new bot for a client.

**Request body (optional):**
```json
{
    "config": "config_1",
    "library": "ccxtpro"
}
```

| Field | Default | Description |
|---|---|---|
| `config` | `"config_1"` | Named configuration set from `config.json` |
| `library` | `"ccxtpro"` | Exchange API library: `"ccxtpro"` (WebSocket) or `"ccxt"` (REST) |

**Response:**
```json
{
    "botid": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error responses:**
- `422` — Invalid configuration or validation failure
- `429` — Bot limit exceeded (`MAX_BOTS_PER_CLIENT`)

#### `POST /clients/{client_id}/bots/{botid}/run`

Start a previously created bot.

**Response:**
```json
{
    "message": "Bot started"
}
```

#### `POST /clients/{client_id}/bots/{botid}/stop`

Stop a running bot without removing it. The bot can be restarted.

**Response:**
```json
{
    "message": "Bot stopped"
}
```

#### `DELETE /clients/{client_id}/bots/{botid}`

Stop and remove a bot. Cleans up the registry file.

**Response:**
```json
{
    "message": "Bot removed"
}
```

#### `GET /clients/{client_id}/bots/{botid}/orders`

Retrieve order history for a bot.

**Response:**
```json
[
    {
        "timestamp": "2024-01-15T10:30:00Z",
        "position": "LONG",
        "base": "ETH",
        "quote": "USDT",
        "buy_exchange": "okx",
        "sell_exchange": "binance",
        "buy_price": 2450.50,
        "sell_price": 2451.20,
        "buy_trade_amount": 0.01,
        "sell_trade_amount": 0.01,
        "executed_amount": 0.01,
        "buy_value": 24.505,
        "sell_value": 24.512,
        "buy_fee_rate": 0.001,
        "sell_fee_rate": 0.001,
        "buy_fee_base": 0.00001,
        "buy_fee_quote": 0.02451,
        "sell_fee_quote": 0.02451,
        "profit": 0.00598,
        "profit_percentage": 0.000244
    }
]
```

#### `GET /clients/{client_id}/bots/{botid}/trades`

Retrieve trade history for a bot. Same schema as orders.

---

### Parameters

#### `GET /clients/{client_id}/parameters`

Get the current parameters configuration for a client.

**Response:**
```json
{
    "version": 1,
    "exchanges": { "okx": true, "binance": false },
    "symbols": { "ETH/USDT": true, "BTC/USDT": false },
    "strategy": "arbitrage"
}
```

#### `PUT /clients/{client_id}/parameters`

Update parameters for a client. Changes are persisted to `sonarftdata/config/{client_id}_parameters.json` and hot-reloaded into all running bots for that client.

**Request body:**
```json
{
    "version": 1,
    "exchanges": { "okx": true, "binance": true },
    "symbols": { "ETH/USDT": true },
    "strategy": "market_making"
}
```

**Validation rules:**
- `strategy` must be `"arbitrage"` or `"market_making"`
- All keys in `exchanges` and `symbols` must match `^[\w\s/(). %,:-]{1,128}$`
- Maximum 50 entries per dict

**Response:**
```json
{
    "message": "Parameters updated"
}
```

---

### Indicators

#### `GET /clients/{client_id}/indicators`

Get the current indicators configuration for a client.

**Response:**
```json
{
    "version": 1,
    "periods": { "14": true, "21": false },
    "oscillators": { "RSI": true, "MACD": false },
    "movingaverages": { "SMA": true, "EMA": false }
}
```

#### `PUT /clients/{client_id}/indicators`

Update indicators for a client.

**Request body:**
```json
{
    "version": 1,
    "periods": { "14": true },
    "oscillators": { "RSI": true, "Stochastic RSI": true },
    "movingaverages": { "SMA": true }
}
```

---

### Legacy Endpoints (Deprecated)

These endpoints remain functional for backward compatibility but new integrations should use the canonical paths above.

| Method | Path | Canonical Equivalent |
|---|---|---|
| `GET` | `/bots?client_id=` | `GET /clients/{id}/bots` |
| `POST` | `/bots?client_id=` | `POST /clients/{id}/bots` |
| `GET` | `/parameters/defaults` | — |
| `GET` | `/parameters?client_id=` | `GET /clients/{id}/parameters` |
| `PUT` | `/parameters?client_id=` | `PUT /clients/{id}/parameters` |
| `GET` | `/indicators/defaults` | — |
| `GET` | `/indicators?client_id=` | `GET /clients/{id}/indicators` |
| `PUT` | `/indicators?client_id=` | `PUT /clients/{id}/indicators` |

---

## WebSocket

### Ticket Authentication

The WebSocket connection uses a single-use ticket to keep the JWT out of server logs and browser history.

**Step 1: Get a ticket (30-second TTL)**

```bash
curl -X POST \
     -H "Authorization: Bearer <jwt>" \
     http://localhost:8000/api/v1/ws/ticket
```

**Response:**
```json
{
    "ticket": "dGhpcyBpcyBhIHRlc3Q",
    "ttl_seconds": 30
}
```

**Step 2: Connect with the ticket**

```
ws://localhost:8000/api/v1/ws/{clientId}?ticket=dGhpcyBpcyBhIHRlc3Q
```

The ticket is consumed on the first connection attempt. If the connection fails, a new ticket must be obtained.

### Client → Server Commands

All commands use the `keypress` type:

**Create a bot:**
```json
{ "type": "keypress", "key": "create" }
```

**Run a bot:**
```json
{ "type": "keypress", "key": "run", "botid": "550e8400-e29b-41d4-a716-446655440000" }
```

**Stop a bot:**
```json
{ "type": "keypress", "key": "stop", "botid": "550e8400-e29b-41d4-a716-446655440000" }
```

**Remove a bot:**
```json
{ "type": "keypress", "key": "remove", "botid": "550e8400-e29b-41d4-a716-446655440000" }
```

**Toggle simulation mode:**
```json
{ "type": "keypress", "key": "set_simulation", "botid": "550e8400-...", "value": false }
```

> **Warning:** Setting `value: false` switches to live trading. This requires `SONARFT_ALLOW_LIVE=true` on the server. The frontend should display an explicit confirmation modal before sending this command.

### Server → Client Events

**Connection established:**
```json
{ "type": "connected", "client_id": "user@example.com", "ts": 1705312200 }
```

**Log message:**
```json
{ "type": "log", "level": "INFO", "message": "Bot warming up — indicators need ~45 candles", "ts": 1705312201 }
```

Log levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Bot created:**
```json
{ "type": "bot_created", "botid": "550e8400-e29b-41d4-a716-446655440000", "ts": 1705312202 }
```

**Bot stopped:**
```json
{ "type": "bot_stopped", "botid": "550e8400-e29b-41d4-a716-446655440000", "ts": 1705312210 }
```

**Bot removed:**
```json
{ "type": "bot_removed", "botid": "550e8400-e29b-41d4-a716-446655440000", "ts": 1705312215 }
```

**Order placed successfully:**
```json
{ "type": "order_success", "ts": 1705312220 }
```

**Trade completed successfully:**
```json
{ "type": "trade_success", "ts": 1705312221 }
```

**Error:**
```json
{ "type": "error", "message": "Exchange connection failed", "ts": 1705312225 }
```

**Ping (keepalive):**
```json
{ "type": "ping", "ts": 1705312230 }
```

The server sends a ping every 30 seconds. The frontend closes the connection if no message is received within 60 seconds, triggering the reconnect loop.

---

## Rate Limiting

Rate limiting is implemented via `slowapi`. Default limits apply per IP address. Exceeding the limit returns:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

---

## Error Responses

All error responses follow a consistent format:

```json
{
    "detail": "Bot not found: 550e8400-e29b-41d4-a716-446655440000"
}
```

| Status | Condition |
|---|---|
| `400` | Bad request — missing required parameter |
| `401` | Unauthorized — missing or invalid token |
| `404` | Not found — bot or config does not exist |
| `422` | Validation error — invalid request body |
| `429` | Rate limit exceeded or bot limit exceeded |
| `500` | Internal server error |

---

## Request IDs

Every request and response includes an `X-Request-ID` header. If the client sends this header, the value is propagated. Otherwise, a UUID is generated. All log lines within a request include the request ID, enabling end-to-end tracing:

```
2024-01-15 10:30:00 INFO [a1b2c3d4-...] sonarft.access — ACCESS POST /api/v1/clients/user/bots -> 200 (45.2ms)
```

To correlate a client error with server logs, include `X-Request-ID` in your requests:

```bash
curl -H "X-Request-ID: my-trace-id-001" \
     -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/v1/clients/user/bots
```

---

## Shared Types

All request and response schemas are defined in two places that must stay in sync:

| File | Language | Used by |
|---|---|---|
| `shared/types/api.ts` | TypeScript | `packages/web` |
| `packages/api/src/models/schemas.py` | Python (Pydantic) | `packages/api` |

The TypeScript types are the source of truth. When modifying the API contract, update `shared/types/api.ts` first, then update `schemas.py` to match.
