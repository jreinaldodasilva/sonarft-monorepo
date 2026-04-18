---
Prompt ID: 01-API-ARCH
Package: api
Category: Architecture
Difficulty: Medium
Time Estimate: 30-45 minutes
Run After: None
Can Run In Parallel With: 02-API-ENDPOINTS
Output Location: docs/architecture/api-architecture.md
Last Updated: July 2025
Status: Complete
---

# Prompt 01 — API Architecture & Project Structure Review

**Focus:** API architecture, module organization, and structural design  
**Category:** API Design & Architecture  
**Deliverables:** 8 sections / 10 analysis areas  
**Output File:** `docs/architecture/api-architecture.md`  
**Prerequisites:** Master Instruction + API codebase uploaded

---

## What This Prompt Does

Analyzes the overall architecture, module organization, and structural design of the sonarft API. You'll get:

- High-level API structure and organization
- Module relationships and dependencies
- Integration points with bot engine and frontend
- Directory structure assessment
- Architectural patterns and anti-patterns
- Recommendations for structural improvements

---

## Copy & Paste Into Your AI Chat

```text
# PROMPT 01: API Architecture & Project Structure Review

Please analyze the sonarft API codebase and provide a comprehensive architectural overview.

Focus on these areas:

## 1. Overall Architecture
- Describe the high-level architecture (FastAPI application structure)
- How are modules organized? (src/api, src/core, src/services, src/websocket, src/models)
- What is the directory structure and how does it reflect the design?
- Are there clear separation of concerns across layers?

## 2. Module Organization
For each major module, provide:
- **api/v1/endpoints/** — Describe all endpoint routers (health, bots, config)
  - How are endpoints organized by resource?
  - Is there code duplication across endpoints?
  - Are naming conventions consistent?

- **core/** — What does each core module handle?
  - config.py: Configuration and settings management
  - errors.py: Error handling and exception definitions
  - security.py: Authentication and token verification
  - Are these responsibilities clear and well-separated?

- **services/** — What services exist and what do they do?
  - bot_service: Bot lifecycle management
  - config_service: Configuration management
  - Are services properly abstracted from endpoints?

- **models/** — How are data models organized?
  - schemas.py: Pydantic models for request/response validation
  - Are models reused across endpoints?

- **websocket/** — Real-time communication layer
  - manager.py: WebSocket connection management
  - How are connections tracked and broadcast?

## 3. Integration Points
- How does the API integrate with the bot engine (sonarft)?
- What is the IPC/subprocess mechanism for bot communication?
- How does the API communicate with the frontend (sonarftweb)?
- What external dependencies exist (CCXT, exchanges)?

## 4. Application Factory Pattern
- Analyze create_app() function in main.py
- How is the FastAPI application initialized?
- How are middleware, error handlers, and routers registered?
- Is the configuration properly loaded and validated?

## 5. Cross-Package Dependencies
- What does the API depend on from the bot package?
- How are dependencies imported and managed?
- Are there circular dependencies or tight coupling issues?

## 6. Architectural Patterns
- What design patterns are being used? (e.g., service layer, dependency injection)
- Are patterns applied consistently?
- Are there opportunities to improve consistency?

## 7. Concerns & Questions
- List any architectural concerns or inconsistencies
- Suggest structural improvements
- Are there missing layers or abstractions?
- How would the architecture scale with more bots/users?

## Output Format

Generate a Markdown document with:
- Executive Summary (key findings in 3-5 sentences)
- Architecture Diagram (using Mermaid)
- Module Organization Table
- Integration Points Diagram
- Architectural Strengths (2-3 items)
- Architectural Concerns (with severity: Low/Medium/High)
- Recommendations (prioritized list)

Be specific about file paths, class names, and line numbers. Do not guess about functionality not present in the code.
```

---

## Expected Output

A comprehensive architecture review document that includes:

- Visual diagrams of API structure and integration points
- Detailed breakdown of each major module
- Assessment of design patterns and consistency
- Identification of architectural strengths and weaknesses
- Concrete, actionable recommendations

---

## How to Use the Output

1. Save the generated document to `docs/architecture/01-api-architecture.md`
2. Review architectural concerns and plan refactoring
3. Use recommendations to guide structural improvements
4. Refer to this document when adding new endpoints or services
5. Share with team for architectural alignment discussions

---

## Related Prompts

After this prompt, consider:

- [Prompt 2: API Endpoints Design](./02-api-endpoints-design.md) — Detailed endpoint review
- [Prompt 1: Architecture Structure](./01-architecture-structure.md) — You are here
- [Prompt 3: Data Models & Validation](./03-data-models-validation.md) — Model design

---

_Part of the sonarft API Code Review Prompt Suite_
