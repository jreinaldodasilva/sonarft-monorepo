# SonarFT Monorepo

**System Oscillator for Navigation and Ranging in Financial Trade**

A three-layer monorepo separating the trading engine, API backend, and React frontend into independent, deployable packages.

---

## Architecture

```
sonarft-monorepo/
├── packages/
│   ├── bot/        # Python — core trading engine (indicators, execution, CCXT)
│   ├── api/        # Python — FastAPI REST + WebSocket backend
│   └── web/        # TypeScript — React frontend (Vite)
├── shared/
│   └── types/      # api.ts — single source of truth for API contract
├── infra/
│   ├── docker-compose.yml      # Production orchestration
│   └── docker-compose.dev.yml  # Development overrides (hot reload)
├── Makefile        # Top-level dev commands
└── docs/           # Architecture decisions, API docs
```

### Layer responsibilities

| Package        | Language    | Role                                                                        |
| -------------- | ----------- | --------------------------------------------------------------------------- |
| `packages/bot` | Python 3.11 | Pure trading engine — no HTTP, no auth. Importable as `sonarft-bot`.        |
| `packages/api` | Python 3.11 | FastAPI service — REST endpoints, WebSocket, JWT auth, CORS, rate limiting. |
| `packages/web` | TypeScript  | React 18 + Vite frontend. Talks only to `packages/api`.                     |
| `shared/types` | TypeScript  | API contract types shared between `api` (Pydantic) and `web` (TypeScript).  |

---

## 📚 Code Review Prompts Documentation

Comprehensive AI-assisted code review prompt suites for each package. Perfect for:

- **Production readiness assessment** — Is the system ready to deploy?
- **Security audits** — Find all security issues across the stack
- **Performance reviews** — Can it scale to thousands of users?
- **Integration verification** — Do all components work together correctly?
- **Team onboarding** — Understanding the entire system architecture

### Getting Started with Prompts

**New to AI code reviews?** Start here:

1. **[🚀 Usage Guide](./docs/PROMPTS_USAGE_GUIDE.md)** — Practical techniques for better results (15 min)
2. **[📖 Master Guide](./docs/PROMPTS_MASTER_GUIDE.md)** — Complete overview (10 min)
3. **[🎯 Cross-Package Guide](./CROSS_PACKAGE_NAVIGATION.md)** — How to review full stack (5 min)
4. **Pick a package below** and follow its quick-start guide

### By Package

| Package & Link                             | Focus                       | Quick Audit | Complete Audit |
| ------------------------------------------ | --------------------------- | ----------- | -------------- |
| **[🤖 Bot](./packages/bot/docs/prompts/)** | Trading engine & indicators | 30 min      | 2-3 hrs        |
| **[🔗 API](./packages/api/docs/prompts/)** | REST + WebSocket backend    | 30 min      | 2-3 hrs        |
| **[⚛️ Web](./packages/web/docs/prompts/)** | React frontend              | 30 min      | 2-3 hrs        |

**Each package includes:**

- ✅ Quick-start guide (5 min read)
- ✅ Master instruction with AI context
- ✅ 10 core domain-specific prompts
- ✅ Consolidation & roadmap templates
- ✅ Best practices reference

### Popular Review Paths

- **🚀 Quick Check (30 min)** → Run Prompt 10 in any package
- **🔍 Deep Dive (2-3 hours)** → Complete audit in one package
- **🎯 Full-Stack Review (6-8 hours)** → Bot → API → Web sequence
- **🔒 Security Focus (2 hours)** → Prompt 04 in all packages (CRITICAL)
- **🏭 Pre-Deployment (4-5 hours)** → Complete audit in all packages (parallel)

### Quick Reference

- **[📇 Prompt Index](./docs/PROMPTS_INDEX.md)** — Find prompts by goal/technology
- **[📋 Implementation Guide](./IMPLEMENTATION_GUIDE.md)** — How we improved the prompts
- **[✅ Status Doc](./PROMPT_IMPROVEMENTS_STATUS.md)** — Current progress

### Prompt Suite Statistics

- **Total Files:** 49 prompt documents + 6 navigation guides
- **🤖 Bot Package:** 17 prompts covering trading logic, indicators, execution, security
- **🔗 API Package:** 15 prompts covering architecture, endpoints, WebSocket, performance
- **⚛️ Web Package:** 15 prompts covering components, hooks, styling, integration
- **⏱️ Total Review Time:** 6-8 hours (one package) or 12-18 hours (full-stack with 3 reviewers in parallel)

[→ Learn more in the Master Guide](./docs/PROMPTS_MASTER_GUIDE.md)

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose

### Option 1 — Docker (recommended)

```bash
# Copy and configure environment
cp packages/api/.env.example packages/api/.env
cp packages/web/.env.development.example packages/web/.env.development

# Start all services
make dev
```

Services:

- API: http://localhost:8000
- API Docs: http://localhost:8000/api/v1/docs
- Web: http://localhost:5173

### Option 2 — Manual

```bash
# Install all dependencies
make install

# Terminal 1: API server
make dev-api

# Terminal 2: Web dev server
make dev-web
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive docs: `http://localhost:8000/api/v1/docs`

### Endpoints

| Method | Path                     | Description          |
| ------ | ------------------------ | -------------------- |
| GET    | `/health`                | Service health check |
| GET    | `/bots?client_id=`       | List bot IDs         |
| POST   | `/bots?client_id=`       | Create new bot       |
| POST   | `/bots/{botId}/run`      | Start bot            |
| POST   | `/bots/{botId}/stop`     | Stop bot             |
| DELETE | `/bots/{botId}`          | Remove bot           |
| GET    | `/bots/{botId}/orders`   | Order history        |
| GET    | `/bots/{botId}/trades`   | Trade history        |
| GET    | `/parameters/defaults`   | Default parameters   |
| GET    | `/parameters?client_id=` | Client parameters    |
| PUT    | `/parameters?client_id=` | Update parameters    |
| GET    | `/indicators/defaults`   | Default indicators   |
| GET    | `/indicators?client_id=` | Client indicators    |
| PUT    | `/indicators?client_id=` | Update indicators    |
| WS     | `/ws/{clientId}?token=`  | Real-time stream     |

### Authentication

Set `NETLIFY_SITE_URL` for Netlify Identity JWT validation, or `SONARFT_API_TOKEN` for static token auth. If neither is set, auth is disabled (development only).

---

## Development Commands

```bash
make help          # Show all commands
make install       # Install all dependencies
make dev           # Start all services (Docker, hot reload)
make dev-api       # Start API only
make dev-web       # Start web only
make test          # Run all tests
make build         # Build Docker images
make lint          # Lint all packages
make clean         # Remove build artifacts
```

---

## Environment Variables

### `packages/api/.env`

| Variable              | Default                     | Description                         |
| --------------------- | --------------------------- | ----------------------------------- |
| `NETLIFY_SITE_URL`    | —                           | Netlify site URL for JWT validation |
| `SONARFT_API_TOKEN`   | —                           | Static token fallback               |
| `CORS_ORIGINS`        | `http://localhost:3000,...` | Allowed CORS origins                |
| `MAX_BOTS_PER_CLIENT` | `5`                         | Max concurrent bots per client      |
| `DATA_DIR`            | `sonarftdata`               | Path to bot data directory          |

### `packages/web/.env.development`

| Variable               | Default                         | Description                   |
| ---------------------- | ------------------------------- | ----------------------------- |
| `VITE_API_URL`         | `http://localhost:8000/api/v1`  | API base URL                  |
| `VITE_WS_URL`          | `ws://localhost:8000/api/v1/ws` | WebSocket base URL            |
| `VITE_VITALS_URL`      | —                               | Web Vitals reporting endpoint |
| `VITE_IDLE_TIMEOUT_MS` | `1800000`                       | Session idle timeout (ms)     |
