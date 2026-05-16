Use the following prompt to instruct an AI agent or technical writer to generate complete setup, configuration, onboarding, architecture, and developer documentation for the SonarFT monorepo.

---

# Prompt — Create Setup, Configuration and Developer Guides for SonarFT Monorepo

You are a senior software architect and technical documentation engineer.

Your task is to create complete, production-quality technical documentation for the **SonarFT monorepo**, covering setup, installation, architecture, development workflows, configuration, operations, deployment, and contributor onboarding.

The output must be written as if it will become the official `/docs` documentation for the repository.

The documentation must be practical, implementation-aware, and aligned with the architecture and engineering conventions described below.

---

# Project Overview

SonarFT (System Oscillator for Navigation and Ranging in Financial Trade) is an automated cryptocurrency trading platform composed of three independent packages in a monorepo:

| Package        | Language              | Role                                        |
| -------------- | --------------------- | ------------------------------------------- |
| `packages/bot` | Python 3.11           | Trading engine, indicators, execution, CCXT |
| `packages/api` | Python 3.11           | FastAPI backend, REST + WebSocket           |
| `packages/web` | TypeScript / React 18 | Frontend UI                                 |
| `shared/types` | TypeScript            | Shared API contract types                   |

The system supports:

- Multi-exchange crypto trading
- Simulation and live trading
- Technical indicators (RSI, MACD, SMA, EMA, StochRSI, VWAP)
- WebSocket streaming
- Multi-bot concurrency
- JWT authentication
- Docker deployment
- Real-time logs and metrics
- JSON-driven configuration

The architecture is:

- Async-first
- Modular OOP
- Dependency-injected
- Configuration-driven
- Multi-tenant
- Production-ready

---

# Documentation Goals

Generate documentation that allows:

1. A new developer to fully set up the monorepo locally
2. A contributor to understand the architecture quickly
3. An operator to run the stack in development and production
4. A maintainer to understand conventions and patterns
5. A developer to extend the bot, API, or frontend safely
6. A DevOps engineer to deploy and troubleshoot the platform

The documentation must feel enterprise-grade and suitable for a professional open-source repository.

---

# Required Documentation Structure

Generate the documentation as multiple markdown documents with clear sections.

Include the following documents:

---

## 1. README.md

Create a top-level README including:

- What SonarFT is
- Core capabilities
- High-level architecture diagram (ASCII or Mermaid)
- Package overview
- Quick start
- Development commands
- Docker setup
- Testing
- Tech stack summary
- Screenshots/placeholders
- Links to deeper docs

---

## 2. docs/getting-started.md

Include:

- Prerequisites
- Python setup
- Node setup
- Virtual environment setup
- Installing dependencies
- Monorepo bootstrap
- Environment variables
- Starting API
- Starting frontend
- Running bot locally
- Running Docker Compose
- Hot reload workflows
- Troubleshooting common startup issues

---

## 3. docs/architecture.md

Document:

- Monorepo architecture
- Package responsibilities
- Layered architecture
- Dependency graph
- Data flow
- WebSocket flow
- Trade execution lifecycle
- Configuration lifecycle
- Multi-bot concurrency model
- Simulation mode design
- Shared type synchronization
- API ↔ frontend interaction
- Runtime storage structure
- Logging architecture
- Metrics pipeline

Include Mermaid diagrams where useful.

---

## 4. docs/developer-guide.md

Create a deep developer guide covering:

### Coding Standards

Use the exact SonarFT conventions:

- Module headers
- Logger injection
- Async patterns
- Type annotations
- Dependency injection
- Naming conventions
- Error handling
- Financial precision
- Simulation mode guards
- Config loading patterns

### Python Standards

Explain:

- asyncio usage
- asyncio.gather
- asyncio.Lock
- stop event pattern
- retry/backoff
- resource cleanup
- exception handling

### FastAPI Standards

Explain:

- application factory
- lifespan
- middleware
- request IDs
- security headers
- WebSocket auth
- rate limiting

### React Standards

Explain:

- hooks organization
- state management
- reducers
- RAF batching
- shared API contracts
- integration layer

### Git Workflow

Define:

- branch naming
- PR standards
- lint/test requirements
- commit conventions

---

## 5. docs/configuration-guide.md

Document every config file:

- config.json
- config_parameters.json
- config_exchanges.json
- config_symbols.json
- config_fees.json
- config_indicators.json
- config_markets.json

Explain:

- purpose
- structure
- example values
- validation
- runtime loading
- hot reload
- rollback behavior
- live trading safeguards

Include complete JSON examples.

---

## 6. docs/api-guide.md

Document:

- FastAPI structure
- REST endpoints
- WebSocket endpoints
- Authentication
- JWT flow
- WebSocket ticket auth
- Error handling
- Rate limiting
- Request IDs
- Response schemas
- Shared types strategy

Include example requests/responses.

---

## 7. docs/bot-engine-guide.md

Explain the trading engine in depth.

Document:

- SonarftBot lifecycle
- BotManager
- Trade search orchestration
- Price analysis
- Indicators
- VWAP calculations
- Profit calculations
- Spread validation
- Order execution
- Simulation mode
- Exchange abstraction
- Trade history persistence
- Metrics collection

Explain how modules collaborate internally.

---

## 8. docs/frontend-guide.md

Document:

- React architecture
- Vite setup
- Component organization
- Hooks
- API integration
- WebSocket integration
- Redux usage
- Chart rendering
- State transitions
- Authentication flow
- Mock testing with MSW

---

## 9. docs/testing-guide.md

Explain:

- pytest
- pytest-asyncio
- Vitest
- MSW
- accessibility testing
- property-based testing
- integration testing
- mocking exchange APIs
- testing async systems
- CI workflow

Include commands and examples.

---

## 10. docs/deployment-guide.md

Document:

- Docker Compose
- Development containers
- Production deployment
- Reverse proxy
- TLS
- Environment variables
- Scaling multiple bots
- Persistent volumes
- Logging
- Monitoring
- Backup strategy
- Security hardening

---

# Technical Constraints

The documentation MUST align with the following implementation details.

---

# Important Implementation Details

## Async-First Architecture

All I/O is async.

Patterns used:

- `asyncio.gather`
- `asyncio.Lock`
- `asyncio.Event`
- async WebSockets
- async file I/O

Explain WHY these patterns are used.

---

## Dependency Injection

Modules never self-instantiate dependencies.

All modules receive:

- logger
- api_manager
- peer modules

through constructors.

`SonarftBot.initialize_modules()` is the wiring root.

---

## Configuration-Driven Design

All trading behavior is controlled by JSON config files.

Never imply hardcoded trading parameters.

---

## Simulation Mode

Simulation mode gates all real order execution.

Explain:

- execution branching
- fake order IDs
- simulated fills/slippage
- safety mechanisms

---

## Financial Precision

Financial math uses:

```python
from decimal import getcontext
getcontext().prec = 28
```

Explain why decimal precision matters.

---

## Logging Standards

Use:

```python
self.logger = logger or logging.getLogger(__name__)
```

Never use `print()`.

Explain:

- request IDs
- metrics logs
- rotating files
- structured JSON logs

---

## Middleware Stack

Document:

- GZipMiddleware
- SlowAPIMiddleware
- SecurityHeadersMiddleware
- AccessLogMiddleware
- RequestIdMiddleware
- CORSMiddleware

Explain ordering and purpose.

---

## Shared Types

`shared/types/api.ts` is the single source of truth.

Must stay synchronized with:
`packages/api/src/models/schemas.py`

Explain the workflow and risks.

---

# Style Requirements

The generated documentation must:

- Be highly structured
- Use markdown headings properly
- Include tables
- Include code blocks
- Include JSON examples
- Include shell commands
- Include diagrams
- Include troubleshooting sections
- Include best practices
- Include operational notes
- Include warnings/cautions
- Be technically precise
- Avoid vague generic explanations
- Explain WHY patterns exist, not only WHAT they are

---

# Output Requirements

Generate:

- Production-quality markdown
- Clear navigation structure
- Cross-links between docs
- Consistent terminology
- Consistent formatting
- Enterprise-grade documentation tone

Assume the audience includes:

- Backend developers
- Frontend developers
- Quant/trading developers
- DevOps engineers
- Contributors
- Operators

Do NOT produce shallow summaries.

Produce detailed technical documentation suitable for a real production repository.
