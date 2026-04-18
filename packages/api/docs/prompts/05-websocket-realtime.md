# WebSocket Real-Time Data Streaming Review Prompt

**Prompt:** 05-websocket-realtime  
**Time:** 30-45 minutes  
**Output:** Markdown document in `docs/websocket/`  
**Prerequisites:** [Master Instruction](./00-master-instruction.md)

---

## What This Prompt Does

Analyzes WebSocket implementation, real-time communication, connection management, and message handling. You'll get:

- WebSocket endpoint design review
- Connection lifecycle assessment
- Message format and protocol analysis
- Broadcasting and subscription strategy
- Error handling in real-time context
- Performance and scalability considerations

---

## Copy & Paste Into Your AI Chat

```text
# PROMPT 05: WebSocket Real-Time Data Streaming Review

Please review the WebSocket implementation in the sonarft API and evaluate its design for real-time communication.

## 1. WebSocket Endpoint Design
Analyze the WebSocket endpoint (if implemented):
- What is the WebSocket URL/path?
- How are connections initiated?
- Is authentication required for WebSocket connections?
- Are there separate endpoints for different data types (trades, status, etc.)?

## 2. Connection Management (websocket/manager.py)
Review the WebSocketManager:
- How are connections tracked? (data structure used)
- How are connections registered and unregistered?
- Is there connection pooling?
- Are stale connections cleaned up?
- What happens when a connection drops?

## 3. Message Protocol
Analyze the message format:
- What is the message structure? (JSON, binary, etc.)
- Are there different message types? (subscribe, unsubscribe, data, error)
- Is the protocol documented?
- Are message versioning strategies in place?
- Can the protocol evolve without breaking clients?

## 4. Subscription & Filtering
Review subscription management:
- How do clients subscribe to data streams?
- Can clients filter which data they receive?
- Is there a subscription confirmation?
- Can subscriptions be dynamic (changed after connection)?
- Are unsubscription/cleanup working properly?

## 5. Broadcasting Strategy
Analyze how data is broadcast:
- How does the server know what to broadcast?
- Are all clients receiving same data or filtered data?
- How is bot-specific data handled? (client A sees bot A data, not bot B)
- What happens when multiple clients request same data?
- Is broadcasting efficient? (no redundant sends)

## 6. Error Handling in WebSocket
Review error scenarios:
- How are errors communicated over WebSocket?
- Are disconnections handled gracefully?
- How does the client know a connection failed?
- Are error details appropriately detailed?
- Is there automatic reconnection guidance?

## 7. Performance & Scalability
Assess performance characteristics:
- How many concurrent connections can be handled?
- What is the message throughput?
- Are there backpressure mechanisms? (buffer limits)
- Is there connection timeout handling?
- Could 100 concurrent clients cause issues?

## 8. Memory & Resource Management
Check for resource leaks:
- Are old connections properly cleaned up?
- Is memory allocated per connection? How much?
- Are there memory leaks with long-running connections?
- Is there a maximum connection limit?

## 9. Testing Coverage
Review WebSocket testing:
- Are WebSocket connections tested?
- Are failure scenarios tested? (disconnection, slow client)
- Are multiple concurrent connections tested?
- Is message ordering verified?
- Are edge cases covered? (large messages, rapid subscriptions)

## 10. Integration with Application
Check integration:
- How does WebSocket manager get data?
- Is there a callback system for broadcasting?
- How does WebSocket server communicate with bot engine?
- Are there race conditions between WebSocket and REST endpoints?

## 11. Client Expectations
Consider the frontend (sonarftweb) perspective:
- How should clients handle connection drops?
- What reconnection strategy should they use?
- How should they handle message ordering?
- What error messages will they receive?

## 12. Concerns & Recommendations
- Identify scaling limitations
- Suggest performance improvements
- Recommend error handling enhancements
- Rate severity: Low/Medium/High
- Provide implementation examples

## Output Format

Generate a Markdown document including:
- Executive Summary
- WebSocket Architecture Diagram
- Message Protocol Specification
- Connection Lifecycle Diagram
- Performance Analysis
- Scalability Assessment
- Issues Found (with severity)
- Recommendations (prioritized, with code examples)
- Client Integration Guide

Be specific about websocket/manager.py implementation and message formats used.
```

---

## Expected Output

A comprehensive WebSocket review that includes:

- Message protocol specification
- Connection management assessment
- Scalability analysis
- Identified limitations and issues
- Performance optimization recommendations

---

## How to Use the Output

1. Save the generated document to `docs/websocket/05-websocket-realtime.md`
2. Review scalability limits and plan for growth
3. Improve error handling and resilience
4. Share message protocol spec with frontend team
5. Plan performance testing

---

## Related Prompts

After this prompt, consider:

- [Prompt 8: Performance Optimization](./08-performance-optimization.md) — WebSocket performance
- [Prompt 6: Error Handling & Logging](./06-error-handling-logging.md) — WebSocket errors
- [Prompt 1: Architecture Structure](./01-architecture-structure.md) — WebSocket integration

---

_Part of the sonarft API Code Review Prompt Suite_
