# Testing, Quality Assurance & Test Coverage Review

**Prompt ID:** 09-API-TESTING  
**Package:** `packages/api`  
**Reviewer:** Amazon Q (Senior Python / pytest / QA)  
**Date:** July 2025  
**Status:** Complete

---

## Executive Summary

The SonarFT API has a solid unit test foundation covering all 14 REST endpoints, authentication modes, input validation, WebSocket command dispatch, and error handlers — 60+ test cases across 4 test files. The test architecture is clean: `conftest.py` provides well-structured fixtures that inject mock services into `app.state`, avoiding real bot engine or filesystem dependencies. Security testing is notably thorough — parametrised botid and client_id validation tests cover path traversal, injection, and oversized inputs. The main gaps are: the API has no CI job (only the web and bot packages run in CI); there is no coverage measurement or threshold; the integration test directory is empty; canonical `/clients/{id}/...` routes have no dedicated tests (only legacy routes are tested); and the `stop` command, `set_simulation` success path, ticket auth, and concurrent connection scenarios are untested in the WebSocket suite.

---

## 1. Test Structure & Organisation

### 1.1 Directory Layout

```
packages/api/tests/
├── conftest.py                  # Shared fixtures: app, client, mock services
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_smoke.py            # 6 tests — infrastructure smoke tests
│   ├── test_endpoints.py        # 40 tests — all 14 REST endpoints
│   ├── test_security.py         # 25 tests — auth modes, token validation, input sanitisation
│   └── test_websocket.py        # 22 tests — WS lifecycle, commands, validation, log streaming
└── integration/
    └── __init__.py              # Empty — no integration tests implemented
```

### 1.2 Framework Configuration

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

`asyncio_mode = auto` enables automatic async test detection via `pytest-asyncio`. ✅

### 1.3 Test Count Summary

| File | Tests | Focus |
|---|---|---|
| `test_smoke.py` | 6 | App startup, health endpoint, fixture wiring |
| `test_endpoints.py` | 40 | All 14 REST endpoints — status codes, schemas, errors |
| `test_security.py` | 25 | Auth modes, token validation, botid/client_id sanitisation |
| `test_websocket.py` | 22 | WS lifecycle, commands, input validation, log streaming |
| **Total** | **93** | — |

---

## 2. Unit Test Coverage

### 2.1 Coverage by Module

| Module | Estimated Coverage | Notes |
|---|---|---|
| `src/api/v1/endpoints/bots.py` | ~85% | All endpoints tested via legacy routes |
| `src/api/v1/endpoints/clients.py` | ~10% | ⚠️ No dedicated tests — canonical routes untested |
| `src/api/v1/endpoints/config.py` | ~80% | Parameters and indicators endpoints covered |
| `src/api/v1/endpoints/health.py` | ~100% | Fully covered |
| `src/api/v1/endpoints/ws_ticket.py` | ~0% | ⚠️ No tests |
| `src/core/security.py` | ~75% | Auth modes, token validation; JWT decode path mocked |
| `src/core/errors.py` | ~90% | Exception handlers tested via endpoint tests |
| `src/core/config.py` | ~60% | Settings loaded; `allowed_origins` property untested |
| `src/core/context.py` | ~100% | Tested via `X-Request-ID` header tests |
| `src/core/limiter.py` | ~0% | ⚠️ Rate limiting not tested |
| `src/services/bot_service.py` | ~30% | ⚠️ Service logic tested only through mocks |
| `src/services/config_service.py` | ~0% | ⚠️ No direct tests — always mocked |
| `src/models/schemas.py` | ~70% | Pydantic validation tested via endpoint tests |
| `src/websocket/manager.py` | ~65% | Commands, validation, log handler; gaps noted |
| `src/websocket/tickets.py` | ~0% | ⚠️ No tests |
| `src/main.py` | ~50% | App factory, middleware tested via integration |

**No coverage measurement is configured** — `pytest-cov` is in `requirements-test.txt` but no `--cov` flag or `.coveragerc` is set up. Actual percentages above are estimates from test inspection.

### 2.2 Critical Untested Paths

| Path | Risk | Why It Matters |
|---|---|---|
| `clients.py` canonical routes | High | Primary API surface — only legacy routes tested |
| `ws_ticket.py` | Medium | WS auth entry point — zero tests |
| `tickets.py` TicketStore | Medium | Single-use ticket logic — zero tests |
| `config_service.py` | Medium | File I/O, atomic writes, path traversal guard |
| `bot_service.py` service logic | Medium | Tenant isolation, bot limit enforcement |
| Rate limiting | Low | slowapi integration untested |

---

## 3. Integration Tests

### 3.1 Current State

`tests/integration/__init__.py` exists but contains no tests. There are zero integration tests.

### 3.2 What Integration Tests Should Cover

| Scenario | Priority |
|---|---|
| `ConfigService` reads/writes real JSON files | High |
| `BotService` with real `BotManager` (mocked exchanges) | High |
| `TicketStore` issue → WS connect flow | High |
| Canonical `/clients/{id}/bots` end-to-end | High |
| SQLite history query via `SonarftHelpers` | Medium |
| Rate limiting enforcement | Medium |
| Security header presence on all responses | Low |

---

## 4. Endpoint Tests

### 4.1 Coverage Matrix

| Endpoint | Tested? | Status Codes Covered | Notes |
|---|---|---|---|
| `GET /health` | ✅ | 200 | Security headers, request ID echo |
| `GET /bots` (legacy) | ✅ | 200, 400 | Missing 401 (covered in security tests) |
| `POST /bots` (legacy) | ✅ | 201, 400, 429 | — |
| `POST /bots/{id}/run` | ✅ | 200, 404, 422 | Oversized botid tested |
| `POST /bots/{id}/stop` | ✅ | 200, 404 | — |
| `DELETE /bots/{id}` | ✅ | 200, 404 | — |
| `GET /bots/{id}/orders` | ✅ | 200, 404, 422 | Pagination params, limit/offset bounds |
| `GET /bots/{id}/trades` | ✅ | 200, 404 | Pagination forwarding verified |
| `GET /parameters/defaults` | ✅ | 200, 404 | — |
| `GET /parameters` | ✅ | 200, 400, 404 | — |
| `PUT /parameters` | ✅ | 200, 400, 422 | XSS key injection tested |
| `GET /indicators/defaults` | ✅ | 200 | — |
| `GET /indicators` | ✅ | 200, 400 | — |
| `PUT /indicators` | ✅ | 200, 400, 422 | Null byte injection tested |
| `POST /ws/ticket` | ❌ | — | Zero tests |
| `GET /clients/{id}/bots` | ❌ | — | Zero tests — canonical route |
| `POST /clients/{id}/bots` | ❌ | — | Zero tests |
| `POST /clients/{id}/bots/{id}/run` | ❌ | — | Zero tests |
| `POST /clients/{id}/bots/{id}/stop` | ❌ | — | Zero tests |
| `DELETE /clients/{id}/bots/{id}` | ❌ | — | Zero tests |
| `GET /clients/{id}/bots/{id}/orders` | ❌ | — | Zero tests |
| `GET /clients/{id}/bots/{id}/trades` | ❌ | — | Zero tests |
| `GET /clients/{id}/parameters` | ❌ | — | Zero tests |
| `PUT /clients/{id}/parameters` | ❌ | — | Zero tests |
| `GET /clients/{id}/indicators` | ❌ | — | Zero tests |
| `PUT /clients/{id}/indicators` | ❌ | — | Zero tests |

### 4.2 Pagination Testing

`TestGetOrders` verifies that `limit` and `offset` are forwarded to the service:

```python
mock_bot_service.get_orders.assert_called_once_with("bot-001", "test", 50, 10)
```

Boundary validation is also tested (`limit=9999` → 422, `offset=-1` → 422). ✅

### 4.3 Error Handler Testing

`TestErrorHandlers` covers all three custom handlers:
- `BotNotFoundError` → 404 with `botid` in detail ✅
- `BotLimitExceededError` → 429 with limit in detail ✅
- `RuntimeError` (unhandled) → 500 with `"Internal server error"` ✅

---

## 5. Authentication & Security Testing

### 5.1 Auth Mode Coverage

| Auth Mode | Tested? | Tests |
|---|---|---|
| Dev mode (no auth) | ✅ | `TestDevModeAuth` — 3 tests |
| Static token — correct | ✅ | `TestStaticTokenAuth` — 5 tests |
| Static token — wrong | ✅ | `test_wrong_token_rejected` |
| Static token — missing | ✅ | `test_missing_token_rejected` |
| Static token — empty bearer | ✅ | `test_empty_bearer_rejected` |
| Netlify JWT — valid | ❌ | Not tested (requires live JWKS or full mock) |
| Netlify JWT — invalid | ✅ | `test_invalid_jwt_raises_401` (mocked) |
| Netlify JWT — missing | ✅ | `test_missing_token_with_netlify_raises_401` |
| Ticket auth (WS) | ❌ | Not tested |
| `__ticket_verified__` sentinel | ❌ | Not tested |

### 5.2 Input Validation Security Tests

`TestBotIdValidation` uses `@pytest.mark.parametrize` with 5 valid and 7 invalid botids:

```python
INVALID_BOTIDS = [
    "../etc/passwd",   # path traversal
    "bot/evil",        # path separator
    "bot evil",        # space
    "",                # empty
    "a" * 65,          # oversized
    "bot;drop",        # SQL injection attempt
    "bot<script>",     # XSS attempt
]
```

`TestClientIdSanitization` tests 7 traversal attempts plus `__proto__` prototype pollution. ✅

### 5.3 All Protected Endpoints Spot-Check

`test_all_protected_endpoints_require_token` iterates all 13 protected endpoints and asserts 401 without a token. This is a valuable regression guard. ✅

---

## 6. Error Handling Testing

### 6.1 Coverage

| Error Scenario | Tested? | Location |
|---|---|---|
| `BotNotFoundError` → 404 | ✅ | `TestErrorHandlers`, `TestRunBot`, `TestStopBot`, `TestRemoveBot` |
| `BotLimitExceededError` → 429 | ✅ | `TestErrorHandlers`, `TestCreateBot` |
| Unhandled exception → 500 | ✅ | `TestErrorHandlers.test_unhandled_exception_returns_500` |
| Pydantic 422 validation | ✅ | `TestUpdateParameters`, `TestUpdateIndicators`, `TestRunBot` |
| Missing `client_id` → 400 | ✅ | Multiple endpoint tests |
| Config file not found → 404 | ✅ | `TestGetDefaultParameters`, `TestGetParameters` |
| WS invalid JSON → error event | ✅ | `TestWebSocketInputValidation` |
| WS unknown command → error event | ✅ | `TestWebSocketInputValidation` |
| WS bot limit → error event | ✅ | `TestWebSocketCreateCommand` |
| WS handler exception → error event | ✅ | `TestWebSocketCreateCommand`, `TestWebSocketRemoveCommand` |
| WS invalid token → 1008 | ✅ | `TestWebSocketAuth` |
| Timeout scenarios | ❌ | Not tested |
| Config write failure | ❌ | Not tested |

---

## 7. WebSocket Testing

### 7.1 Coverage Matrix

| Scenario | Tested? | Location |
|---|---|---|
| Connect → `connected` event | ✅ | `TestWebSocketConnection` |
| `connected` event has `ts` field | ✅ | `test_connected_event_has_ts` |
| Invalid token → close 1008 | ✅ | `TestWebSocketAuth` |
| Dev mode — any token accepted | ✅ | `test_dev_mode_any_token_accepted` |
| `create` command → `BotManager.create_bot` called | ✅ | `TestWebSocketCreateCommand` |
| `create` at limit → error event | ✅ | `test_create_at_limit_sends_error_event` |
| `create` failure → graceful | ✅ | `test_create_failure_handled_gracefully` |
| `remove` command → `BotManager.remove_bot` called | ✅ | `TestWebSocketRemoveCommand` |
| `run` command → `BotManager.run_bot` called | ✅ | `TestWebSocketRunCommand` |
| Invalid botid → error event | ✅ | `test_invalid_botid_sends_error` |
| Missing botid → error event | ✅ | `test_missing_botid_sends_error` |
| Unknown command → error event | ✅ | `test_unknown_command_sends_error` |
| Invalid JSON → error event | ✅ | `test_invalid_json_sends_error` |
| Oversized botid → error event | ✅ | `test_oversized_botid_sends_error` |
| Log handler attached on connect | ✅ | `test_log_handler_attached_on_connect` |
| Log handler detached on disconnect | ✅ | `test_log_handler_attached_on_connect` (asserts after `with` block) |
| `stop` command | ❌ | Not tested |
| `set_simulation` success | ❌ | Not tested |
| Ticket auth path (`?ticket=`) | ❌ | Not tested |
| Existing connection displaced | ❌ | Not tested |
| Concurrent connections | ❌ | Not tested |
| Queue full / event drop | ❌ | Not tested |
| Keepalive ping | ❌ | Not tested |
| `bot_created` event delivered | ❌ | Not tested end-to-end |
| `bot_removed` event delivered | ❌ | Not tested end-to-end |

### 7.2 Timing-Dependent Tests

Tests for async command dispatch use `time.sleep(0.1)` to allow background tasks to complete:

```python
# test_websocket.py:79
ws.send_json({"key": "create"})
time.sleep(0.1)
mock_bot_service._manager.create_bot.assert_called_once_with("test-client")
```

This is a pragmatic approach for synchronous `TestClient` but is inherently flaky — on a slow CI machine, 100ms may not be enough. A more robust approach uses `pytest-asyncio` with `await asyncio.sleep(0)` to yield the event loop.

### 7.3 Log Streaming Test Gap

`test_log_event_delivered_to_client` verifies the handler is attached and accepts records but does not verify end-to-end delivery to the WebSocket client. The comment in the test acknowledges this:

```python
# Full end-to-end delivery verified in integration tests
```

But integration tests don't exist. This is the most important missing test given the `_BOT_LOGGER_NAME` bug identified in Prompt 05.

---

## 8. Database Testing

### 8.1 Current State

`ConfigService` and `SonarftHelpers` are always mocked in tests — no test exercises real file I/O or SQLite operations. The `mock_config_service` fixture returns `AsyncMock` objects for all methods.

### 8.2 What Should Be Tested

| Operation | Test Type | Priority |
|---|---|---|
| `ConfigService.get_parameters` reads real JSON | Integration | High |
| `ConfigService.update_parameters` atomic write | Integration | High |
| `ConfigService._client_path` path traversal guard | Unit | High |
| `SonarftHelpers._db_insert` + `_db_query` round-trip | Unit | Medium |
| `SonarftHelpers.purge_history` retention policy | Unit | Medium |
| `TicketStore.issue` + `redeem` single-use | Unit | High |
| `TicketStore.redeem` expired ticket | Unit | High |
| `TicketStore._evict_expired` | Unit | Low |

### 8.3 Test Database Strategy

For `ConfigService` tests, use `tmp_path` (pytest built-in fixture) to create a temporary directory:

```python
def test_get_parameters_reads_file(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "test_client_parameters.json").write_text(
        '{"exchanges": {"Binance": true}, "symbols": {}, "strategy": "arbitrage"}'
    )
    service = ConfigService.__new__(ConfigService)
    service._data_dir = str(tmp_path)
    result = asyncio.run(service.get_parameters("test_client"))
    assert result.exchanges == {"Binance": True}
```

---

## 9. External Dependency Mocking

### 9.1 Mock Architecture

The `conftest.py` fixtures inject mocks directly into `app.state`:

```python
# conftest.py:mock_bot_service
app.state.bot_service = service  # MagicMock with AsyncMock methods
```

This is the correct approach — it tests the full request/response cycle through FastAPI routing, middleware, and dependency injection, while isolating the bot engine. ✅

### 9.2 Mock Realism

| Mock | Realism | Notes |
|---|---|---|
| `mock_bot_service.get_botids` | ✅ Returns `["bot-001", "bot-002"]` | Realistic list |
| `mock_bot_service.create_bot` | ✅ Returns `"bot-003"` | Realistic UUID-like string |
| `mock_bot_service.get_orders` | ⚠️ Returns `[]` by default | No realistic trade records in default fixture |
| `mock_config_service.get_parameters` | ⚠️ Returns `MagicMock(exchanges=..., symbols=...)` | Not a real `ParametersConfig` instance |
| `mock_bot_service._manager` | ✅ Separate mock for WS handler | Correctly mirrors production structure |

The `mock_config_service` returns `MagicMock` objects rather than real `ParametersConfig` instances. This means Pydantic serialisation is not exercised in config endpoint tests — the response schema is not validated end-to-end.

### 9.3 Bot Engine Isolation

The bot engine (`sonarft_manager`, `sonarft_bot`, etc.) is never imported in tests — the `mock_bot_service` fixture prevents `BotService.__init__` from running. This is correct for unit tests but means the bot package import path is never exercised in CI. ✅

---

## 10. Test Code Quality

### 10.1 Strengths

- **Descriptive test names** — `test_invalid_botid_sends_error`, `test_bot_limit_returns_429` are self-documenting ✅
- **Class-based organisation** — tests grouped by endpoint/feature in classes ✅
- **`_trade_record()` helper** — reusable factory for test data ✅
- **`@pytest.mark.parametrize`** — used effectively for botid and client_id validation ✅
- **Fixture teardown** — `mock_bot_service` and `mock_config_service` restore `app.state` on teardown ✅
- **`raise_server_exceptions=False`** — prevents test crashes on expected 500 responses ✅

### 10.2 Issues

**Timing-dependent assertions** (`time.sleep(0.1)`) in 4 WebSocket tests — fragile on slow CI.

**`mock_config_service` returns `MagicMock` not `ParametersConfig`** — Pydantic serialisation not exercised:

```python
# conftest.py:mock_config_service
service.get_parameters = AsyncMock(return_value=MagicMock(
    exchanges={"binance": True}, symbols={"BTC/USDT": True}
))
```

Should return a real `ParametersConfig` instance:

```python
service.get_parameters = AsyncMock(return_value=ParametersConfig(
    exchanges={"binance": True}, symbols={"BTC/USDT": True}
))
```

**`test_no_auth_returns_401_in_static_mode` is a no-op**:

```python
# test_endpoints.py:TestListBots
def test_no_auth_returns_401_in_static_mode(self, client, mock_bot_service):
    "Covered by TestStaticTokenAuth in test_security.py — skip duplicate here."
    pass
```

This test always passes and provides no value. It should either be removed or implemented.

**`test_connection_stays_open` is trivially weak**:

```python
def test_connection_stays_open(self, client):
    with client.websocket_connect(_ws_url()) as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected"
```

This is identical to `test_connects_and_receives_connected_event` — a duplicate.

### 10.3 DRY Assessment

The `_ws_url()` helper and `_trade_record()` factory reduce boilerplate effectively. The `auth_headers` fixture is reused across all endpoint tests. No significant duplication found. ✅

---

## 11. Continuous Integration

### 11.1 Current CI Pipeline — `.github/workflows/ci.yml`

```yaml
jobs:
  test-web:    # ✅ npm test + npm audit
  test-bot:    # ✅ pytest + pip-audit
```

**The API package has no CI job.** The `test-bot` job runs `packages/bot` tests. There is no job that runs `packages/api` tests. This means:
- API tests never run automatically on push/PR
- API test failures are not caught before merge
- No coverage reporting for the API

### 11.2 Missing CI Job

```yaml
# .github/workflows/ci.yml — add:
test-api:
  name: API — test & lint
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: packages/api

  steps:
    - uses: actions/checkout@v4

    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"

    - name: Install bot package
      run: pip install -e ../bot

    - name: Install API dependencies
      run: pip install -r requirements.txt -r requirements-test.txt

    - name: Run tests with coverage
      run: pytest tests/ -q --cov=src --cov-report=term-missing --cov-fail-under=70

    - name: Python dependency audit
      run: pip-audit -r requirements.txt --severity high
```

### 11.3 Coverage Threshold

No coverage threshold is configured. `pytest-cov` is in `requirements-test.txt` but never invoked. A minimum threshold of 70% would catch regressions without being overly restrictive.

### 11.4 Linting in CI

`ruff` is configured in `pyproject.toml` but not run in CI. Adding a lint step would catch style and correctness issues automatically:

```yaml
- name: Lint
  run: pip install ruff && ruff check src/ tests/
```

---

## 12. Test Maintainability

### 12.1 Flaky Test Risks

| Test | Flakiness Risk | Cause |
|---|---|---|
| `test_create_command_calls_bot_manager` | Medium | `time.sleep(0.1)` — timing-dependent |
| `test_remove_command_calls_bot_manager` | Medium | `time.sleep(0.1)` |
| `test_run_command_calls_bot_manager` | Medium | `time.sleep(0.1)` |
| `test_create_failure_handled_gracefully` | Medium | `time.sleep(0.1)` |
| All other tests | Low | Synchronous, deterministic |

### 12.2 Test Isolation

Each test gets a fresh `TestClient` via the `client` fixture (function scope). `mock_bot_service` and `mock_config_service` restore `app.state` on teardown. The `app` fixture is session-scoped — the same app instance is reused across all tests. This is efficient but means `app.state` mutations in one test could leak into another if teardown fails. ⚠️

The `lru_cache` on `get_settings()` is cleared in `TestStaticTokenAuth.static_client` and `TestWebSocketAuth.test_invalid_token_closes_with_1008` — correct, but this pattern must be applied consistently whenever env vars are patched. ✅

### 12.3 Hardcoded Values

| Value | Location | Risk |
|---|---|---|
| `"test-client"` | `_ws_url()` | Low — consistent across WS tests |
| `"test-token"` | `_ws_url()` | Low — dev mode accepts any token |
| `"bot-001"`, `"bot-002"` | `conftest.py` | Low — consistent |
| `"secret-token"` | `TestStaticTokenAuth` | Low — test-only |
| `time.sleep(0.1)` | 4 WS tests | Medium — timing-dependent |

---

## 13. Performance Testing

### 13.1 Current State

No performance or load tests exist. No benchmarks are established.

### 13.2 Recommended Performance Test Scenarios

```python
# tests/performance/test_load.py — using pytest-benchmark
import pytest

def test_health_endpoint_latency(benchmark, client):
    result = benchmark(client.get, "/api/v1/health")
    assert result.status_code == 200

def test_list_bots_latency(benchmark, client, mock_bot_service, auth_headers):
    mock_bot_service.get_botids.return_value = ["bot-001"] * 5
    result = benchmark(
        client.get, "/api/v1/bots?client_id=test", headers=auth_headers
    )
    assert result.status_code == 200
```

---

## 14. Test Fixtures & Factories

### 14.1 Existing Fixtures

| Fixture | Scope | Purpose |
|---|---|---|
| `app` | session | FastAPI app instance — created once |
| `client` | function | `TestClient` wrapping `app` |
| `auth_headers` | function | `{"Authorization": "Bearer test-token"}` |
| `mock_bot_service` | function | Injects mock into `app.state.bot_service` |
| `mock_config_service` | function | Injects mock into `app.state.config_service` |

### 14.2 Missing Fixtures

| Missing Fixture | Purpose |
|---|---|
| `tmp_config_dir` | Temporary `sonarftdata/config/` for `ConfigService` integration tests |
| `tmp_db` | Temporary SQLite DB for `SonarftHelpers` tests |
| `ticket_store` | Fresh `TicketStore` instance for unit tests |
| `static_auth_client` | Pre-configured client with `SONARFT_API_TOKEN` set |
| `real_bot_service` | `BotService` with mocked `BotManager` (not full mock) |

### 14.3 `_trade_record()` Factory

The `_trade_record(**overrides)` helper in `test_endpoints.py` is a good pattern — it provides a valid base record with override support. It should be moved to `conftest.py` for reuse across test files.

---

## 15. Concerns & Recommendations

### 15.1 Concerns

| # | Concern | Severity | Location |
|---|---|---|---|
| T1 | **No CI job for API tests** — API tests never run automatically | High | `.github/workflows/ci.yml` |
| T2 | **Canonical `/clients/{id}/...` routes have zero tests** — primary API surface untested | High | `tests/unit/test_endpoints.py` |
| T3 | **`ws_ticket.py` and `tickets.py` have zero tests** — WS auth entry point untested | High | `tests/` |
| T4 | **No integration tests** — `tests/integration/` is empty | Medium | `tests/integration/` |
| T5 | **No coverage measurement** — `pytest-cov` installed but never invoked | Medium | `pytest.ini`, CI |
| T6 | **`time.sleep(0.1)` in 4 WS tests** — timing-dependent, flaky on slow CI | Medium | `test_websocket.py` |
| T7 | **`mock_config_service` returns `MagicMock` not `ParametersConfig`** — Pydantic serialisation not exercised | Medium | `conftest.py` |
| T8 | **`ConfigService` never tested with real filesystem** — path traversal guard untested | Medium | `tests/` |
| T9 | **`stop` and `set_simulation` WS commands untested** | Low | `test_websocket.py` |
| T10 | **`test_no_auth_returns_401_in_static_mode` is a no-op `pass`** | Low | `test_endpoints.py:TestListBots` |

---

### 15.2 Recommendations (Prioritised)

#### P1 — Fix immediately

**R1: Add API CI job to `.github/workflows/ci.yml`**

```yaml
test-api:
  name: API — test & audit
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: packages/api
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - name: Install dependencies
      run: |
        pip install -e ../bot
        pip install -r requirements.txt -r requirements-test.txt
    - name: Run tests with coverage
      run: pytest tests/ -q --cov=src --cov-report=term-missing --cov-fail-under=70
    - name: Lint
      run: pip install ruff && ruff check src/ tests/
    - name: Dependency audit
      run: pip install pip-audit && pip-audit -r requirements.txt --severity high
```

**R2: Add tests for canonical `/clients/{id}/...` routes**

```python
# tests/unit/test_clients.py
class TestCanonicalListBots:
    def test_returns_botids(self, client, mock_bot_service, auth_headers):
        mock_bot_service.get_botids.return_value = ["bot-001"]
        r = client.get("/api/v1/clients/test-client/bots", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == {"botids": ["bot-001"]}

    def test_invalid_client_id_returns_422(self, client, auth_headers):
        r = client.get("/api/v1/clients/../evil/bots", headers=auth_headers)
        assert r.status_code in (404, 422)
```

**R3: Add `TicketStore` unit tests**

```python
# tests/unit/test_tickets.py
from src.websocket.tickets import TicketStore
import time

def test_issue_and_redeem():
    store = TicketStore(ttl=30)
    ticket = store.issue("client-1")
    assert store.redeem(ticket) == "client-1"

def test_single_use():
    store = TicketStore(ttl=30)
    ticket = store.issue("client-1")
    store.redeem(ticket)
    assert store.redeem(ticket) is None  # already consumed

def test_expired_ticket():
    store = TicketStore(ttl=0)  # immediate expiry
    ticket = store.issue("client-1")
    time.sleep(0.01)
    assert store.redeem(ticket) is None
```

---

#### P2 — Medium effort

**R4: Fix `mock_config_service` to return real Pydantic models**

```python
# conftest.py
from src.models.schemas import ParametersConfig, IndicatorsConfig

service.get_parameters = AsyncMock(return_value=ParametersConfig(
    exchanges={"binance": True}, symbols={"BTC/USDT": True}
))
service.get_indicators = AsyncMock(return_value=IndicatorsConfig(
    periods={"5min": True}, oscillators={}, movingaverages={}
))
```

**R5: Replace `time.sleep(0.1)` with event-based assertions**

```python
# test_websocket.py — replace timing-dependent pattern
import asyncio

# Instead of:
ws.send_json({"key": "create"})
time.sleep(0.1)
mock.assert_called_once()

# Use a short poll loop:
ws.send_json({"key": "create"})
for _ in range(10):
    if mock.called:
        break
    time.sleep(0.01)
mock.assert_called_once()
```

**R6: Add `ConfigService` integration tests using `tmp_path`**

```python
# tests/integration/test_config_service.py
import pytest, json, asyncio
from src.services.config_service import ConfigService

@pytest.fixture
def config_service(tmp_path):
    (tmp_path / "config").mkdir()
    svc = ConfigService.__new__(ConfigService)
    svc._data_dir = str(tmp_path)
    return svc

def test_update_then_get_parameters(config_service, tmp_path):
    from src.models.schemas import ParametersConfig
    config = ParametersConfig(exchanges={"Binance": True}, symbols={"BTC/USDT": True})
    asyncio.run(config_service.update_parameters("test-client", config))
    result = asyncio.run(config_service.get_parameters("test-client"))
    assert result.exchanges == {"Binance": True}
```

**R7: Add `stop` and `set_simulation` WS command tests**

```python
# test_websocket.py
class TestWebSocketStopCommand:
    def test_stop_command_calls_pause_bot(self, client, mock_bot_service):
        mock_bot_service._manager.pause_bot = AsyncMock(return_value=None)
        with client.websocket_connect(_ws_url()) as ws:
            ws.receive_json()  # connected
            ws.send_json({"key": "stop", "botid": "bot-001"})
            time.sleep(0.1)
        mock_bot_service._manager.pause_bot.assert_called_once_with("bot-001")
```

---

#### P3 — Longer term

**R8: Add end-to-end log streaming test**

```python
# tests/integration/test_websocket_e2e.py
import logging, asyncio, pytest
from httpx_ws import aconnect_ws

@pytest.mark.asyncio
async def test_log_streaming_end_to_end(async_client):
    async with aconnect_ws("/api/v1/ws/test?token=test", async_client) as ws:
        await ws.receive_json()  # connected
        logging.getLogger("sonarft_manager").info("test message")
        event = await asyncio.wait_for(ws.receive_json(), timeout=1.0)
        assert event["type"] == "log"
        assert "test message" in event["message"]
```

This test would have caught the `_BOT_LOGGER_NAME` bug immediately.

**R9: Add coverage to `pytest.ini`**

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
addopts = --cov=src --cov-report=term-missing
```

**R10: Move `_trade_record()` to `conftest.py`**

```python
# conftest.py
@pytest.fixture
def trade_record_factory():
    def _make(**overrides):
        base = dict(timestamp="2025-07-01T12:00:00", position="LONG", ...)
        base.update(overrides)
        return base
    return _make
```

---

## CI/CD Integration Checklist

- [ ] Add `test-api` job to `.github/workflows/ci.yml`
- [ ] Add `--cov=src --cov-fail-under=70` to pytest invocation
- [ ] Add `ruff check src/ tests/` lint step to CI
- [ ] Add `pip-audit -r requirements.txt --severity high` to CI
- [ ] Add tests for all canonical `/clients/{id}/...` routes
- [ ] Add `TicketStore` unit tests
- [ ] Add `ConfigService` integration tests with `tmp_path`
- [ ] Fix `mock_config_service` to return real Pydantic models
- [ ] Replace `time.sleep(0.1)` with poll-based assertions
- [ ] Add `stop` and `set_simulation` WS command tests
- [ ] Add end-to-end log streaming integration test

---

## Related Prompts

- [Prompt 04: Authentication & Security](../security/04-authentication-security.md) — Security test coverage
- [Prompt 05: WebSocket & Real-time](../websocket/05-websocket-realtime.md) — WS test gaps
- [Prompt 10: Code Quality Python](../code-quality/10-code-quality-python.md) — Code quality affecting testability
- [Prompt 08: Performance Optimization](../performance/08-performance-optimization.md) — Performance testing

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 09_
