---
Prompt ID: 13-BOT-INTEGRATION
Package: api & bot
Category: Cross-Package Integration
Difficulty: Medium
Time Estimate: 45-60 minutes
Run After: 01-API-ARCH
Can Run In Parallel With: 02-API-ENDPOINTS
Output Location: docs/integration/bot-api-integration.md
Last Updated: April 2026
Status: Draft
---

# Prompt 13 — Bot Package & API Integration Review

**Focus:** Review the `packages/bot` codebase and its integration with the `packages/api` layer. Identify IPC/subprocess flows, data contracts, and security boundaries.
**Deliverables:** Integration diagram, data contract table, security checklist, and prioritized recommendations
**Output File:** `docs/integration/bot-api-integration.md`
**Prerequisites:** Master Instruction + Prompt 01 + full monorepo uploaded (`packages/api`, `packages/bot`, `shared`, `schemas`)

---

## What This Prompt Does

Performs a targeted review of the bot implementation and how the API controls, observes, and receives data from bots. Key areas:

- IPC & Control Flow: subprocess, sockets, Redis, or internal queue usage
- Command API: start/stop/pause/resume flow and tracing from API endpoint to bot handler
- Data Contracts: Pydantic schemas, trade packets, status payloads shared between API and bot
- Security Boundaries: where secrets live, who can trigger bot actions, and privilege separation
- Telemetry & Observability: how bot metrics are emitted to API/WebSocket
- Concurrency & Async Patterns: threading, asyncio tasks, background workers
- Testing Coverage: unit and integration tests for bot behaviors and API integration

## Copy & Paste Into Your AI Chat

```text
# PROMPT 13: Bot Package & API Integration Review

Please analyze the `packages/bot` codebase and its integration points with `packages/api`.

1. Code Inventory
- List all major bot modules and classes (e.g., `sonarft_bot.py`, `sonarft_api_manager.py`, `sonarft_execution.py`, `sonarft_search.py`).
- For each, summarize responsibility and public methods used by the API.

2. IPC & Command Flow
- How does the API instruct the bot to start/stop/pause? Follow the call chain from API endpoint (cite file/path/line) to bot handler.
- Is subprocess used? If so, where are commands constructed and executed? Cite exact lines.
- Are internal queues or event buses used? Describe data structures and flow.

3. Data Contracts
- Identify shared schemas used for control and telemetry (trade packets, status events). Cite `shared/`, `packages/api/models`, and `packages/bot/models.py`.
- Where do Pydantic models diverge? List mismatches and potential serialization issues.

4. Security & Secrets
- Where are exchange API keys and secrets stored and used? (bot-side: `sonarft_api_manager.py` or config files)
- Are secrets passed via environment variables or persisted in files? Are they logged anywhere?
- Can API endpoints trigger dangerous bot actions without proper authorization?

5. Concurrency & Robustness
- How are long-running tasks managed? (asyncio tasks, background threads)
- Are exceptions in bot tasks surfaced to API or hidden? How are failures reported?

6. Observability
- How does the bot expose metrics or status? (WebSocket messages, logs, metrics endpoint)
- Are metrics correlated with API requests (trace IDs, request IDs)?

7. Tests
- Are there unit tests for critical bot functions? Are integration tests covering API<->bot flows?

8. Recommendations
- Provide prioritized remediation steps for mismatches, security gaps, and reliability issues.

Be explicit: cite file paths and line numbers whenever possible. If a requested artifact is not present, mark it as "⚠️ Not Found in Source Code".
```

---

## Expected Output

- Integration diagram (Mermaid)
- Control flow tracing (API endpoint → bot command handler → execution)
- Data contract table (schema name | location | used by)
- Security checklist (secrets, permissions, logging)
- Prioritized recommendations with code pointers

---

_Part of the sonarft API & Bot integration prompt suite_
