---
Prompt ID: 07-API-DB
Package: api
Category: Data
Difficulty: Medium
Time Estimate: 30-45 minutes
Run After: 01-API-ARCH
Can Run In Parallel With: 06-API-ERRORS
Output Location: docs/database/database-persistence.md
Last Updated: July 2025
Status: Complete
---

# Prompt 07 — Database, Persistence & Data Storage Review

**Focus:** Data persistence strategies, database design, and query patterns  
**Category:** Database & Persistence  
**Deliverables:** 8 sections / 10 analysis areas  
**Output File:** `docs/database/database-persistence.md`  
**Prerequisites:** Master Instruction + Prompt 01 + codebase uploaded
**Important:** Include `packages/bot` in the uploaded sources. Verify bot state persistence and any bot-side database interactions (trade history, config persistence) for schema compatibility and transactional safety.

---

## What This Prompt Does

Comprehensive data persistence and database design analysis with consistency evaluation. Provides:

✅ **Storage Architecture** — Persistence mechanisms and data storage strategies  
✅ **Database Design** — Schema structure, relationships, and indexing strategies  
✅ **Queries & Data Access** — Query patterns, parameterization, and optimization  
✅ **Data Consistency** — Transaction usage, ACID compliance, and race condition prevention  
✅ **Bot State Management** — Configuration and status tracking mechanisms  
✅ **Configuration Storage** — Config persistence, versioning, and validation  
✅ **Metrics & Analytics Data** — Time-series storage and data retention policies  
✅ **Data Backup & Recovery** — Backup strategies and disaster recovery planning  
✅ **Data Migration** — Schema migration tools and rollback capabilities  
✅ **Concurrency & Locking** — Concurrent access handling and deadlock prevention  
✅ **Performance Characteristics** — Query latency and scalability assessment  
✅ **Data Privacy & Security** — Encryption, access controls, and PII handling  
✅ **Scalability** — Horizontal scaling and read replica strategies  
✅ **Concerns & Recommendations** — Data consistency risks and improvement suggestions

---

## Related Prompts

Same Package:

- [Prompt 01](./01-architecture-structure.md) — Overall architecture data flow
- [Prompt 03](./03-data-models-validation.md) — Data models that interface with storage
- [Prompt 08](./08-performance-optimization.md) — Database performance optimization

Cross-Package:

- [Bot Prompt 07](../../bot/docs/prompts/07-data-persistence.md) — Bot data persistence patterns
- [Bot Prompt 07](../../bot/docs/prompts/07-data-persistence.md) — Bot data persistence patterns
- NOTE: Cite specific bot files that read/write shared storage (e.g., `packages/bot/sonarftdata/`, `packages/bot/sonarft_execution.py`) and check for concurrent update risks between API and bot processes.
- [Web Prompt 07](../../web/docs/prompts/07-data-management.md) — Web data management that depends on this storage

---

## Copy & Paste Into Your AI Chat

```text
# PROMPT 07: Database, Persistence & Data Storage Review

Please review data persistence and storage mechanisms in the sonarft API.

## 1. Storage Architecture
Analyze how data is stored:
- What persistence mechanism is used? (database, files, in-memory, etc.)
- Is there a database? (SQL, NoSQL, etc.) If so, what type?
- Are there file-based storage needs? (config files, logs)
- Is there in-memory caching?
- How is state maintained across restarts?

## 2. Database Design (if applicable)
If a database is used, review:
- What are the main tables/collections?
- How are bots, configurations, and metrics stored?
- What are the primary keys?
- Are relationships normalized or denormalized?
- Are indexes used appropriately?
- Is the schema documented?

## 3. Queries & Data Access
Review data access patterns:
- How are queries written? (ORM, raw SQL, query builder)
- Are queries parameterized to prevent SQL injection?
- Are common queries optimized?
- Is N+1 query problem present?
- Are there missing indexes causing slow queries?

## 4. Data Consistency
Check data consistency mechanisms:
- Are transactions used?
- Is there ACID compliance?
- How are race conditions prevented?
- What happens if two requests modify same bot simultaneously?
- Is eventual consistency acceptable?

## 5. Bot State Management
Analyze bot data storage:
- How is bot configuration stored?
- How is bot status (running/stopped) tracked?
- How are trading positions stored?
- Is there a history of trades/executions?
- Can state be corrupted by concurrent updates?

## 6. Configuration Storage
Review configuration persistence:
- How are bot configurations stored?
- Can configurations be updated without downtime?
- Is there version control for configs?
- Can old configs be restored?
- Are configs validated on load?

## 7. Metrics & Analytics Data
If metrics are stored:
- How are trading metrics stored?
- Is there time-series data?
- How much data retention is needed?
- Is archiving/purging implemented?
- Can old data be queried efficiently?

## 8. Data Backup & Recovery
Check backup and disaster recovery:
- Is there a backup strategy?
- How frequently are backups taken?
- Can backups be restored?
- Is there a recovery time objective (RTO)?
- Is there a recovery point objective (RPO)?

## 9. Data Migration
Review data migration capabilities:
- Are there database migration tools? (Alembic, etc.)
- How are schema changes handled?
- Can migrations be rolled back?
- Is there a way to migrate between database systems?

## 10. Concurrency & Locking
Analyze concurrent access:
- How are concurrent writes handled?
- Are there deadlock risks?
- Is optimistic or pessimistic locking used?
- Are there connection pool limits?

## 11. Performance Characteristics
Assess performance:
- What is query latency?
- How much data can be stored?
- Does performance degrade with data size?
- Are there slow queries?
- Could pagination help?

## 12. Data Privacy & Security
Review data security:
- Is sensitive data encrypted at rest?
- Are database credentials secure?
- Are there access controls?
- Is data exported/imported securely?
- Is PII properly handled?

## 13. Scalability
Check scalability:
- Can the system scale to more bots/users?
- Is horizontal scaling possible?
- Is there a read replica strategy?
- Could sharding be needed?

## 14. Concerns & Recommendations
- Identify data consistency risks
- Suggest performance improvements
- Recommend scaling strategies
- Rate severity: Low/Medium/High
- Provide implementation examples

## Output Format

Generate a Markdown document including:
- Executive Summary
- Data Architecture Diagram
- Database Schema (if applicable)
- Query Pattern Analysis
- Performance Assessment
- Scalability Analysis
- Issues Found (with severity)
- Recommendations (with examples)
- Backup & Recovery Plan
- Data Security Checklist

Be specific about table names, query examples, and performance metrics if available.
```

---

## Expected Output

A comprehensive data storage and persistence review that includes:

- Data architecture overview
- Database design assessment (if applicable)
- Query performance analysis
- Data consistency evaluation
- Scalability recommendations

---

## How to Use the Output

1. Save the generated document to `docs/database/07-database-persistence.md`
2. Optimize slow queries based on findings
3. Plan data backup and recovery procedures
4. Implement data retention policies
5. Scale database infrastructure as needed

---

## Related Prompts

After this prompt, consider:

- [Prompt 8: Performance Optimization](./08-performance-optimization.md) — Database performance
- [Prompt 4: Authentication & Security](./04-authentication-security.md) — Data security
- [Prompt 1: Architecture Structure](./01-architecture-structure.md) — Data flow

---

_Part of the sonarft API Code Review Prompt Suite_
