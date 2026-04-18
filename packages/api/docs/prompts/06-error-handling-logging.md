---
Prompt ID: 06-API-ERRORS
Package: api
Category: Operations
Difficulty: Medium
Time Estimate: 30-45 minutes
Run After: 01-API-ARCH
Can Run In Parallel With: 07-API-DB
Output Location: docs/error-handling/error-handling-logging.md
Last Updated: April 2026
Status: Complete
---

# Prompt 06 — Error Handling, Logging & Observability Review

**Focus:** Error handling patterns, logging strategies, and system observability  
**Category:** Error Handling & Logging  
**Deliverables:** 8 sections / 10 analysis areas  
**Output File:** `docs/error-handling/error-handling-logging.md`  
**Prerequisites:** Master Instruction + Prompt 01 + codebase uploaded

---

## What This Prompt Does

Comprehensive error handling and logging analysis with observability evaluation. Provides:

✅ **Exception Hierarchy** — Custom exception organization and inheritance patterns  
✅ **Error Handlers** — Exception-to-HTTP response conversion and status codes  
✅ **Logging Coverage** — Operation logging completeness and level appropriateness  
✅ **Structured Logging** — JSON/key-value format usage and correlation IDs  
✅ **Sensitive Information in Logs** — Security audit for credential and PII exposure  
✅ **Error Response Format** — Client error response consistency and detail level  
✅ **Logging Configuration** — Startup configuration and runtime level changes  
✅ **Exception Context** — Context preservation and stack trace handling  
✅ **Timeout & Retry Handling** — External call timeouts and exponential backoff  
✅ **Graceful Degradation** — Transient error recovery and circuit breaker patterns  
✅ **Debugging Support** — Error traceability and troubleshooting information  
✅ **Performance Impact** — Logging overhead and blocking operation assessment  
✅ **Compliance & Standards** — API standards compliance and audit trail maintenance  
✅ **Concerns & Recommendations** — Missing logging and improvement suggestions

---

## Related Prompts

Same Package:

- [Prompt 01](./01-architecture-structure.md) — Overall architecture error handling patterns
- [Prompt 04](./04-authentication-security.md) — Security-related error handling
- [Prompt 05](./05-websocket-realtime.md) — WebSocket error handling

Cross-Package:

- [Bot Prompt 06](../../bot/docs/prompts/06-error-recovery.md) — Bot error recovery that this API handles
- [Web Prompt 06](../../web/docs/prompts/06-error-boundaries.md) — Web error boundaries that consume API errors

---

## Copy & Paste Into Your AI Chat

````text
# PROMPT 06: Error Handling, Logging & Observability Review

Please review error handling, logging, and observability across the sonarft API.

## 1. Exception Hierarchy
Review custom exceptions (core/errors.py):
- What custom exceptions are defined?
- Is the exception hierarchy clear and well-organized?
- Do all exceptions inherit from appropriate base classes?
- Are exception names descriptive?
- Are there redundant or overlapping exceptions?

Example questions:
- Is BotNotFoundError distinct from BotLimitExceededError?
- Are there generic exceptions when specific ones would help?
- Could exception hierarchy be flattened or restructured?

## 2. Error Handlers
Analyze error handling mechanisms:
- What error handlers are registered? (bot_not_found_handler, etc.)
- How do handlers convert exceptions to HTTP responses?
- Are error status codes appropriate?
- Is error information detailed enough for debugging?
- Is error information safe (no security leakage)?

## 3. Logging Coverage
Review logging throughout the codebase:
- Are critical operations logged? (bot start, stop, errors)
- Are database operations logged?
- Are API requests/responses logged?
- Are WebSocket events logged?
- Is logging level (DEBUG, INFO, WARNING, ERROR) appropriate?

## 4. Structured Logging
Check for structured logging patterns:
- Are logs using structured format (JSON, key-value)?
- Or just plain text?
- Are correlation IDs used to track requests?
- Are context variables logged (user, request_id, bot_id)?

## 5. Sensitive Information in Logs
Critical security check:
- Are passwords logged anywhere?
- Are API keys logged?
- Are tokens logged?
- Are user credentials exposed?
- Is there PII in logs?
- Are database connection strings exposed?

## 6. Error Response Format
Review error responses to clients:
- What is the standard error response format?
- Are errors consistent across all endpoints?
- Do errors include error codes/identifiers?
- Is error detail level appropriate?
- Are validation errors clearly described?

Example error formats:
```json
{
  "error": "Bot not found",
  "code": "BOT_NOT_FOUND",
  "status": 404
}
````

## 7. Logging Configuration

Review logging setup:

- Is logging configured at startup (main.py)?
- Can log level be changed at runtime?
- Are different log levels for different modules?
- Is log rotation configured?
- Is log storage/persistence implemented?

## 8. Exception Context

Check for exception context preservation:

- Are exceptions caught and re-raised with context?
- Are stack traces preserved?
- Are underlying causes preserved (exception chaining)?
- Is debugging information available in logs?

## 9. Timeout & Retry Handling

Review timeout and retry strategies:

- Are timeouts set for external calls?
- Are retries implemented? With exponential backoff?
- Are retry attempts logged?
- Is there a limit on retries?
- Do timeouts generate meaningful errors?

## 10. Graceful Degradation

Check error recovery:

- Can the API recover from transient errors?
- Are there circuit breakers or bulkheads?
- What happens when the bot engine is unavailable?
- How are partial failures handled?

## 11. Debugging Support

Evaluate debuggability:

- Are errors traceable to source?
- Is there enough context to diagnose issues?
- Can support staff understand errors from logs?
- Are there request/response logs for troubleshooting?

## 12. Performance Impact

Check logging performance:

- Could excessive logging slow down the API?
- Are there any synchronous logging calls that block requests?
- Is there any risk of log file filling disk?

## 13. Compliance & Standards

- Do errors comply with API standards?
- Are logs maintainable long-term?
- Is there audit trail for compliance?

## 14. Concerns & Recommendations

- Identify missing logging
- Suggest error handling improvements
- Recommend additional observability
- Rate severity: Low/Medium/High
- Provide implementation examples

## Output Format

Generate a Markdown document including:

- Executive Summary
- Exception Hierarchy Diagram
- Logging Strategy Assessment
- Error Response Examples (good and bad)
- Sensitive Information Audit
- Logging Coverage Matrix
- Issues Found (with severity)
- Recommendations (with code examples)
- Logging Best Practices Guide

Be specific about files, line numbers, and log statements.

```

---

## Expected Output

A comprehensive error handling and observability review that includes:
- Exception hierarchy and patterns
- Logging coverage assessment
- Security audit for sensitive information
- Debugging effectiveness evaluation
- Recommendations for observability improvements

---

## How to Use the Output

1. Save the generated document to `docs/error-handling/06-error-handling.md`
2. Review sensitive information findings - fix immediately
3. Add missing logging for critical operations
4. Implement structured logging
5. Establish centralized log management
6. Create dashboards for monitoring

---

## Related Prompts

After this prompt, consider:
- [Prompt 4: Authentication & Security](./04-authentication-security.md) — Security logging
- [Prompt 8: Performance Optimization](./08-performance-optimization.md) — Logging performance
- [Prompt 9: Testing & Quality](./09-testing-quality.md) — Error handling tests

---

*Part of the sonarft API Code Review Prompt Suite*
```
