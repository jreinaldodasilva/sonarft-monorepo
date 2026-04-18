---
Prompt ID: 02-BOT-ASYNC
Package: bot
Category: Design
Difficulty: Advanced
Time Estimate: 30-45 minutes
Run After: 01-BOT-ARCH
Can Run In Parallel With: 03-BOT-ENGINE, 04-BOT-MATH, 05-BOT-INDICATORS
Output Location: docs/async/bot-concurrency.md
Last Updated: July 2025
Status: Complete
---

# Prompt 02 — Async Design & Concurrency Review

**Focus:** Async/await correctness and concurrency safety  
**Category:** Architecture & Design  
**Deliverables:** 7 sections / 15 analysis areas  
**Output File:** `docs/async/bot-concurrency.md`  
**Prerequisites:** Master Instruction + Prompt 01 + codebase uploaded

---

## What This Prompt Does

Comprehensive analysis of async/await correctness and concurrency safety. Provides:

✅ **Async/Await Correctness** — Every async function reviewed for proper awaiting and blocking operations  
✅ **Task Management Analysis** — Task creation, cleanup, and lifecycle management  
✅ **Concurrency Synchronization** — Shared state, locks, and race condition detection  
✅ **Async/Await Error Handling** — Exception propagation and recovery patterns  
✅ **Concurrency Risk Table** — All concurrency concerns with severity ratings  
✅ **Task Lifecycle Summary** — Complete task management documentation  
✅ **Concurrency Flow Diagram** — Mermaid diagram of async execution patterns  
✅ **Recommendations** — Critical bugs and best-practice improvements

---

## Related Prompts

Same Package:

- [Prompt 01](./01-architecture-structure.md) — Overall architecture (run first)
- [Prompt 03](./03-trading-engine-logic.md) — Trading logic execution
- [Prompt 09](./09-performance-scalability.md) — Performance impact of concurrency

Cross-Package:

- [API Prompt 01](../../api/docs/prompts/01-architecture-structure.md) — API async patterns
- [Web Prompt 05](../../web/docs/prompts/05-real-time-updates.md) — WebSocket concurrency

---

## When to Use This Prompt

Use this prompt to verify async/await correctness and identify concurrency risks. Critical for a system designed for multi-bot concurrency.

**Best for:**

- Verifying async safety
- Finding race conditions
- Checking task lifecycle management
- Validating error handling in async code

---

## The Prompt

Copy and paste this into your AI chat:

```text
Review all async behavior in the sonarft codebase.

Focus on these critical async patterns and risks:

### 1. Async/Await Correctness

Examine every async function and report:
- **Async function name** and location
- **What it does** (one sentence)
- **Awaited calls** (list every await, confirm it's awaited properly)
- **Non-awaited coroutines** (are any coroutines created but not awaited?)
- **Blocking operations inside async functions** (file I/O, network calls, expensive computation)
- **Risk level** (None / Low / Medium / High)

Common issues to find:
- Creating async tasks/coroutines without `await` or `.create_task()`
- Calling thread-blocking functions (time.sleep, blocking file I/O) inside async code
- No exception handling for task creation/awaiting
- Tasks that never complete or garbage-collect
- Race conditions on shared state

### 2. Task Management Analysis

Examine:
- **Task creation patterns** (asyncio.create_task, gather, etc.)
- **Task cleanup** (are tasks cancelled and awaited on shutdown?)
- **Dangling tasks** (any tasks that may be abandoned?)
- **Task cancellation handling** (CancelledError caught and handled?)
- **Long-running loops** (any while True loops? Do they yield control?)

### 3. Concurrency Synchronization

Check:
- **Shared mutable state** (what global/class variables are shared?)
- **Lock usage** (asyncio.Lock for critical sections?)
- **Deadlock risks** (any scenarios where locks could deadlock?)
- **Race conditions** (any concurrent access to shared data without locks?)
- **WebSocket message concurrency** (how are concurrent messages handled?)

### 4. Async/Await Error Handling

Verify:
- Are exceptions in tasks propagated or silently lost?
- Are timeout scenarios handled?
- Is connection loss handled gracefully?
- Can the system recover from failed async operations?

### 5. Concurrency Risk Table

Create a table of all concurrency concerns:

| Location | Pattern | Risk | Severity | Remediation |
|----------|---------|------|----------|------------|

### 6. Task Lifecycle Summary

Document:
- How tasks are created
- How they are monitored
- When they are cancelled
- How they are cleaned up
- Any edge cases in the lifecycle

### 7. Concurrency Flow Diagram

Create a Mermaid sequence or flowchart showing:
- Typical execution flow
- Where concurrency occurs
- Task creation and joining points
- Critical sections

### 8. Recommendations

Identify:
- Critical async bugs
- Refactoring opportunities
- Best-practice improvements
```

---

## What This Generates

The AI will produce **`docs/architecture/async-concurrency.md`** containing:

- **Async Function Inventory** — All async functions with risk assessment
- **Task Management Review** — How tasks are created, monitored, and cleaned up
- **Concurrency Risk Table** — All identified concurrency issues
- **Flow Diagrams** — Visual representation of async execution patterns
- **Remediation Recommendations** — How to fix identified issues

---

## Expected Findings

Common issues in trading systems:

- ⚠️ Tasks not properly cleaned up on shutdown
- ⚠️ Race conditions on shared state (balances, prices)
- ⚠️ Exception handling gaps in async code
- ⚠️ Blocking calls inside async function

---

## Next Steps

After this prompt completes:

1. Review `docs/architecture/async-concurrency.md`
2. Move to [03-trading-engine-logic.md](./03-trading-engine-logic.md) — Trading logic (CRITICAL)
3. Or continue with other prompts in order

---

## Tips for Success

- **Pay attention to concurrency issues** — They're hard to debug in production
- **Check shared state** — Especially order books, balances, trade lists
- **Look for task cleanup** — Shutdown should cancel all pending tasks
- **Verify locks** — Critical sections should be protected
