---
Prompt ID: 08-API-PERF
Package: api
Category: Performance
Difficulty: Advanced
Time Estimate: 45-60 minutes
Run After: 01-API-ARCH, 07-API-DB
Can Run In Parallel With: 09-API-TESTING
Output Location: docs/performance/performance-optimization.md
Last Updated: July 2025
Status: Complete
---

# Prompt 08 — Performance Optimization & Scalability Review

**Focus:** API performance bottlenecks, caching strategies, and scalability limits  
**Category:** Performance & Scalability  
**Deliverables:** 10 sections / 12 analysis areas  
**Output File:** `docs/performance/performance-optimization.md`  
**Prerequisites:** Master Instruction + Prompt 01 + codebase uploaded

---

## What This Prompt Does

Comprehensive API performance analysis with optimization opportunities and scalability evaluation. Provides:

✅ **Current Performance Baseline** — Request/response times and throughput metrics  
✅ **Async/Concurrency Model** — FastAPI async usage and parallelization opportunities  
✅ **Caching Strategy** — Data caching implementation and invalidation patterns  
✅ **Database Query Optimization** — Query performance and N+1 problem identification  
✅ **WebSocket Scalability** — Concurrent connection limits and backpressure handling  
✅ **Bot Engine Integration** — Subprocess communication and async bot management  
✅ **Resource Utilization** — Memory/CPU usage and resource leak prevention  
✅ **HTTP/API Efficiency** — Response compression and HTTP caching headers  
✅ **Serialization Performance** — JSON/binary format efficiency and payload optimization  
✅ **Bottleneck Analysis** — Performance bottleneck identification and impact assessment  
✅ **Load Testing** — Concurrent user handling and graceful degradation  
✅ **Infrastructure Scaling** — Horizontal scaling and load balancing capabilities  
✅ **Dependency Performance** — External API calls and timeout handling  
✅ **Configuration & Optimization Knobs** — Connection pools and batch processing tuning  
✅ **Concerns & Recommendations** — Performance bottlenecks and optimization suggestions

---

## Related Prompts

Same Package:

- [Prompt 01](./01-architecture-structure.md) — Overall architecture performance characteristics
- [Prompt 05](./05-websocket-realtime.md) — WebSocket performance that affects overall API perf
- [Prompt 07](./07-database-persistence.md) — Database performance that impacts API

Cross-Package:

- [Bot Prompt 09](../../bot/docs/prompts/09-performance-monitoring.md) — Bot performance that this API serves
- [Web Prompt 08](../../web/docs/prompts/08-performance-monitoring.md) — Web performance that depends on this API

---

## Copy & Paste Into Your AI Chat

```text
# PROMPT 08: Performance Optimization & Scalability Review

Please review the sonarft API for performance characteristics, optimization opportunities, and scalability.

## 1. Current Performance Baseline
Assess current performance:
- What are typical request/response times?
- Are there performance benchmarks or metrics?
- What is the current throughput (requests/sec)?
- Are there any known slow endpoints?
- What is typical resource utilization (CPU, memory)?

## 2. Async/Concurrency Model
Review async implementation:
- Is FastAPI's async model properly used?
- Are blocking operations awaited?
- Are there any sync operations in async handlers?
- Could operations be parallelized?
- Are there deadlocks or race conditions?

## 3. Caching Strategy
Analyze caching:
- What data is cached? (if anything)
- Is caching used for expensive operations?
- Is cache invalidation correct?
- Could more aggressive caching help?
- Is there cache warming?
- Could Redis or similar be beneficial?

## 4. Database Query Optimization
Review query performance:
- Are queries optimized?
- Are there N+1 query problems?
- Are indexes used?
- Are complex joins avoidable?
- Could query results be cached?

## 5. WebSocket Scalability
If WebSocket is used:
- How many concurrent connections can be handled?
- Is there backpressure handling?
- Are messages efficiently serialized?
- Could broadcasting be optimized?
- Is memory usage per connection acceptable?

## 6. Bot Engine Integration
Review bot interaction:
- How is the bot engine invoked from API?
- Are subprocess calls blocking?
- Could bot communication be async?
- Is there timeout handling for bot calls?
- Could parallel bot management help?

## 7. Resource Utilization
Analyze resource usage:
- What is memory footprint?
- Is there memory leaks?
- What is CPU utilization under load?
- Are resources properly released?
- Could connection pooling help?

## 8. HTTP/API Efficiency
Review HTTP usage:
- Are responses compressed (gzip)?
- Are large payloads unnecessarily large?
- Could pagination reduce response size?
- Are HTTP caches used (Cache-Control headers)?
- Is HTTP/1.1 sufficient or would HTTP/2 help?

## 9. Serialization Performance
Analyze data serialization:
- What serialization format is used? (JSON, Orjson, etc.)
- Is serialization a bottleneck?
- Could binary formats help?
- Are there unnecessary fields in responses?
- Could response size be reduced?

## 10. Bottleneck Analysis
Identify performance bottlenecks:
- Where does time go? (database, bot engine, serialization)
- What operations are slowest?
- What would have highest ROI if optimized?
- Are there external API calls that are slow?

## 11. Load Testing
Review load testing:
- Has the API been load tested?
- What happens at 10, 100, 1000 concurrent users?
- Are there graceful degradation mechanisms?
- Is there rate limiting?
- Are there circuit breakers?

## 12. Infrastructure Scaling
Assess scalability:
- Can the API scale horizontally? (run multiple instances)
- Are there stateless vs stateful components?
- Is there load balancing?
- Can the database scale?
- Could microservices help?

## 13. Dependency Performance
Review external dependencies:
- Are external API calls slow?
- Is timeout handling appropriate?
- Could caching reduce external calls?
- Are dependencies efficient?

## 14. Configuration & Optimization Knobs
Check for tuning:
- Can connection pool size be adjusted?
- Can timeouts be tuned?
- Are there batch settings?
- Could batch processing improve throughput?

## 15. Concerns & Recommendations
- Identify performance bottlenecks
- Quantify impact of optimizations
- Suggest quick wins vs long-term improvements
- Rate impact: Low/Medium/High
- Provide optimization examples

## Output Format

Generate a Markdown document including:
- Executive Summary
- Performance Baseline Assessment
- Bottleneck Analysis with Mermaid diagram
- Async/Concurrency Review
- Caching Opportunities
- Database Query Analysis
- WebSocket Scalability Assessment
- Load Test Recommendations
- Optimization Opportunities (quick wins first)
- Recommendations (with estimated impact)
- Before/After optimization examples
- Performance Monitoring Checklist

Be specific about endpoints, operations, and expected performance metrics.
```

---

## Expected Output

A comprehensive performance and scalability review that includes:

- Bottleneck identification
- Optimization opportunities ranked by impact
- Scaling capability assessment
- Load testing strategy
- Performance monitoring plan

---

## How to Use the Output

1. Save the generated document to `docs/performance/08-performance-optimization.md`
2. Implement quick-win optimizations first
3. Set up performance monitoring
4. Conduct load testing
5. Plan infrastructure scaling
6. Establish performance baselines

---

## Related Prompts

After this prompt, consider:

- [Prompt 7: Database Persistence](./07-database-persistence.md) — Database performance
- [Prompt 5: WebSocket Real-Time](./05-websocket-realtime.md) — WebSocket performance
- [Prompt 9: Testing & Quality](./09-testing-quality.md) — Performance testing

---

_Part of the sonarft API Code Review Prompt Suite_
