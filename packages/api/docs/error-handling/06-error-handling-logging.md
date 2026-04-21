# Prompt 06 — Error Handling, Logging & Observability Review

**Generated:** July 2025 | **Updated:** July 2025 (post-implementation)
**Reviewer:** Amazon Q (Senior Python / Observability / Async Systems)
**Status:** ✅ All high findings resolved

---

## Executive Summary

All critical observability gaps have been resolved. `generic_error_handler` now logs full tracebacks with method, path, and request ID. `ConfigService` has try/except on all 6 methods with correct 404/500 responses. `BotService.create_bot` detects `None` returns from `BotManager`. Auth failures are logged with source IP. `Settings.log_level` is applied to `basicConfig`. Request IDs propagate through the full async call chain via `ContextVar`. The bot package's dead `BotRunError` catch has been removed.

---

## Logging Configuration (Current)

```python
# main.py
logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(request_id)s] %(name)s — %(message)s",
)
for _h in logging.root.handlers:
    _h.addFilter(RequestIdFilter())
```

- `LOG_LEVEL` env var now controls runtime log level ✅
- Every log line includes `[<request-id>]` ✅
- `RequestIdFilter` injects `request_id` from `ContextVar` ✅

---

## Request ID Middleware (Implemented)

```python
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response
```

- Client-supplied `X-Request-ID` is echoed back ✅
- UUID4 generated if not supplied ✅
- `ContextVar` propagates through the full async call chain ✅
- `X-Request-ID` returned in every response header ✅

---

## Error Handler (Current)

```python
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from .context import request_id_var
    _logger.exception(
        "Unhandled exception [%s %s] request_id=%s: %s",
        request.method, request.url.path, request_id_var.get("-"), exc,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

Full traceback logged at ERROR level. Request ID included. Generic message returned to client.

---

## ConfigService Error Handling (Implemented)

All 6 methods now have try/except:

```python
async def get_parameters(self, client_id: str) -> ParametersConfig:
    path = _client_path(self._data_dir, client_id, "parameters")
    try:
        data = await asyncio.to_thread(_read_json, path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Parameters not found for client: {client_id}")
    except Exception as exc:
        _logger.exception("Failed to read parameters for %s: %s", client_id, exc)
        raise HTTPException(status_code=500, detail="Failed to read parameters") from exc
    return ParametersConfig(**data)
```

- `FileNotFoundError` → 404 ✅
- Other exceptions → 500 with traceback log ✅
- Write failures → 500 with traceback log ✅

---

## Auth Failure Logging (Implemented)

```python
# core/security.py
_logger.warning("Auth failure from %s — missing or invalid token", _client_ip(request))
_logger.warning("Auth failure from %s — invalid JWT", ip)
_logger.warning("Auth failure from %s — invalid static token", ip)
```

`_client_ip()` reads `request.client.host` with `X-Forwarded-For` fallback for reverse-proxy deployments.

---

## Logging Coverage Matrix (Current)

| Operation | Logged | Level |
|---|---|---|
| Bot created | ✅ | INFO |
| Bot paused | ✅ | INFO |
| Bot removed | ✅ | INFO |
| Bot creation failure | ✅ | ERROR |
| Config file read failure | ✅ | EXCEPTION |
| Config file write failure | ✅ | EXCEPTION |
| JWT validation failure | ✅ | WARNING + IP |
| HTTP 401 (missing/invalid token) | ✅ | WARNING + IP |
| WebSocket auth failure (1008) | ✅ | WARNING + IP |
| WebSocket command failure | ✅ | ERROR |
| Unhandled exception (500) | ✅ | EXCEPTION + request_id |
| WS client connected | ✅ | INFO |
| WS client disconnected | ✅ | INFO |
| Queue full drop | ✅ | WARNING |

---

## Resolved Issues

| # | Original Issue | Resolution |
|---|---|---|
| 1 | `generic_error_handler` swallows exceptions | ✅ Logs full traceback with request_id |
| 2 | `ConfigService` no error handling | ✅ try/except on all 6 methods |
| 3 | `BotService.create_bot` wrong botid on failure | ✅ Raises HTTP 500 on `None` return |
| 4 | `Settings.log_level` ignored | ✅ Applied to `basicConfig` |
| 5 | No auth failure logging | ✅ WARNING with source IP |
| 6 | No request correlation | ✅ `X-Request-ID` + `ContextVar` |
| 7 | `BotRunError` dead code | ✅ Removed |
| 8 | No structured logging | ✅ `[request_id]` in every log line |

---

## Remaining Items

| Item | Status |
|---|---|
| JSON log format (for log aggregators) | ℹ️ Plain text with request_id — acceptable |
| Log rotation | ℹ️ Not configured — use OS/container log rotation |
| Audit trail for parameter changes | ✅ Already in bot: `apply_parameters` logs AUDIT |

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 06_
_Previous: [Prompt 05 — WebSocket](../websocket/05-websocket-realtime.md)_
_Next: [Prompt 07 — Database](../database/07-database-persistence.md)_
