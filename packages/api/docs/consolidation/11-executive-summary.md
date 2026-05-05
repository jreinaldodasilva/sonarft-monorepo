# Executive Summary — Consolidated API Review

**Prompt ID:** 11-API-FINAL  
**Package:** `packages/api` + `packages/bot`  
**Reviewer:** Amazon Q (Senior Python / FastAPI / Security / Architecture)  
**Review Cycle:** Prompts 01–10 complete  
**Date:** July 2025  
**Output:** `docs/consolidation/11-executive-summary.md`

---

## 1. Executive Summary (1-Page Brief)

### Overall Assessment

The SonarFT API is a **well-architected, production-capable FastAPI service** for a single-operator cryptocurrency trading system. The codebase demonstrates strong engineering discipline: correct async patterns throughout, a security-first middleware stack, Pydantic v2 validation, ticket-based WebSocket auth, and a mature bot engine with circuit breakers, exponential backoff, and structured JSON metrics. For its target workload (1 operator, ≤5 bots), the system is functionally complete and deployable.

**Confidence level for production deployment: 7.5/10** — deployable with two pre-flight fixes (`.env` gitignore, `_BOT_LOGGER_NAME`).

### Top 3 Risks

1. **`.env` not in `packages/api/.gitignore`** — one `git add .` away from committing `SONARFT_API_TOKEN` or `NETLIFY_SITE_URL` to version control (High, Security)
2. **`_BOT_LOGGER_NAME` mismatch** — log streaming is silently broken in production; the WebSocket client receives zero bot log events (High, Functional)
3. **No API CI job** — all 93 API tests never run automatically; regressions go undetected before merge (High, Quality)

### Top 3 Strengths

1. **Correct async architecture** — zero blocking calls in any async handler; `asyncio.to_thread` used consistently for all I/O; `asyncio.gather` for parallel operations
2. **Security-first design** — RS256 JWT with live JWKS, timing-safe token comparison, ticket-based WS auth, full security header stack, path traversal guards, parameterised SQL
3. **Production-grade bot engine** — circuit breaker, exponential backoff order cancellation, flash crash detection, daily loss limits, structured JSON metrics, SQLite WAL with hot backup

### Top 3 Next Steps

1. Add `.env` to `packages/api/.gitignore` and fix `_BOT_LOGGER_NAME` (< 1 hour, zero risk)
2. Add API CI job to `.github/workflows/ci.yml` with coverage threshold (2–3 hours)
3. Add tests for canonical `/clients/{id}/...` routes and `TicketStore` (1 day)

### Timeline to Full Production Readiness

- **Today** (2 fixes): Deployable for single-operator use
- **30 days**: All critical/high items resolved — confident production deployment
- **60 days**: Integration tests, canonical route tests, performance baselines
- **90 days**: Architectural improvements (WS router, structured logging, migration tooling)

---

## 2. Overall Health Assessment

### Health by Domain

| Domain | Score | Status | Key Finding |
|---|---|---|---|
| Architecture | 8.5/10 | ✅ Strong | Clean layered separation; WS endpoint inline in factory |
| REST Endpoints | 8.0/10 | ✅ Good | Canonical routes untested; legacy duplication by design |
| Data Models | 8.5/10 | ✅ Strong | Full Pydantic v2; `WsLogEvent.level` TypeScript mismatch |
| Security | 8.0/10 | ⚠️ Good | `.env` in git; auth silently disabled in dev |
| WebSocket | 7.5/10 | ⚠️ Good | `_BOT_LOGGER_NAME` bug breaks log streaming |
| Error Handling | 8.0/10 | ✅ Good | Services raise `HTTPException` directly |
| Database | 7.5/10 | ⚠️ Good | Bot registry never cleaned; no migration tooling |
| Performance | 8.5/10 | ✅ Strong | Correct async; `orjson`/`uvloop` not enabled |
| Testing | 6.5/10 | ⚠️ Needs Work | No CI job; canonical routes untested; no integration tests |
| Code Quality | 8.2/10 | ✅ Strong | `Makefile` uses wrong linter; `B904` suppresses real issues |
| **Overall** | **7.9/10** | ✅ **Production-capable** | Two pre-flight fixes required |

---

## 3. Critical Issues Summary

### High Severity — Must Address

| ID | Issue | Domain | Source | Effort |
|---|---|---|---|---|
| H1 | **`.env` not in `packages/api/.gitignore`** — credentials will be committed if a developer fills in values | Security | Prompt 04 V1 | 5 min |
| H2 | **`_BOT_LOGGER_NAME = "src.services.bot_service"` is wrong** — log streaming silently broken in production | WebSocket | Prompt 05 W1 | 15 min |
| H3 | **No CI job for API package** — 93 tests never run automatically | Testing | Prompt 09 T1 | 2–3 hrs |
| H4 | **Canonical `/clients/{id}/...` routes have zero tests** — primary API surface untested | Testing | Prompt 09 T2 | 1 day |
| H5 | **`ws_ticket.py` and `TicketStore` have zero tests** — WS auth entry point untested | Testing | Prompt 09 T3 | 4 hrs |

### Medium Severity — Should Address

| ID | Issue | Domain | Source | Effort |
|---|---|---|---|---|
| M1 | **Auth silently disabled in dev mode** — no startup warning | Security | Prompt 04 V2 | 30 min |
| M2 | **Static token never expires** — leaked token valid indefinitely | Security | Prompt 04 V4 | 1 day |
| M3 | **No `pip audit` in CI** — Python CVEs not caught automatically | Security | Prompt 04 V6 | 1 hr |
| M4 | **No `WsBotStoppedEvent`** — `stop` command has no WS confirmation | WebSocket | Prompt 05 W3 | 2 hrs |
| M5 | **`order_success`/`trade_success` via string matching** — fragile coupling to log text | WebSocket | Prompt 05 W4 | 4 hrs |
| M6 | **Services raise `HTTPException` directly** — HTTP translation in wrong layer | Error Handling | Prompt 06 E1/E2 | 4 hrs |
| M7 | **No HTTP access log** — no record of requests, status codes, response times | Error Handling | Prompt 06 E3 | 2 hrs |
| M8 | **Bot registry files never deleted** — `sonarftdata/bots/*.json` accumulates indefinitely | Database | Prompt 07 D2 | 1 hr |
| M9 | **`daily_loss` table created in `sonarft_search.py` not `_init_db`** — schema inconsistency | Database | Prompt 07 D4 | 1 hr |
| M10 | **No integration tests** — `tests/integration/` is empty | Testing | Prompt 09 T4 | 3 days |
| M11 | **No coverage measurement** — `pytest-cov` installed but never invoked | Testing | Prompt 09 T5 | 1 hr |
| M12 | **`Makefile` uses `pylint` but packages configure `ruff`** — tooling inconsistency | Code Quality | Prompt 10 Q1 | 30 min |
| M13 | **`B904` ruff ignore suppresses exception chaining warnings** | Code Quality | Prompt 10 Q2 | 1 hr |
| M14 | **`WsLogEvent.level` mismatch** — Python allows `DEBUG`/`CRITICAL`; TypeScript only `INFO`/`WARNING`/`ERROR` | Models | Prompt 03 8.1 | 30 min |
| M15 | **`ParametersConfig` name collision** — API (3 fields) and bot (13 fields) share a name | Models | Prompt 03 8.2 | 2 hrs |

---

## 4. Strengths & Assets

### Architecture & Design
- **Clean layered separation** — endpoints → services → bot engine → persistence; no business logic in routers (`Prompt 01`)
- **Application factory pattern** — `create_app()` with lifespan-managed service initialisation; services on `app.state` (`Prompt 01`)
- **Dependency injection** — FastAPI `Depends` for endpoints; constructor injection for bot modules; no hard-coded dependencies (`Prompt 10`)
- **Dual-route strategy** — canonical `/clients/{id}/...` + deprecated `/bots?client_id=` with clear OpenAPI deprecation markers (`Prompt 02`)

### Security
- **RS256 JWT with live JWKS** — asymmetric algorithm; API never holds a private key; automatic key rotation (`Prompt 04`)
- **Timing-safe token comparison** — `hmac.compare_digest` prevents timing oracle attacks (`Prompt 04`)
- **WebSocket ticket auth** — JWT never appears in server logs or browser history (`Prompt 04`)
- **Full security header stack** — HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy (`Prompt 04`)
- **Path traversal guard** — `_client_path` resolves and checks prefix; config key regex allowlist (`Prompt 05`)
- **Parameterised SQL** — all SQLite queries use `?` placeholders; table name validated against `_ALLOWED_TABLES` (`Prompt 07`)

### Bot Engine
- **Circuit breaker** — `run_bot` stops after configurable consecutive failures with alert (`Prompt 06`)
- **Exponential backoff order cancellation** — `_cancel_order_with_retry` with 3 attempts and webhook alert on final failure (`Prompt 06`)
- **Flash crash detection** — price deviation threshold prevents execution during extreme volatility (`Prompt 06`)
- **Structured JSON metrics** — `sonarft_metrics.py` emits typed events for every signal, order, trade, and risk event (`Prompt 06`)
- **SQLite WAL with hot backup** — concurrent reads, daily automated backup via `sqlite3.Connection.backup()` (`Prompt 07`)
- **Open order reconciliation** — stale orders from previous runs cancelled at bot startup (`Prompt 07`)

### Async Correctness
- **Zero blocking calls** — all I/O uses `asyncio.to_thread` or native async APIs (`Prompt 08`)
- **`asyncio.gather` for parallelism** — symbol processing, liquidity checks, exchange queries all concurrent (`Prompt 08`)
- **`asyncio.shield` for interruptible waits** — stop event can interrupt backoff sleep without cancelling the outer task (`Prompt 10`)

### Testing
- **93 tests** covering all 14 legacy REST endpoints, 3 auth modes, parametrised injection attacks, all WS command paths, all error handlers (`Prompt 09`)
- **`test_all_protected_endpoints_require_token`** — iterates all 13 protected endpoints as a regression guard (`Prompt 09`)
- **Mock injection via `app.state`** — full request/response cycle exercised without real bot engine (`Prompt 09`)

---

## 5. Consolidated Recommendations by Priority

### Critical — Fix Before Any Production Deployment

| # | Action | Effort | Source |
|---|---|---|---|
| C1 | Add `.env` to `packages/api/.gitignore`; run `git rm --cached packages/api/.env` | 5 min | Prompt 04 R1 |
| C2 | Fix `_BOT_LOGGER_NAME` to match actual bot logger hierarchy | 15 min | Prompt 05 R1 |
| C3 | Add API CI job to `.github/workflows/ci.yml` with `pytest --cov --cov-fail-under=70` | 2–3 hrs | Prompt 09 R1 |

### High — Complete Before Full Release

| # | Action | Effort | Source |
|---|---|---|---|
| H1 | Add tests for all canonical `/clients/{id}/...` routes | 1 day | Prompt 09 R2 |
| H2 | Add `TicketStore` unit tests (issue, redeem, expiry, single-use) | 4 hrs | Prompt 09 R3 |
| H3 | Add startup warning when auth is disabled | 30 min | Prompt 04 R2 |
| H4 | Add `pip audit` to CI for API and bot packages | 1 hr | Prompt 04 R4 |
| H5 | Add `WsBotStoppedEvent` and emit from `_handle_stop` | 2 hrs | Prompt 05 R2 |
| H6 | Fix `Makefile` to use `ruff check` instead of `pylint` | 30 min | Prompt 10 R1 |
| H7 | Remove `B904` from ruff ignore; fix the 2 known violations | 1 hr | Prompt 10 R2 |
| H8 | Fix `mock_config_service` to return real `ParametersConfig` instances | 30 min | Prompt 09 R4 |
| H9 | Add `Cache-Control: no-store` to `SecurityHeadersMiddleware` | 30 min | Prompt 04 R5 |
| H10 | Delete bot registry file on bot removal | 1 hr | Prompt 07 R1 |

### Medium — Plan Next Quarter

| # | Action | Effort | Source |
|---|---|---|---|
| M1 | Add `ConfigService` integration tests with `tmp_path` | 1 day | Prompt 09 R6 |
| M2 | Add end-to-end log streaming integration test | 4 hrs | Prompt 09 R8 |
| M3 | Add `stop` and `set_simulation` WS command tests | 2 hrs | Prompt 09 R7 |
| M4 | Replace `time.sleep(0.1)` with poll-based WS test assertions | 2 hrs | Prompt 09 R5 |
| M5 | Add HTTP access logging middleware | 2 hrs | Prompt 06 R4 |
| M6 | Move `HTTPException` out of service layer; add domain exceptions | 4 hrs | Prompt 06 R5 |
| M7 | Add `request_id` to error response bodies | 1 hr | Prompt 06 R6 |
| M8 | Add `GZipMiddleware` for responses > 1 KB | 30 min | Prompt 08 R2 |
| M9 | Enable `uvloop` in Dockerfile CMD | 15 min | Prompt 08 R1 |
| M10 | Switch WS send loop to `orjson`; set `ORJSONResponse` as default | 1 hr | Prompt 08 R3/R4 |
| M11 | Extract `BOTID_PATTERN` / `CLIENT_ID_PATTERN` constants | 1 hr | Prompt 10 R3 |
| M12 | Name `__ticket_verified__` sentinel as a typed constant | 1 hr | Prompt 04 R3 / Prompt 10 R4 |
| M13 | Align `WsLogEvent.level` between Python and TypeScript | 30 min | Prompt 03 R1 |
| M14 | Remove dead code: `BotActionRequest`, `BotStatusResponse`, `BotRunError` | 30 min | Prompt 03 R2 / Prompt 06 R3 |
| M15 | Move `TicketResponse` to `schemas.py` | 30 min | Prompt 03 R3 |
| M16 | Add dict size limits to `ParametersConfig`/`IndicatorsConfig` | 1 hr | Prompt 03 R5 |
| M17 | Add `daily_loss` table to `_init_db` (consolidate schema) | 1 hr | Prompt 07 R2 |
| M18 | Add config file versioning (`version: int = 1`) | 2 hrs | Prompt 07 R3 |
| M19 | Use `logger.exception()` in bot error handlers | 1 hr | Prompt 10 R6 |
| M20 | Add `Content-Security-Policy: default-src 'none'` header | 30 min | Prompt 04 R6 |

### Low — Nice to Have

| # | Action | Effort | Source |
|---|---|---|---|
| L1 | Extract `_execute_two_leg_trade` shared method in `SonarftExecution` | 1 day | Prompt 10 R7 |
| L2 | Extract WebSocket endpoint from `create_app()` into a router | 4 hrs | Prompt 10 R8 |
| L3 | Add `bot_manager` type annotation in `WebSocketManager` | 30 min | Prompt 10 R9 |
| L4 | Create shared root-level `ruff` config | 1 hr | Prompt 10 R10 |
| L5 | Run `mypy` in CI for API package | 1 hr | Prompt 10 R11 |
| L6 | Add mtime-based config file cache in `ConfigService` | 2 hrs | Prompt 08 R5 |
| L7 | Add `Sunset` / `Deprecation` headers to legacy routes | 1 hr | Prompt 02 R7 |
| L8 | Add date-range filtering to history endpoints | 1 day | Prompt 02 R8 |
| L9 | Add `WsBaseEvent` base class in Python schemas | 2 hrs | Prompt 03 R7 |
| L10 | Rename API `ParametersConfig` to `ClientParametersConfig` | 2 hrs | Prompt 03 R8 |
| L11 | Add `503` response when `BotService` is unavailable | 1 hr | Prompt 06 R9 |
| L12 | Add structured JSON logging to API layer | 1 day | Prompt 06 R8 |
| L13 | Write backup to separate directory | 1 hr | Prompt 07 R4 |
| L14 | Add cursor-based pagination for history endpoints | 1 day | Prompt 07 R5 |
| L15 | Establish Locust load test baseline | 1 day | Prompt 08 R9 |

---

## 6. Go / No-Go Production Readiness Assessment

| Checkpoint | Status | Condition |
|---|---|---|
| **Security: Critical vulnerabilities addressed** | ⚠️ Conditional | Fix C1 (`.env` gitignore) first |
| **Security: Auth configured for production** | ✅ Ready | Set `NETLIFY_SITE_URL` or `SONARFT_API_TOKEN` in `.env` |
| **Functionality: Core trading loop works** | ⚠️ Conditional | Fix C2 (`_BOT_LOGGER_NAME`) — log streaming broken |
| **Testing: Coverage adequate** | ⚠️ Conditional | Fix C3 (CI job) + H1 (canonical route tests) |
| **Documentation: API documented** | ✅ Ready | OpenAPI at `/api/v1/docs`; README complete |
| **Error Handling: Errors handled and logged** | ✅ Ready | Generic 500 handler; request ID correlation |
| **Performance: Handles expected load** | ✅ Ready | Correct async; ≤5 bots well within capacity |
| **Scalability: Can grow as needed** | ✅ Ready | Vertical scaling path clear; horizontal documented |
| **Monitoring: Issues detectable** | ✅ Ready | `sonarft_metrics.jsonl`; rotating logs; health endpoint |
| **Support: Team can maintain** | ✅ Ready | Comprehensive docs; clear architecture |

**Verdict: CONDITIONAL GO**

The system is deployable for single-operator production use **after completing C1 and C2** (< 30 minutes of work). C3 (CI job) should be completed within the first week of production operation.

---

## 7. 30 / 60 / 90 Day Improvement Plan

### Next 30 Days — Critical Path

**Week 1 (< 1 day total):**
- [ ] C1: Add `.env` to `packages/api/.gitignore` + `git rm --cached`
- [ ] C2: Fix `_BOT_LOGGER_NAME` to `"sonarft_manager"` (or root logger with filter)
- [ ] H3: Add startup warning when auth is disabled
- [ ] H6: Fix `Makefile` to use `ruff check`
- [ ] H9: Add `Cache-Control: no-store` to `SecurityHeadersMiddleware`
- [ ] H10: Delete bot registry file on bot removal
- [ ] M14: Remove dead code (`BotActionRequest`, `BotStatusResponse`, `BotRunError`)

**Week 2 (2–3 days):**
- [ ] C3: Add API CI job with coverage threshold
- [ ] H4: Add `pip audit` to CI
- [ ] H7: Remove `B904` from ruff ignore; fix violations
- [ ] H8: Fix `mock_config_service` to return real Pydantic models
- [ ] M13: Align `WsLogEvent.level` with TypeScript

**Week 3–4 (3–4 days):**
- [ ] H1: Add tests for all canonical `/clients/{id}/...` routes
- [ ] H2: Add `TicketStore` unit tests
- [ ] H5: Add `WsBotStoppedEvent`
- [ ] M11: Extract `BOTID_PATTERN` / `CLIENT_ID_PATTERN` constants
- [ ] M15: Move `TicketResponse` to `schemas.py`

### Next 60 Days — Near-Term Improvements

**Testing (1 week):**
- [ ] M1: `ConfigService` integration tests with `tmp_path`
- [ ] M2: End-to-end log streaming integration test
- [ ] M3: `stop` and `set_simulation` WS command tests
- [ ] M4: Replace `time.sleep(0.1)` with poll-based assertions
- [ ] M11: Add coverage reporting to CI

**Error Handling & Observability (3 days):**
- [ ] M5: HTTP access logging middleware
- [ ] M6: Move `HTTPException` out of service layer
- [ ] M7: Add `request_id` to error response bodies
- [ ] M19: Use `logger.exception()` in bot error handlers

**Performance (1 day):**
- [ ] M8: Add `GZipMiddleware`
- [ ] M9: Enable `uvloop` in Dockerfile
- [ ] M10: Switch to `orjson` + `ORJSONResponse`

**Models & Validation (2 days):**
- [ ] M12: Name `__ticket_verified__` sentinel
- [ ] M16: Add dict size limits to config models
- [ ] M17: Consolidate `daily_loss` table into `_init_db`
- [ ] M18: Add config file versioning

### Next 90 Days — Medium-Term Vision

**Architecture (1 week):**
- [ ] L2: Extract WebSocket endpoint into a router
- [ ] L12: Add structured JSON logging to API layer
- [ ] L11: Add `503` response for unavailable services
- [ ] L4: Create shared root-level `ruff` config

**Database & Persistence (3 days):**
- [ ] L13: Write backup to separate directory
- [ ] L14: Add cursor-based pagination
- [ ] Evaluate Alembic for schema migrations

**Code Quality (3 days):**
- [ ] L1: Extract `_execute_two_leg_trade` shared method
- [ ] L5: Run `mypy` in CI
- [ ] L10: Rename `ParametersConfig` to `ClientParametersConfig`

**Performance & Scaling (1 week):**
- [ ] L15: Establish Locust load test baseline
- [ ] L6: Add mtime-based config cache
- [ ] Document horizontal scaling migration path (Redis for tickets/rate limits)

---

## 8. Success Metrics

### Code Quality Metrics

| Metric | Current | Target (30d) | Target (90d) |
|---|---|---|---|
| Test count | 93 | 150+ | 200+ |
| API test coverage | ~50% (estimated) | 70% | 80% |
| CI pipeline | Web + Bot only | Web + Bot + API | All packages |
| Ruff violations | 0 (with B904 suppressed) | 0 (B904 enabled) | 0 |
| Dead code models | 2 (`BotActionRequest`, `BotStatusResponse`) | 0 | 0 |

### Security Metrics

| Metric | Current | Target |
|---|---|---|
| `.env` in git | ⚠️ Yes (empty values) | ❌ Not tracked |
| CVE scan in CI | Bot only | All packages |
| Auth disabled warning | ❌ None | ✅ Startup log |
| Critical/High CVEs | 0 (estimated) | 0 |

### Performance Metrics

| Metric | Current | Target |
|---|---|---|
| Health endpoint latency | < 5ms (estimated) | < 5ms (measured) |
| History query (100 records) | < 10ms (estimated) | < 10ms (measured) |
| Bot cycle duration | Tracked in metrics | P95 < 500ms |
| WS event delivery latency | < 1ms (estimated) | < 5ms (measured) |

### Operational Metrics

| Metric | Current | Target |
|---|---|---|
| Log streaming functional | ❌ Broken | ✅ Fixed (C2) |
| Backup frequency | Daily (automated) | Daily + off-site |
| Bot registry cleanup | ❌ Never | ✅ On removal |
| Uptime (health check) | Docker healthcheck 30s | 99.9% |

---

## 9. Cross-Domain Risk Analysis

### Security Risk Score: 7.5/10

| Risk | Severity | Status |
|---|---|---|
| `.env` tracked by git | High | ⚠️ Fix C1 immediately |
| Auth silently disabled in dev | Medium | ⚠️ Fix H3 |
| Static token never expires | Medium | ⚠️ Plan M2 |
| `__ticket_verified__` string bypass | Low | Plan M12 |
| No `pip audit` in CI | Medium | Fix H4 |
| No `Cache-Control` headers | Low | Fix H9 |
| JWT algorithm confusion | ✅ Not possible | RS256 explicit allowlist |
| SQL injection | ✅ Not possible | Parameterised queries throughout |
| Path traversal | ✅ Not possible | Regex + path prefix check |
| XSS via config keys | ✅ Not possible | Allowlist regex on all dict keys |
| Timing attack on token | ✅ Not possible | `hmac.compare_digest` |

### Operational Risk Score: 8.0/10

| Risk | Severity | Status |
|---|---|---|
| Log streaming broken | High | ⚠️ Fix C2 immediately |
| No HTTP access log | Medium | Plan M5 |
| Bot state lost on restart | Medium | Documented; manual recovery |
| No `503` for unavailable services | Low | Plan L11 |
| Backup on same disk as source | Low | Plan L13 |
| No runtime log-level change | Low | Plan L12 |

### Performance Risk Score: 8.5/10

| Risk | Severity | Status |
|---|---|---|
| `orjson` unused | Low | Plan M10 |
| No response compression | Low | Fix M8 |
| `uvloop` not enabled | Low | Fix M9 |
| Config files read on every request | Low | Plan L6 |
| No load test baselines | Medium | Plan L15 |
| Exchange API latency (external) | N/A | Cannot optimise |

### Quality Risk Score: 7.0/10

| Risk | Severity | Status |
|---|---|---|
| No API CI job | High | Fix C3 |
| Canonical routes untested | High | Fix H1 |
| No integration tests | Medium | Plan M1/M2 |
| No coverage measurement | Medium | Fix M11 |
| `time.sleep(0.1)` flaky tests | Medium | Fix M4 |
| `execute_long/short_trade` duplication | Medium | Plan L1 |

---

## 10. Dependency & Integration Issues

### Bot Engine Integration

| Issue | Severity | Notes |
|---|---|---|
| In-process coupling — API crash = bot crash | High | Acceptable for single-operator; document for multi-tenant |
| `_BOT_LOGGER_NAME` mismatch | High | Fix C2 |
| Shared `sonarftdata/` filesystem | Medium | Docker Compose correctly uses shared volume ✅ |
| Bot state lost on API restart | Medium | No reconciliation from persistent storage |
| `ParametersConfig` name collision | Medium | API (3 fields) vs bot (13 fields) — same name, different domain |

### Frontend Integration

| Issue | Severity | Notes |
|---|---|---|
| WS endpoint invisible to OpenAPI | Medium | Developers must read source/README |
| `WsLogEvent.level` TypeScript mismatch | Medium | Fix M13 |
| No `WsBotStoppedEvent` | Medium | Fix H5 |
| `create` via WS auto-runs (REST does not) | Low | Document asymmetry |
| Mixed timestamp formats (ISO vs epoch) | Low | REST uses ISO, WS uses epoch |

### External Dependencies

| Dependency | Risk | Notes |
|---|---|---|
| Netlify Identity JWKS | Medium | External service; JWKS fetch fails → auth broken |
| ccxt/ccxtpro exchange APIs | High | External; latency and availability outside control |
| Exchange rate limits | Medium | `max_orders_per_minute` guard in place ✅ |

---

## Resource Estimation

### Critical Path (C1–C3): < 1 day

| Item | Effort | Expertise |
|---|---|---|
| C1: `.env` gitignore | 5 min | Any developer |
| C2: Fix `_BOT_LOGGER_NAME` | 15 min | Python/logging |
| C3: Add API CI job | 2–3 hrs | GitHub Actions / Python |

### High Priority (H1–H10): 3–4 days

| Item | Effort | Expertise |
|---|---|---|
| H1: Canonical route tests | 1 day | pytest / FastAPI |
| H2: TicketStore tests | 4 hrs | pytest |
| H3–H10: Remaining high items | 1–2 days | Python / FastAPI |

### Medium Priority (M1–M20): 2–3 weeks

| Item | Effort | Expertise |
|---|---|---|
| Integration tests | 3 days | pytest / asyncio |
| Error handling refactor | 2 days | Python / FastAPI |
| Performance quick wins | 1 day | Python / Docker |
| Model/schema cleanup | 1 day | Pydantic v2 |

### Low Priority (L1–L15): 4–6 weeks

| Item | Effort | Expertise |
|---|---|---|
| Architecture improvements | 1 week | FastAPI / Python |
| Database improvements | 3 days | SQLite / Python |
| Load testing | 1 week | Locust / performance |

---

## Team Alignment & Communication

### Key Findings to Discuss

1. **Log streaming is broken** (C2) — the trading dashboard shows no bot activity logs in production. This is a user-visible functional regression that should be fixed before any user-facing deployment.

2. **`.env` is tracked by git** (C1) — any developer who fills in real credentials and runs `git add .` will commit them. This needs immediate team awareness.

3. **The API has no CI** (C3) — 93 tests exist but never run automatically. The team may not be aware that API test failures go undetected.

4. **Canonical routes are the primary API surface** — the web frontend uses `/clients/{id}/bots`, not `/bots?client_id=`. The untested canonical routes (H1) are the routes actually in use.

### Areas Requiring Additional Expertise

| Area | Expertise Needed |
|---|---|
| Netlify Identity JWT configuration | Netlify Identity / OAuth2 |
| Exchange API key management | Exchange-specific documentation |
| Production TLS configuration | nginx / Traefik / cloud load balancer |
| Horizontal scaling (if needed) | Redis / distributed systems |

### Process Improvements

1. **Add pre-commit hooks** — `ruff check` + `ruff format` on every commit prevents style regressions
2. **Require CI to pass before merge** — once C3 is done, enforce branch protection rules
3. **Weekly `pip audit` review** — schedule a recurring check of Python CVEs
4. **Document the 30/60/90 plan** — track progress in a project board

---

## Related Prompts

- [Prompt 12: Implementation Roadmap](../roadmap/12-implementation-roadmap.md) — Detailed sprint plan
- [Prompt 01: Architecture](../architecture/01-api-architecture.md) — Full architecture review
- [Prompt 04: Security](../security/04-authentication-security.md) — Full security review
- [Prompt 09: Testing](../testing/09-testing-quality.md) — Full testing review

---

_Part of the SonarFT API Code Review Prompt Suite — Prompt 11_
