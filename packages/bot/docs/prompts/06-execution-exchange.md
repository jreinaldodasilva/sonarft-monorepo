---
Prompt ID: 06-BOT-EXECUTION
Package: bot
Category: Safety
Difficulty: Advanced
Time Estimate: 45-60 minutes
Run After: 01-BOT-ARCH, 03-BOT-ENGINE, 05-BOT-INDICATORS
Can Run In Parallel With: 07-BOT-CONFIG, 08-BOT-SECURITY
Output Location: docs/trading/execution-review.md
Last Updated: April 2026
Status: Complete
---

# Prompt 06 — Execution & Exchange Integration Review

**Focus:** Order execution and exchange API integration  
**Category:** Trading Logic & Safety  
**Deliverables:** 9 sections / 14 analysis areas  
**Output File:** `docs/trading/execution-review.md`  
**Prerequisites:** Master Instruction + Prompt 01 + codebase uploaded

---

## What This Prompt Does

Critical review of order execution and exchange API integration safety. Provides:

✅ **API Abstraction Layer** — Exchange connection management and method routing  
✅ **Transport Layer Options** — WebSocket vs REST usage and failover logic  
✅ **Market Data Fetching** — Order book, ticker, and volume data retrieval  
✅ **Order Placement Logic** — Order parameters, validation, and confirmation  
✅ **Simulated Order Execution** — Simulation mode accuracy and realism  
✅ **Partial Fill Handling** — Partial order tracking and position management  
✅ **Error Handling & Retries** — Connection and API error recovery  
✅ **Order Cancellation & Cleanup** — Open order management and shutdown behavior  
✅ **Exchange-Specific Assumptions** — Per-exchange requirements and quirks  
✅ **API Abstraction Matrix** — Method coverage and error handling table  
✅ **Execution Flow Diagram** — Mermaid flowchart of complete trade execution  
✅ **Failures & Edge Cases Table** — Risk assessment for failure scenarios  
✅ **Conclusion** — Production readiness and critical issue summary

---

## Related Prompts

Same Package:

- [Prompt 01](./01-architecture-structure.md) — Overall architecture (run first)
- [Prompt 03](./03-trading-engine-logic.md) — Trading decisions that trigger execution
- [Prompt 08](./08-security-risk.md) — Security implications of exchange integration
- [Prompt 09](./09-performance-scalability.md) — Execution performance and rate limits

Cross-Package:

- [API Prompt 02](../../api/docs/prompts/02-api-endpoints-design.md) — API endpoints for bot control
- [API Prompt 05](../../api/docs/prompts/05-websocket-realtime.md) — WebSocket streaming to API
- [Web Prompt 05](../../web/docs/prompts/05-real-time-updates.md) — Real-time execution display

---

## When to Use This Prompt

Use this prompt to verify exchange integration and order execution safety. Critical for ensuring trades execute correctly on real exchanges.

**Best for:**

- Verifying API abstraction layer
- Checking order placement logic
- Validating error handling
- Assessing exchange integration safety

---

## The Prompt

Copy and paste this into your AI chat:

```text
Review the exchange integration and order execution path in sonarft.

### 1. API Abstraction Layer

Examine:
- **API Manager class** (what does it do?)
- **Exchange instances** (how are exchange connections created?)
- **Library abstraction** (does code abstract away ccxt/ccxtpro differences?)
- **Method routing** (how are API methods chosen and called?)
- **Error handling** (how are API errors handled?)

### 2. Transport Layer Options

Document:
- **WebSocket usage** (for which operations? Which exchanges?)
- **REST fallback** (does REST fallback work when WebSocket fails?)
- **Automatic failover** (is failover automatic or manual?)
- **Reconnection logic** (how is reconnection handled?)
- **Message ordering** (are messages processed in order?)

### 3. Market Data Fetching

Review:
- **Order book fetch** (how is it fetched? How often?)
- **Ticker data** (how is current price obtained?)
- **Volume data** (how is volume for indicators obtained?)
- **Data staleness** (is data age considered?)
- **API rate limits** (are API limits respected?)

### 4. Order Placement Logic

Examine:
- **Order parameters** (how is amount, price, side specified?)
- **Order validation** (pre-flight checks?)
- **Order placement** (REST vs WebSocket?)
- **Order confirmation** (how is success verified?)
- **Failures** (what happens if order placement fails?)

### 5. Simulated Order Execution

For simulation mode, verify:
- **Simulated fills** (how are orders marked as filled?)
- **Partial fills** (are partial fills simulated correctly?)
- **Slippage** (is slippage modeled?)
- **Order timing** (when are orders marked filled relative to signals?)
- **Accuracy** (are simulations realistic?)

### 6. Partial Fill Handling

Check:
- **Partial fill detection** (is code aware of partial fills?)
- **Position tracking** (is filled amount tracked?)
- **Remaining amount** (is remainder handled correctly?)
- **Exit behavior** (does partial fill affect exit logic?)

### 7. Error Handling & Retries

Examine:
- **Connection errors** (timeout, network down, etc.)
- **API errors** (rate limit, invalid order, etc.)
- **Retry logic** (is there exponential backoff? Max retries?)
- **Silent failures** (could orders execute silently without confirmation?)
- **Error logging** (are errors logged for debugging?)

### 8. Order Cancellation & Cleanup

Review:
- **Order cancellation** (how are open orders cancelled?)
- **Exit cleanup** (are all exit orders placed and confirmed?)
- **Stale orders** (are old unmatched orders cleaned up?)
- **Shutdown behavior** (what happens to open orders on shutdown?)

### 9. Exchange-Specific Assumptions

For each supported exchange:
- **Minimum amounts** (are they enforced?)
- **Precision rules** (amount and price precision?)
- **Fee structure** (maker vs taker, understood?)
- **Limits** (rate limits, concurrent connections?)
- **Quirks** (any edge behaviors?)

### 10. API Abstraction Matrix

Create a table:

| Operation | Method Name | CCXT | CCXTpro | Error Handling | Tested |
|-----------|------------|------|---------|----------------|--------|

Operations: Fetch order book, Fetch ticker, Fetch OHLCV, Place order, Cancel order, Fetch balance, Fetch order status

### 11. Execution Flow Diagram

Create a Mermaid flowchart:
- Signal generated → Validation → Order placement → Confirmation → Tracking → Exit

### 12. Failures & Edge Cases Table

| Scenario | Handling | Risk | Severity |
|----------|----------|------|----------|

Scenarios to cover:
- Exchange down, API rate limit, Order partially filled, Order rejected, Network timeout, WebSocket disconnect, Duplicate order, Insufficient balance

### 13. Conclusion

Summarize:
- Exchange integration safety
- Critical issues found
- Production readiness assessment
```

---

## What This Generates

The AI will produce **`docs/trading/execution-analysis.md`** containing:

- **API Abstraction Review** — How exchanges are integrated
- **Transport Layer Analysis** — WebSocket vs REST usage
- **Order Placement Review** — How orders are placed and confirmed
- **Error Handling Assessment** — What happens when things fail
- **Simulation Accuracy** — How realistic simulations are
- **Failure Scenarios** — How the system handles edge cases
- **Execution Flow Diagram** — Visual representation of execution path

---

## Common Issues Found

Exchange integration bugs:

- ⚠️ No fallback from WebSocket to REST
- ⚠️ Silent order placement failures
- ⚠️ Insufficient data validation before trading
- ⚠️ Partial fills not handled correctly
- ⚠️ Stale data used for trading decisions

---

## Next Steps

1. Review `docs/trading/execution-analysis.md`
2. Continue with [07-configuration-runtime.md](./07-configuration-runtime.md)

---

## Tips for Success

- **Trace order end-to-end** — From decision to confirmation
- **Check simulation realism** — Does simulation match real exchange behavior?
- **Verify error recovery** — What happens when API fails?
- **Look for silent failures** — Can orders execute without confirmation?
- **Check cancellation** — Are open orders properly cleaned up?
