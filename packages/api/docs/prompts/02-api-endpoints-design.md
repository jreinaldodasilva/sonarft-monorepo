---
Prompt ID: 02-API-ENDPOINTS
Package: api
Category: Design
Difficulty: Medium
Time Estimate: 45-60 minutes
Run After: 01-API-ARCH
Can Run In Parallel With: 03-API-MODELS
Output Location: docs/endpoints/api-endpoints-design.md
Last Updated: July 2025
Status: Complete
---

# Prompt 02 — API Endpoints Design & REST Contract Review

**Focus:** RESTful endpoints, HTTP methods, routing, and API design patterns  
**Category:** API Design & REST  
**Deliverables:** 8 sections / 12 analysis areas  
**Output File:** `docs/endpoints/api-endpoints-design.md`  
**Prerequisites:** Master Instruction + Prompt 01 + codebase uploaded
**Important:** Upload `packages/bot` alongside `packages/api` so the reviewer can verify endpoints that send commands or data to the bot. Cite bot-side handlers where relevant.

---

## What This Prompt Does

Comprehensive RESTful API endpoints analysis with design pattern evaluation. Provides:

✅ **Endpoint Inventory** — Complete catalog of all API endpoints with methods, paths, and handlers  
✅ **HTTP Method Review** — Appropriateness of GET, POST, PUT, DELETE, PATCH usage  
✅ **URI Path Design** — Resource naming consistency and path structure assessment  
✅ **Request & Response Contracts** — Pydantic model validation and schema documentation  
✅ **Status Code Usage** — HTTP status code appropriateness and error handling  
✅ **API Consistency** — Naming patterns, formats, and documentation standards  
✅ **Pagination, Filtering, Sorting** — List endpoint capabilities and parameter handling  
✅ **Rate Limiting & Throttling** — API protection and enforcement mechanisms  
✅ **API Versioning** — Versioning strategy and backward compatibility  
✅ **Documentation** — OpenAPI/Swagger completeness and clarity  
✅ **Concerns & Recommendations** — Issues identification and improvement suggestions

---

## Related Prompts

Same Package:

- [Prompt 01](./01-api-architecture.md) — Overall API architecture and structure
- [Prompt 03](./03-api-models.md) — Pydantic models and data validation
- [Prompt 04](./04-api-security.md) — Authentication and authorization patterns

Cross-Package:

- [Bot Prompt 01](../../bot/docs/prompts/01-architecture-structure.md) — Bot architecture that consumes this API
- [Bot Prompt 01](../../bot/docs/prompts/01-architecture-structure.md) — Bot architecture that consumes this API
- NOTE: When describing endpoints that interact with the bot (e.g., start/stop/pause bot), cite `packages/bot/sonarft_api_manager.py`, `packages/bot/sonarft_bot.py`, or related files to show exact call flow.
- [Web Prompt 02](../../web/docs/prompts/02-api-integration.md) — Web frontend integration with this API

---

## Copy & Paste Into Your AI Chat

```text
# PROMPT 02: API Endpoints Design & REST Contract Review

Please review all RESTful endpoints in the sonarft API and evaluate their design and consistency.

## 1. Endpoint Inventory
List ALL endpoints found in the codebase:
- For each endpoint, document: HTTP Method, URI Path, Handler Function, Description
- Include request parameters (path, query, body)
- Include response codes and schemas
- Note authentication requirements

Focus on:
- api/v1/endpoints/health.py — Health check and status endpoints
- api/v1/endpoints/bots.py — Bot lifecycle and management endpoints
- api/v1/endpoints/config.py — Configuration endpoints

## 2. HTTP Method Review
For each endpoint:
- Is the HTTP method (GET, POST, PUT, DELETE, PATCH) appropriate for the operation?
- Are there any misused methods? (e.g., using GET to modify state)
- Are safe methods (GET) truly read-only?
- Are idempotent methods used correctly?

## 3. URI Path Design
Evaluate path naming and consistency:
- Are resource names correct and consistent? (plural for collections, singular for items)
- Examples: GET /api/v1/bots (collection) vs GET /api/v1/bots/{id} (item)
- Are nested resources properly structured?
- Are query parameters vs path parameters used appropriately?
- Is the API prefix consistent (/api/v1)?

## 4. Request & Response Contracts
For each endpoint:
- What is the request body schema? (from Pydantic models)
- What are the response schemas? (success and error cases)
- Are request bodies validated?
- Are responses documented with examples?
- Are nullable/optional fields handled correctly?

## 5. Status Code Usage
Review HTTP status codes:
- 2xx (Success): 200, 201, 202, 204 — used correctly?
- 3xx (Redirect): Any needed?
- 4xx (Client Error): 400, 401, 403, 404, 422 — used appropriately?
- 5xx (Server Error): 500, 503 — error handling working?

## 6. API Consistency
Check for consistency across all endpoints:
- Do all endpoints follow the same naming pattern?
- Are request/response formats consistent?
- Is error response format standardized?
- Are all endpoints documented similarly?
- Are timestamps formatted consistently?

## 7. Pagination, Filtering, Sorting
If applicable:
- How are list endpoints paginated? (limit/offset or cursor-based?)
- Are filtering parameters standardized?
- Is sorting supported? How?
- Are parameters optional and well-documented?

## 8. Rate Limiting & Throttling
- Is rate limiting implemented?
- Are there rate limit headers in responses?
- How are limits enforced per user/IP?
- Are there endpoint-specific limits?

## 9. API Versioning
- Is the API properly versioned (/api/v1)?
- How would backward compatibility be maintained?
- Are there deprecated endpoints?

## 10. Documentation
- Are endpoints documented? (OpenAPI/Swagger)
- Are descriptions clear and accurate?
- Are examples provided for complex endpoints?
- Can developers understand the API from documentation?

## 11. Concerns & Recommendations
- Identify inconsistencies or problematic design choices
- Rate severity: Low/Medium/High
- Suggest specific improvements
- Provide refactoring examples if needed

## Output Format

Generate a Markdown document including:
- Executive Summary
- Complete Endpoint Reference Table (Method | Path | Handler | Auth | Description)
- Design Pattern Analysis
- Endpoint Documentation Examples
- Consistency Assessment
- Issues Found (with severity ratings)
- Recommendations (prioritized)
- Before/After refactoring examples

Be specific about file paths (e.g., api/v1/endpoints/bots.py line 42) and handler names.
```

---

## Expected Output

A detailed endpoints review that includes:

- Complete reference of all endpoints
- Visual representation of endpoint hierarchy
- Assessment of REST compliance
- Identification of design inconsistencies
- Concrete recommendations for improvement

---

## How to Use the Output

1. Save the generated document to `docs/endpoints/02-api-endpoints.md`
2. Use endpoint reference as API documentation
3. Review inconsistencies and plan refactoring
4. Share with frontend team for integration planning
5. Update API documentation based on findings

---

## Related Prompts

After this prompt, consider:

- [Prompt 3: Data Models & Validation](./03-data-models-validation.md) — Request/response schemas
- [Prompt 4: Authentication & Security](./04-authentication-security.md) — Endpoint security
- [Prompt 1: Architecture Structure](./01-architecture-structure.md) — Endpoint organization

---

_Part of the sonarft API Code Review Prompt Suite_
