# Prompt 5 — Real-time Updates & WebSocket Integration

**Focus:** WebSocket communication, real-time data handling, connection management  
**Category:** Real-time Communication  
**Output File:** `docs/real-time/websocket-integration.md`  
**Run After:** [02-api-integration.md](./02-api-integration.md), [03-state-management.md](./03-state-management.md)  
**Time Estimate:** 20-30 minutes  
**Prerequisites:** Understand API and state management

---

## When to Use This Prompt

Use this prompt to analyze how the app handles WebSocket connections for real-time updates. Review connection lifecycle, event handling, and data synchronization.

**Best for:**
- Understanding real-time data flow
- Debugging WebSocket issues
- Improving connection resilience
- Optimizing real-time performance
- Identifying data sync issues

---

## The Prompt

Copy and paste this into your AI chat:

```text
Analyze the WebSocket integration in sonarftweb and how the app handles real-time updates from sonarft.

Cover the following areas:

### 1. WebSocket Architecture

Examine the WebSocket setup:
- **Library/Approach:** What WebSocket library is used (native WebSocket, Socket.io, etc.)?
- **Connection setup:** How is the WebSocket connection established?
- **URL/Endpoint:** What WebSocket endpoint is connected to?
- **Authentication:** How is the WebSocket connection authenticated?
- **Configuration:** Is the connection configurable per environment?
- **Singleton pattern:** Is there a single connection or multiple?

### 2. Connection Lifecycle

Analyze connection management:
- **Connection:** How is the connection established on app startup?
- **Reconnection:** How does the app reconnect if the connection drops?
- **Retry logic:** Is there exponential backoff or similar?
- **Cleanup:** How is the connection closed on app unmount?
- **Event listeners:** Are listeners properly cleaned up?
- **Memory leaks:** Could there be memory leaks from listeners?

### 3. WebSocket Events

Document all WebSocket events:
- **Event name:** What is the event called?
- **Data structure:** What data is sent with the event?
- **Handler location:** Which component(s) handle this event?
- **Frequency:** How often is this event fired?
- **Response action:** What happens when this event is received?
- **State update:** How does the app update state from this event?

Create a table:

| Event Name | Data Structure | Handler | Frequency | State Update |
|------------|---|---------|-----------|--------------|
| | | | | |

### 4. Real-time Data Integration

Analyze how real-time data is processed:
- **Data parsing:** How is WebSocket data parsed?
- **Validation:** Is data validated before use?
- **Merging:** How is real-time data merged with existing state?
- **Conflicts:** How are conflicts between real-time and API data handled?
- **Ordering:** Are events processed in order?
- **Deduplication:** Are duplicate events prevented?

### 5. Error Handling & Resilience

Examine error handling:
- **Connection errors:** How are WebSocket errors caught?
- **Parse errors:** How are malformed messages handled?
- **Timeout:** Is there a timeout for expecting data?
- **Retry:** Are failed operations retried?
- **Graceful degradation:** Does the app work without WebSocket?
- **User notification:** Are connection issues shown to the user?

### 6. Performance

Review real-time performance:
- **Message frequency:** How many messages per second?
- **Payload size:** How large are WebSocket messages?
- **Throttling:** Is message handling throttled?
- **Batching:** Are multiple updates batched?
- **UI updates:** Do WebSocket updates cause excessive re-renders?
- **Memory:** Is memory growing with active WebSocket?

### 7. Testing & Mocking

Examine testing approach:
- **Test helpers:** How are WebSocket events mocked in tests?
- **Test scenarios:** Are connection/reconnection scenarios tested?
- **Event mocking:** Can events be simulated for testing?
- **Test data:** Is there mock WebSocket data?

### 8. Real-time Features Using WebSocket

For each real-time feature, document:
- **Feature name:** What real-time feature is this?
- **Events used:** Which WebSocket events are used?
- **Data flow:** How does data flow from WebSocket to UI?
- **Use cases:** When/how is this used?

Examples might include:
- Live price updates
- Trade execution confirmations
- Bot status changes
- Account balance updates
- Order fill notifications

### 9. Debugging & Monitoring

Review debugging capabilities:
- **Logging:** Are WebSocket events logged?
- **DevTools:** Can WebSocket messages be inspected?
- **Metrics:** Are connection metrics tracked?
- **Errors reported:** Are WebSocket errors reported/logged?

### 10. Comparison with REST API

Compare WebSocket vs REST API usage:
- **Data freshness:** Why was WebSocket chosen for certain data?
- **Latency:** Is WebSocket lower latency than REST polling?
- **Bandwidth:** Is WebSocket more efficient than polling?
- **Complexity:** Is WebSocket complexity justified?
- **Fallback:** What happens if WebSocket isn't available?

### 11. Data Consistency

Analyze consistency:
- **Race conditions:** Can race conditions occur between REST and WebSocket?
- **State sync:** How is state synchronized between sources?
- **Conflict resolution:** How are conflicts resolved?
- **Last-write-wins:** Is there a consistent conflict strategy?

### 12. Scalability

Review scalability:
- **Connection pooling:** Is connection pooling needed?
- **Broadcast limitations:** Can the server broadcast to all clients?
- **Message ordering:** Is ordering guaranteed?
- **Backpressure:** How is backpressure handled?

### 13. WebSocket Integration Diagram

Create a Mermaid diagram showing:
- WebSocket connection between client and sonarft
- Events flowing in each direction
- How events trigger state updates
- Relationship with REST API
```

---

## After Running This Prompt

The AI should produce a document covering:
- **WebSocket architecture and setup**
- **Connection lifecycle management**
- **Event inventory and handling**
- **Real-time data integration**
- **Error handling and resilience**
- **Performance characteristics**
- **Testing and mocking strategies**
- **Data consistency**
- **Recommendations for improvement**

**Save to:** `docs/real-time/websocket-integration.md`

**Related Prompts:**
- [02-api-integration.md](./02-api-integration.md) — REST API for comparison
- [03-state-management.md](./03-state-management.md) — State updates from events
- [08-performance-optimization.md](./08-performance-optimization.md) — Performance tuning

---

## Key Areas to Focus On

1. **Connection Resilience:** Proper reconnection logic
2. **Memory Leaks:** Event listener cleanup
3. **Data Consistency:** Race conditions between REST/WebSocket
4. **Error Handling:** Connection failure recovery
5. **Performance:** Message handling efficiency
