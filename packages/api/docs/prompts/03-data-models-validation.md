---
Prompt ID: 03-API-MODELS
Package: api
Category: Data
Difficulty: Medium
Time Estimate: 30-45 minutes
Run After: 01-API-ARCH
Can Run In Parallel With: 02-API-ENDPOINTS
Output Location: docs/models/data-models-validation.md
Last Updated: April 2026
Status: Complete
---

# Prompt 03 — Data Models & Validation Review

**Focus:** Pydantic models, data validation, and data integrity  
**Category:** Data Models & Validation  
**Deliverables:** 8 sections / 10 analysis areas  
**Output File:** `docs/models/data-models-validation.md`  
**Prerequisites:** Master Instruction + Prompt 01 + codebase uploaded

---

## What This Prompt Does

Comprehensive Pydantic models analysis with validation and data integrity evaluation. Provides:

✅ **Model Inventory** — Complete catalog of all Pydantic models and their usage  
✅ **Pydantic V2 Compliance** — Framework adoption and configuration assessment  
✅ **Field Validation** — Validation rules, constraints, and error handling  
✅ **Type Annotations** — Type hint completeness and accuracy  
✅ **Request Models vs Response Models** — Separation of concerns and data exposure  
✅ **Nested Models** — Structure complexity and circular reference prevention  
✅ **Serialization** — JSON conversion and custom type handling  
✅ **Model Relationships** — Usage patterns and reusability analysis  
✅ **Validation Rules Completeness** — Missing validation identification  
✅ **Data Integrity** — Invariants and relationship validation  
✅ **Concerns & Recommendations** — Issues and improvement suggestions

---

## Related Prompts

Same Package:

- [Prompt 01](./01-architecture-structure.md) — Overall API architecture using these models
- [Prompt 02](./02-api-endpoints-design.md) — Endpoints that use these models
- [Prompt 04](./04-authentication-security.md) — Security models and validation

Cross-Package:

- [Bot Prompt 03](../../bot/docs/prompts/03-data-structures.md) — Bot data structures that interface with these models
- [Web Prompt 03](../../web/docs/prompts/03-data-validation.md) — Web frontend validation using these models

---

## Copy & Paste Into Your AI Chat

```text
# PROMPT 03: Data Models & Validation Review

Please analyze all Pydantic models in the sonarft API and evaluate their design and validation.

## 1. Model Inventory
List all Pydantic models found in models/schemas.py:
- Model name, purpose, and usage locations
- Which endpoints use each model?
- Are models reused across endpoints?
- Are there duplicate/similar models?

## 2. Pydantic V2 Compliance
Review Pydantic v2 adoption:
- Are models using @field_validator or v1 validators?
- Are ConfigDict properly set up?
- Are aliases used for field name mapping?
- Is JSON schema generation configured correctly?

## 3. Field Validation
For each model:
- What validation rules exist? (required, optional, defaults)
- Are constraints documented? (min/max, patterns, enums)
- Are field descriptions provided?
- Are validation errors clear and helpful?

Examples to check:
- Are API keys/passwords properly marked as sensitive?
- Are numeric fields bounded? (e.g., bot limits, trading amounts)
- Are enum fields used for restricted values?
- Are string patterns enforced where needed? (UUIDs, emails, etc.)

## 4. Type Annotations
- Are all fields properly typed?
- Are Optional/Union types used correctly?
- Are complex types handled? (nested models, lists, dicts)
- Are type hints complete and accurate?

## 5. Request Models vs Response Models
- Are separate models used for requests and responses?
- Can models be simplified by splitting concerns?
- Are there fields in request models that shouldn't be there?
- Are there fields in response models that expose secrets?

## 6. Nested Models
- Are there deeply nested model structures?
- Could nesting be reduced for clarity?
- Are circular references avoided?
- Are shared nested models properly extracted?

## 7. Serialization
- How are models serialized to JSON?
- Are datetime fields properly formatted?
- Are enums serialized correctly?
- Are custom types handled properly?
- Are sensitive fields excluded from responses?

## 8. Model Relationships
Create a diagram showing:
- Which models are used by which endpoints
- Parent-child relationships
- Shared sub-models
- Reusability across endpoints

## 9. Validation Rules Completeness
Check for missing validation:
- Are numeric fields for trading amounts validated for positive values?
- Are bot configuration fields validated?
- Are array fields checked for size/length?
- Are dependencies between fields validated?

## 10. Data Integrity
- Are there invariants that should be validated?
- Could invalid data states be prevented at the model level?
- Are there post-init validation hooks?
- Are relationships between fields validated?

## 11. Concerns & Recommendations
- Identify overly complex models
- Suggest simplifications or restructuring
- Highlight missing validation
- Rate severity: Low/Medium/High
- Provide refactoring examples

## Output Format

Generate a Markdown document including:
- Executive Summary
- Model Inventory Table (Name | Purpose | Used By | Fields Count)
- Pydantic V2 Compliance Assessment
- Validation Rules Audit
- Model Relationships Diagram
- Serialization Analysis
- Issues Found (with severity)
- Recommendations (prioritized, with code examples)

Be specific about model names, field names, and validation rules. Cite exact line numbers.
```

---

## Expected Output

A comprehensive models review that includes:

- Complete model reference and relationships
- Validation completeness assessment
- Identification of missing or redundant models
- Type annotation audit
- Recommendations for model restructuring

---

## How to Use the Output

1. Save the generated document to `docs/models/03-data-models.md`
2. Review validation completeness and add missing rules
3. Plan model restructuring if needed
4. Update model documentation
5. Use for API client code generation

---

## Related Prompts

After this prompt, consider:

- [Prompt 2: API Endpoints Design](./02-api-endpoints-design.md) — How models are used
- [Prompt 4: Authentication & Security](./04-authentication-security.md) — Sensitive field handling
- [Prompt 10: Code Quality Python](./10-code-quality-python.md) — Code organization

---

_Part of the sonarft API Code Review Prompt Suite_
