# Data Models & Validation Review Prompt

**Prompt:** 03-data-models-validation  
**Time:** 30-45 minutes  
**Output:** Markdown document in `docs/models/`  
**Prerequisites:** [Master Instruction](./00-master-instruction.md)

---

## What This Prompt Does

Analyzes Pydantic models, data validation, serialization, and data integrity. You'll get:

- Model inventory and relationships
- Validation rule review
- Serialization strategy assessment
- Data integrity evaluation
- Type annotation completeness
- Model reusability assessment

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
