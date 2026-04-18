---
Prompt ID: 07-BOT-CONFIG
Package: bot
Category: Operations
Difficulty: Beginner
Time Estimate: 20-30 minutes
Run After: 01-BOT-ARCH
Can Run In Parallel With: 08-BOT-SECURITY, 09-BOT-PERFORMANCE, 10-BOT-QUALITY
Output Location: docs/operations/bot-config.md
Last Updated: April 2026
Status: Complete
---

# Prompt 07 — Configuration & Runtime Environment Review

**Focus:** Configuration system and runtime safety  
**Category:** Operational & Infrastructure  
**Deliverables:** 7 sections / 10 analysis areas  
**Output File:** `docs/operations/bot-config.md`  
**Prerequisites:** Master Instruction + Prompt 01 + codebase uploaded

---

## What This Prompt Does

Comprehensive audit of configuration system and runtime environment safety. Provides:

✅ **Configuration File Structure** — Format, schema, validation, and parameter inventory  
✅ **Configuration Loading Behavior** — File locations, environment overrides, and fallbacks  
✅ **Per-Bot & Per-Client Configuration** — Bot isolation and inheritance rules  
✅ **Environment Variable Usage** — Required/optional variables and security assessment  
✅ **Defaults & Hardcoding Audit** — Unsafe defaults and hardcoded value identification  
✅ **Docker Runtime Assumptions** — Container setup, volumes, and entrypoint validation  
✅ **File Paths & History Storage** — Path safety, permissions, and storage locations  
✅ **Path Safety & Traversal Risks** — Path traversal and symlink vulnerability assessment  
✅ **Configuration Validation** — Schema validation, type checking, and error messages  
✅ **Configuration Issues Table** — Problems with severity ratings and remediation  
✅ **Runtime Configuration Summary** — Safety assessment and recommendations  
✅ **Docker Configuration Review** — Production readiness and security assessment  
✅ **Conclusion** — Configuration maturity and hardening recommendations

---

## Related Prompts

Same Package:

- [Prompt 01](./01-architecture-structure.md) — Overall architecture (run first)
- [Prompt 08](./08-security-risk.md) — Security implications of configuration
- [Prompt 09](./09-performance-scalability.md) — Configuration impact on performance

Cross-Package:

- [API Prompt 07](../../api/docs/prompts/07-database-persistence.md) — API configuration and database setup
- [Web Prompt 07](../../web/docs/prompts/07-testing.md) — Web configuration and environment setup

---

## When to Use This Prompt

Use this prompt to audit configuration handling and runtime environment setup. Important for ensuring safe deployment.

**Best for:**

- Verifying configuration validation
- Checking hardcoded values
- Assessing runtime safety
- Validating defaults

---

## The Prompt

Copy and paste this into your AI chat:

```text
Audit the configuration system and runtime environment handling in sonarft.

### 1. Configuration File Structure
- Format (JSON, YAML, Python dict?)
- Schema (validation present?)
- Examples provided?
- Parameter documentation?
- Defaults defined?

Create table of all configuration parameters:

| Parameter | Required | Type | Default | Purpose | Validation |
|-----------|----------|------|---------|---------|------------|

### 2. Configuration Loading Behavior
- Entry point for config loading
- Expected file locations
- Environment variable overrides
- Merge behavior for multiple configs
- Fallback behavior if config missing

### 3. Per-Bot & Per-Client Configuration
If supported:
- What can be configured per-bot vs globally?
- Inheritance from global config?
- Conflict resolution?
- Bot isolation?

### 4. Environment Variable Usage
- Which are required (API keys, secrets?)
- Which are optional?
- Defaults when missing?
- Security (secrets logged?)

### 5. Defaults & Hardcoding Audit
Search for:
- Hardcoded values (should be config?)
- Unsafe defaults (could cause problems?)
- Missing parameters (all needed params in config?)

### 6. Docker Runtime Assumptions
- Base image appropriateness
- Working directory
- Config file location for Docker
- Environment setup
- Volume usage
- Entrypoint command

### 7. File Paths & History Storage
- Relative vs absolute paths
- Path construction safety
- Permission requirements
- Trade history storage location
- Log file rotation

### 8. Path Safety & Traversal Risks
- User-supplied paths controllable?
- Path traversal risks (..)?
- Symlink handling
- File permission safety

### 9. Configuration Validation
- Schema validation present?
- Type checking?
- Range validation for numeric params?
- Dependency validation (if A=X then B must=Y)?
- Clear error messages?

### 10. Configuration Issues Table

| Issue | Location | Type | Severity | Remediation |
|-------|----------|------|----------|------------|

### 11. Runtime Configuration Summary

| Aspect | Current Method | Safe? | Recommendation |
|--------|----------------|-------|-----------------|

### 12. Docker Configuration Review
- Dockerfile production-ready?
- docker-compose correct?
- Container security (non-root user?)
- Secrets handling safe?

### 13. Conclusion
Assess:
- Configuration system maturity
- Safety of defaults
- Production readiness
- Hardening recommendations
```

---

## What This Generates

The AI will produce **`docs/configuration/config-review.md`** containing:

- **Configuration Inventory** — All parameters documented
- **Loading Behavior** — How config is loaded and merged
- **Validation Assessment** — Schema and type checking
- **Defaults Review** — What happens with missing config
- **Issues Table** — Configuration problems identified
- **Docker Review** — Container configuration assessment
- **Recommendations** — How to improve configuration safety

---

## Common Issues Found

Configuration bugs:

- ⚠️ Hardcoded API endpoints or parameters
- ⚠️ No schema validation for config
- ⚠️ Unsafe defaults (e.g., simulation=false)
- ⚠️ Secrets in config files or logs
- ⚠️ Missing configuration options

---

## Next Steps

1. Review `docs/configuration/config-review.md`
2. Continue with [08-security-risk.md](./08-security-risk.md)
