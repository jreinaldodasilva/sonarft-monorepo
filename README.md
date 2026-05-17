# SonarFT

**System Oscillator for Navigation and Ranging in Financial Trade**

An automated cryptocurrency trading platform built as a three-layer monorepo. SonarFT monitors market oscillations using technical indicators, executes trades across single or multiple exchanges, and streams real-time data to a React frontend — all in simulation or live mode.

---

## Core Capabilities

- **Multi-exchange trading** — arbitrage and market-making across OKX, Binance, Bitfinex, and 15+ CCXT-supported exchanges
- **Technical indicators** — RSI, MACD, StochRSI, VWAP, SMA, EMA with configurable periods
- **Simulation mode** — full paper trading with synthetic order IDs and simulated slippage; no real orders placed
- **Multi-bot concurrency** — multiple independent bot instances per client, each isolated by `botid`
- **Real-time streaming** — WebSocket log and event streaming from bot engine to frontend
- **JWT authentication** — API validates Netlify Identity JWT or static token; WebSocket ticket auth keeps JWT out of server logs
- **Configuration-driven** — all trading parameters, exchanges, symbols, and fees are JSON-file driven; no hardcoded values
- **Circuit breaker** — automatic halt after configurable consecutive failures with webhook alerting
- **Daily risk controls** — configurable max daily loss, max daily trades, max total exposure
- **Hot-reload parameters** — update trading parameters on running bots without restart, with rollback on validation failure

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        packages/web                         │
│              React 18 + Vite + TypeScript                   │
│         (Auth → WS Ticket → WebSocket + REST API)           │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│                        packages/api                         │
│              FastAPI + uvicorn (Python 3.11)                │
│     (JWT auth, rate limiting, REST endpoints, WS handler)   │
└──────────────────────┬──────────────────────────────────────┘
                       │ Python import (sonarft-bot)
┌──────────────────────▼──────────────────────────────────────┐
│                        packages/bot                         │
│                   Trading Engine (Python 3.11)              │
│  BotManager → SonarftBot → SonarftSearch → SonarftExecution │
│  SonarftPrices + SonarftIndicators + SonarftMath            │
│  SonarftApiManager (ccxtpro WebSocket / ccxt REST)          │
└──────────────────────┬──────────────────────────────────────┘
                       │ CCXT / ccxtpro
┌──────────────────────▼──────────────────────────────────────┐
│                     Crypto Exchanges                        │
│              OKX · Binance · Bitfinex · ...                 │
└─────────────────────────────────────────────────────────────┘

shared/types/api.ts ──► Single source of truth for API contract
                        (synced with packages/api/src/models/schemas.py)
```

---

## Package Overview

| Package | Language | Role |
|---|---|---|
| `packages/bot` | Python 3.11 | Pure trading engine — indicators, execution, CCXT. No HTTP, no auth. |
| `packages/api` | Python 3.11 | FastAPI service — REST endpoints, WebSocket, JWT auth, CORS, rate limiting. |
| `packages/web` | TypeScript 5 | React 18 + Vite frontend. Talks only to `packages/api`. |
| `shared/types` | TypeScript | API contract types shared between api (Pydantic) and web (TypeScript). |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20 LTS
- Docker + Docker Compose (for containerised deployment)

### Manual Setup (recommended for development)

```bash
# 1. First-time setup — creates .venv, installs all deps
make setup

# 2. Configure environment
cp packages/api/.env.example packages/api/.env
# Edit packages/api/.env — leave NETLIFY_SITE_URL and SONARFT_API_TOKEN empty for dev

# 3. Terminal 1: start the API server
source .venv/bin/activate
make dev-api

# 4. Terminal 2: start the web dev server
make dev-web
```

Services:
- Web: http://localhost:5173
- API: http://localhost:8000
- API docs: http://localhost:8000/api/v1/docs

> **Dev auth bypass:** `packages/web/.env.development` has `VITE_DEV_AUTH_BYPASS=true`
> pre-configured — the web app auto-injects a dev user so you can use the trading
> interface without any auth setup.

### Docker Compose

```bash
cp packages/api/.env.example packages/api/.env
cp packages/web/.env.development.example packages/web/.env.development

make dev   # starts all services with hot reload
```

---

## Development Commands

```bash
make help          # Show all commands
make setup         # First-time setup: create venv, install all deps
make install       # Re-install all dependencies (after pulling changes)
make dev-api       # Start API server with hot reload on :8000
make dev-web       # Start web dev server with HMR on :5173
make dev           # Start all services via Docker Compose
make test          # Run all tests (bot + api + web)
make test-bot      # Run bot tests only (pytest)
make test-api      # Run API tests only (pytest)
make test-web      # Run web tests only (Vitest)
make lint          # Lint all packages (ruff + eslint)
make build         # Build all Docker images
make build-web     # Build web production bundle
make clean         # Remove build artifacts and caches
make logs          # Tail Docker Compose logs
```

---

## Testing

| Package | Framework | Status |
|---|---|---|
| `packages/bot` | pytest + pytest-asyncio + Hypothesis | ✅ Passing |
| `packages/api` | pytest + pytest-asyncio | ✅ Passing (≥75% coverage) |
| `packages/web` | Vitest + RTL + MSW v2 | ✅ 110/110 passing |

```bash
make test          # all packages
make test-bot      # pytest packages/bot
make test-api      # pytest packages/api
make test-web      # vitest packages/web
```

---

## Tech Stack

| Layer | Key Technologies |
|---|---|
| Bot engine | Python 3.11, pandas 3.0, pandas-ta 0.4, ccxt/ccxtpro 4.5, asyncio |
| API server | FastAPI 0.135, uvicorn 0.44, Pydantic v2, PyJWT, slowapi, orjson |
| Web frontend | React 18, TypeScript 5, Vite 8, Recharts |
| Testing | pytest, pytest-asyncio, Hypothesis, Vitest, RTL, MSW v2, jest-axe |
| CI | GitHub Actions — test + lint + audit on push/PR to main/develop |
| Infrastructure | Docker, Docker Compose, nginx |

---

## Project Status

| Metric | Status |
|---|---|
| Web test suite | ✅ 110/110 passing |
| npm audit Critical/High | ✅ 0 |
| ESLint | ✅ 0 errors, 0 warnings |
| WebSocket auth | ✅ Ticket-based (JWT not in URL) |
| Live trading confirmation | ✅ Requires `SONARFT_ALLOW_LIVE=true` env var |
| Accessibility (WCAG AA) | ✅ Contrast, aria-live, focus-visible |
| CI pipeline | ✅ GitHub Actions on push/PR |

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/getting-started.md`](docs/getting-started.md) | Prerequisites, setup, environment variables, first run |
| [`docs/architecture.md`](docs/architecture.md) | Monorepo structure, data flow, trade lifecycle, concurrency model |
| [`docs/developer-guide.md`](docs/developer-guide.md) | Coding standards, async patterns, FastAPI conventions, React patterns |
| [`docs/configuration-guide.md`](docs/configuration-guide.md) | All config files, JSON examples, hot-reload, live trading safeguards |
| [`docs/api-guide.md`](docs/api-guide.md) | REST endpoints, WebSocket, auth, rate limiting, schemas |
| [`docs/bot-engine-guide.md`](docs/bot-engine-guide.md) | Trading engine internals, indicators, execution, simulation mode |
| [`docs/frontend-guide.md`](docs/frontend-guide.md) | React architecture, hooks, state machine, WebSocket integration |
| [`docs/testing-guide.md`](docs/testing-guide.md) | Test strategy, pytest, Vitest, MSW, property-based testing |
| [`docs/deployment-guide.md`](docs/deployment-guide.md) | Docker, production deployment, TLS, scaling, monitoring |
