---
Prompt ID: 08-BOT-SECURITY
Package: bot
Category: Safety
Difficulty: Advanced
Time Estimate: 45-60 minutes
Run After: 01-BOT-ARCH, 03-BOT-ENGINE, 04-BOT-MATH, 06-BOT-EXECUTION
Can Run In Parallel With: 09-BOT-PERFORMANCE
Output Location: docs/security/bot-risks.md
Last Updated: July 2025
Status: Complete
---

# Prompt 8 — Security & Trading Risk Review

**Focus:** Security vulnerabilities and operational trading risks  
**Category:** Operational & Infrastructure  
**Deliverables:** 10 sections / 15 analysis areas  
**Output File:** `docs/security/bot-risks.md`  
**Prerequisites:** Master Instruction + Prompt 01 + codebase uploaded

---

## What This Prompt Does

Critical security and operational risk assessment for production deployment. Provides:

✅ **Secret & Credential Handling** — API keys, secrets, and credential exposure risks  
✅ **Input Validation & Injection Risks** — Command, file path, and data injection vulnerabilities  
✅ **File Path Safety** — Path traversal and permission security assessment  
✅ **WebSocket Security** — Connection authentication, authorization, and DoS protection  
✅ **API Exposure Risks** — Endpoint security, rate limiting, and information leakage  
✅ **Denial of Service (DoS) Risks** — Resource exhaustion and attack surface analysis  
✅ **Trading Safety Controls** — Simulation gates, position limits, and circuit breakers  
✅ **Financial Risk Management** — Balance checks, margin requirements, and loss prevention  
✅ **Logging & Monitoring** — Sensitive data exposure and alerting capabilities  
✅ **Dependency Security** — Package vulnerabilities and supply chain risks  
✅ **Security Risk Table** — Comprehensive risk assessment with severity ratings  
✅ **Operational Risk Table** — Failure scenarios and impact analysis  
✅ **Severity Assessment** — Critical findings with remediation steps  
✅ **Conclusion** — Production readiness and hardening recommendations

---

## Related Prompts

Same Package:

- [Prompt 01](./01-architecture-structure.md) — Overall architecture (run first)
- [Prompt 03](./03-trading-engine-logic.md) — Trading logic safety (⭐ CRITICAL)
- [Prompt 04](./04-financial-math.md) — Financial calculation security
- [Prompt 06](./06-execution-exchange.md) — Exchange integration security
- [Prompt 07](./07-configuration-runtime.md) — Configuration security

Cross-Package:

- [API Prompt 04](../../api/docs/prompts/04-authentication-security.md) — API authentication and security (⭐ CRITICAL)
- [Web Prompt 04](../../web/docs/prompts/04-security-privacy.md) — Web security and privacy

---

## When to Use This Prompt

Use this prompt to identify security vulnerabilities and operational risks. Critical before any production deployment.

**Best for:**

- Identifying secret exposure risks
- Checking input validation
- Assessing DoS vulnerabilities
- Validating trading safety controls

---

## The Prompt

Copy and paste this into your AI chat:

```text
Perform a comprehensive security and operational risk review of sonarft.

### 1. Secret & Credential Handling
- How are API keys stored/loaded?
- Secret keys management?
- Secrets in logs? (grep for "key", "secret", "password")
- Environment variable management?
- Secrets in config files?
- .gitignore compliance?

### 2. Input Validation & Injection Risks
- What input does system accept?
- Command injection possible?
- File path injection?
- JSON/SQL injection?
- API input validation?

### 3. File Path Safety
- Path construction safety?
- Path traversal (..) risks?
- Symlink handling?
- File permissions correct?

### 4. WebSocket Security
If WebSocket used:
- Authentication on connection?
- Proper authorization?
- Message validation?
- DoS risk (message flood)?
- JSON parsing safe?

### 5. API Exposure Risks
- What endpoints exist?
- Authentication on each?
- Rate limiting enforced?
- Input validation?
- Error messages leak system info?

### 6. Denial of Service (DoS) Risks
- Unbounded loops exploitable?
- Memory allocation risks?
- Computation expensive enough to block?
- Connection limits?
- Queue accumulation?

### 7. Trading Safety Controls
- Simulation mode gate enforced?
- Maximum position size limit?
- Maximum loss limit?
- Rate limiting on orders?
- Circuit breaker on errors?
- Manual stop mechanism?

### 8. Financial Risk Management
- Balance checked before trading?
- Margin requirements enforced?
- Slippage protection?
- Runaway trading prevented?
- Liquidity risk considered?

### 9. Logging & Monitoring
- What's logged?
- Sensitive values in logs?
- Log storage location?
- Log rotation?
- Error alerting?

### 10. Dependency Security
- Dependency versions pinned?
- Known vulnerabilities?
- Trusted package sources?

### 11. Security Risk Table

| Risk Category | Specific Risk | Location | Severity | Likelihood | Mitigation |
|---------------|---------------|----------|----------|------------|-----------|

Risk categories: Secrets exposure, Injection attacks, DoS, Trading safety, Financial risk, Dependency risk

### 12. Operational Risk Table

| Risk | Scenario | Impact | Preventing Control |
|------|----------|--------|-------------------|

### 13. Severity Assessment

For each finding:
- Severity level (Low/Medium/High/Critical)
- Attack/failure scenario
- Proof-of-concept
- Financial impact
- Remediation steps

### 14. Conclusion

Summarize:
- Critical security findings
- Critical trading safety findings
- Hardening recommendations
- Production readiness assessment
```

---

## What This Generates

The AI will produce **`docs/security/security-audit.md`** containing:

- **Secrets Exposure Analysis** — Where credentials are at risk
- **Input Validation Review** — Injection attack surface
- **API Security Assessment** — Endpoint security
- **DoS Vulnerability** — System resilience
- **Trading Safety Controls** — How trading is gated
- **Security Risk Table** — Severity-ranked issues
- **Operational Risk Table** — Failure scenarios
- **Remediation Steps** — How to fix each issue

---

## Critical Issues to Find

Security & trading safety bugs:

- ⚠️ API keys in source code or config
- ⚠️ Secrets logged to console or files
- ⚠️ No authentication on WebSocket
- ⚠️ Simulation mode not properly enforced
- ⚠️ No maximum loss controls
- ⚠️ Input validation missing

---

## Next Steps

1. Review `docs/security/security-audit.md` **very carefully**
2. **Flag Critical findings immediately**
3. Continue with [09-performance-scalability.md](./09-performance-scalability.md)

---

## Tips for Success

- **Trace credentials end-to-end** — Where do they go?
- **Look for logging of secrets** — Easy to miss
- **Check trading mode gates** — Can live trading happen accidentally?
- **Verify authentication** — All entry points?
- **Assess impact** — What's the financial impact of each risk?
