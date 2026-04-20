# sonarft API Code Review & Development Prompt Suite

A comprehensive framework for conducting structured AI-assisted code reviews and development guidance for the SonarFT FastAPI backend service.

**sonarft API** is a FastAPI-based backend service that provides RESTful and WebSocket endpoints for the sonarft cryptocurrency trading system. It enables:

- Bot lifecycle management and control (start, stop, pause)
- Real-time trading data and metrics streaming
- WebSocket integration for live market updates
- Configuration management and deployment
- Security through JWT token authentication
- Health monitoring and system status
- Integration with the trading bot engine via inter-process communication

---

## Quick Navigation

### 🚀 Getting Started

- **New to this suite?** Start with [Quick Start Guide](./00-quick-start-guide.md)
- **Want context?** Read [Master Instruction](./00-master-instruction.md) first
- **Multi-package review?** See [Monorepo Prompt Suite Overview](#cross-package-reference)

### 📋 Choose Your Review Path

| Your Goal             | Time      | Path                    |
| --------------------- | --------- | ----------------------- |
| Quick health check    | 30 min    | Quick Audit             |
| Comprehensive review  | 2-3 hours | Complete Audit          |
| Production deployment | 4-5 hours | Production Ready        |
| Specific area review  | 30-60 min | Pick individual prompts |

### 🔍 Individual Prompts by Category

**Foundation (Read First)**

- [Master Instruction](./00-master-instruction.md) — Shared context for all reviews
- [Quick Start Guide](./00-quick-start-guide.md) — How to use this suite

**API Architecture & Design**

- [01-architecture-structure.md](./01-architecture-structure.md) — API structure, module organization, and integration points
- [02-api-endpoints-design.md](./02-api-endpoints-design.md) — RESTful endpoint design, routing, and API contracts
- [03-data-models-validation.md](./03-data-models-validation.md) — Pydantic models, validation rules, and serialization

**Integration & Communication**

- [04-authentication-security.md](./04-authentication-security.md) — JWT authentication, authorization, and security controls
- [05-websocket-realtime.md](./05-websocket-realtime.md) — WebSocket implementation, real-time data streaming, and message handling
- [06-error-handling-logging.md](./06-error-handling-logging.md) — Error handling strategies, logging, and observability

**Infrastructure & Operations**

- [07-database-persistence.md](./07-database-persistence.md) — Data persistence, database design, and query optimization
- [08-performance-optimization.md](./08-performance-optimization.md) — API performance, caching, rate limiting, and scalability

**Quality & Maintenance**

- [09-testing-quality.md](./09-testing-quality.md) — Testing strategy, unit/integration tests, and test coverage
- [10-code-quality-python.md](./10-code-quality-python.md) — Python best practices, code organization, and maintainability

**Post-Review Documents**

- [11-final-consolidation.md](./11-final-consolidation.md) — Executive summary of all findings
- [12-implementation-roadmap.md](./12-implementation-roadmap.md) — Prioritized action items and improvement plan
- [99-best-practices.md](./99-best-practices.md) — FastAPI and Python best practices reference

---

## How to Use This Suite

### Step 1: Prepare Your AI Chat

1. Start a new conversation with your AI (Claude, ChatGPT, etc.)
2. Paste the [Master Instruction](./00-master-instruction.md)
3. Wait for AI to acknowledge (it will confirm it understands the context)

### Step 2: Upload the Codebase

Upload sonarft API source files:

- All Python source files (src/)
- API endpoints (api/v1/endpoints/)
- Core modules (core/)
- Services (services/)
- Models and schemas (models/)
- WebSocket manager (websocket/)
- Configuration files (pyproject.toml, requirements.txt)
- Docker configuration (Dockerfile, docker-compose.yml)

### Step 3: Run a Specific Prompt

1. Go to the prompt file you want (e.g., [01-architecture-structure.md](./01-architecture-structure.md))
2. Copy the prompt text
3. Paste into your AI chat
4. AI generates documentation

### Step 4: Save Output

Each prompt specifies output location. Organize in `docs/` folder:

```
docs/
├── architecture/
├── endpoints/
├── models/
├── security/
├── websocket/
├── error-handling/
├── database/
├── performance/
└── testing/
```

---

## Recommended Review Paths

### Quick Assessment (30 minutes)

Use only [Prompt 10](./10-code-quality-python.md) for a rapid health check

### Complete System Audit (2-3 hours)

Run prompts in this order:

1. [Prompt 1](./01-architecture-structure.md) — Get overview
2. [Prompts 2-10](./02-api-endpoints-design.md) — Detailed reviews (any order)

### Production Readiness (4-5 hours)

1. Complete all 10 prompts (Prompts 1-10)
2. Run [Final Consolidation](./11-final-consolidation.md)
3. Generate [Implementation Roadmap](./12-implementation-roadmap.md)
4. Review [Best Practices](./99-best-practices.md)

### Security-First Review (2 hours)

1. [Prompt 4: Authentication & Security](./04-authentication-security.md)
2. [Prompt 6: Error Handling & Logging](./06-error-handling-logging.md)
3. [Prompt 1: Architecture Overview](./01-architecture-structure.md)

### Operations/Deployment Focus

Skip reviews, go directly to setup guides and operational documentation

---

## Document Organization

```
prompts/
├── README.md (this file)
├── 00-quick-start-guide.md
├── 00-master-instruction.md
├── 01-architecture-structure.md
├── 02-api-endpoints-design.md
├── 03-data-models-validation.md
├── 04-authentication-security.md
├── 05-websocket-realtime.md
├── 06-error-handling-logging.md
├── 07-database-persistence.md
├── 08-performance-optimization.md
├── 09-testing-quality.md
├── 10-code-quality-python.md
├── 11-final-consolidation.md
├── 12-implementation-roadmap.md
├── 13-bot-package-review.md
└── 99-best-practices.md
```

---

## Key Features

- **Modular**: Each prompt is independent and can be used separately
- **Clear Dependencies**: Master instruction provides shared context for all prompts
- **Flexible**: Pick individual prompts or follow complete workflows
- **Professional**: Each document follows the same high-quality structure
- **Production-Focused**: Emphasis on reliability, security, and performance
- **Integrated**: References to bot and web packages for full system understanding

- **Cross-Package Review**: Use `13-bot-package-review.md` to examine the `packages/bot` implementation and its integration with the API. Ensure reviewers upload the full monorepo for this review.

---

## Cross-Package Reference

The sonarft monorepo contains three main components. This suite focuses on the API layer:

| Package | Documentation                                   | Role                                                    |
| ------- | ----------------------------------------------- | ------------------------------------------------------- |
| **Bot** | [Bot Prompts](../../bot/docs/prompts/README.md) | Trading engine, strategy execution, indicators          |
| **API** | [API Prompts](./README.md)                      | FastAPI backend, endpoint management, real-time updates |
| **Web** | [Web Prompts](../../web/docs/prompts/README.md) | React frontend, UI components, client integration       |

For **full-stack reviews**, follow this sequence:

1. Start with [Bot Prompts](../../bot/docs/prompts/) to understand the trading logic
2. Review [API Prompts](./README.md) to understand backend integration
3. Review [Web Prompts](../../web/docs/prompts/) for frontend-backend alignment
4. Run cross-package consolidation to ensure consistency across layers

---

## Getting Help

- **Unsure which prompt to use?** Check [Recommended Review Paths](#recommended-review-paths)
- **Want quick overview?** Read [Quick Start Guide](./00-quick-start-guide.md)
- **Need API context?** Read [Master Instruction](./00-master-instruction.md)
- **Looking for best practices?** See [Best Practices Guide](./99-best-practices.md)

---

_Last updated: July 2025_
_Part of the sonarft monorepo documentation suite_
