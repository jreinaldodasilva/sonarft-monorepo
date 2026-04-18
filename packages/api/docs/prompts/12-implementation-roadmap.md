# Implementation Roadmap: Structured Action Plan

**Prompt:** 12-implementation-roadmap  
**Time:** 30-45 minutes  
**Output:** Markdown document in `docs/`  
**Prerequisites:** [Final Consolidation](./11-final-consolidation.md)

---

## What This Prompt Does

Creates a detailed implementation roadmap with specific action items, prioritization, dependencies, and timelines. You'll get:

- Prioritized action items
- Effort estimation
- Dependency mapping
- Timeline recommendations
- Team assignments
- Success criteria

---

## Copy & Paste Into Your AI Chat

```text
# PROMPT 12: Implementation Roadmap — Detailed Action Plan

Based on the consolidated findings from all previous reviews, please create a detailed implementation roadmap.

## 1. Action Item Inventory
List ALL action items from the comprehensive review:
- Item ID (e.g., SEC-001, PERF-001, TEST-001)
- Title and description
- Affected area (Security, Performance, Testing, etc.)
- Severity (Critical/High/Medium/Low)
- Current status (Not Started/In Progress/Blocked)

## 2. Prioritization Framework
For each action item, determine:
- Business impact (1-10 scale)
- Technical difficulty (1-10 scale)
- Effort required (hours/days)
- Dependencies on other items
- Priority score = (Impact × 2) - (Difficulty × 0.5)

Sort by priority score descending.

## 3. Dependency Analysis
Create dependency graph:
- What items must be completed before others?
- Are there blocking dependencies?
- What can be parallelized?
- What is the critical path?

Example:
```

AUTH-001 (Implement rate limiting)
→ depends on → INFRA-001 (Add Redis)
→ blocks → PERF-001 (Optimize endpoints)

```

## 4. Phase Planning
Organize items into phases:

### Phase 1: Critical Path (Week 1-2)
Must complete before anything else:
- [ ] Item 1
- [ ] Item 2
- [ ] Item 3
Rationale: Blocking other work / Production blockers

### Phase 2: Foundation (Week 3-4)
Building blocks for future work:
- [ ] Item 1
- [ ] Item 2
Rationale: Required infrastructure

### Phase 3: Core Improvements (Week 5-8)
Major improvements:
- [ ] Item 1
- [ ] Item 2
Rationale: Significant value

### Phase 4: Optimization (Week 9-12)
Nice-to-have improvements:
- [ ] Item 1
- [ ] Item 2
Rationale: Long-term quality

## 5. Detailed Action Items
For each critical/high item, provide:

### Item ID: [Title]
- **Description:** What needs to be done
- **Why:** Business rationale
- **Current State:** What's broken/missing
- **Desired State:** What should be in place
- **Effort Estimate:** X hours/days
- **Difficulty:** Easy/Medium/Hard
- **Impact:** Business value
- **Dependencies:** What must happen first
- **Success Criteria:** How to know it's done
- **Acceptance Tests:** How to verify completion
- **Assigned To:** Suggested team member/role
- **Notes:** Constraints, considerations, risks

## 6. Resource Planning
For each phase:
- Required team members/expertise
- Estimated total effort (person-days)
- Potential bottlenecks
- Risk mitigation

## 7. Timeline Recommendations
Proposed timeline:
- When should Phase 1 start?
- Duration of each phase
- Target completion date
- Milestones and checkpoints
- Risk-adjusted timeline (if possible)

## 8. Definition of Done
For each action item:
- Code review completed
- Tests added/passed
- Documentation updated
- Performance verified (if applicable)
- Security verified (if applicable)
- Deployed to staging
- Approved for production

## 9. Risk Assessment
For each phase:
- Technical risks
- Resource risks
- Schedule risks
- Mitigation strategies

## 10. Success Metrics
How to measure success:
- Code quality improvements (coverage %, complexity)
- Performance improvements (response time, throughput)
- Security improvements (vulnerabilities fixed)
- Reliability improvements (uptime, error rate)

## 11. Go/No-Go Criteria
Phase entry criteria:
- Previous phase complete
- Resources available
- No blocking issues
- Team ready

Phase exit criteria:
- All items complete
- Tests passing
- Documentation complete
- Stakeholder approval

## 12. Alternative Approaches
For major items, consider:
- Build vs. buy options
- Different technical approaches
- Phased vs. big-bang implementation

## Output Format

Generate a comprehensive roadmap with:

**Document Structure:**
1. Executive Summary (timeline, phases, resource needs)
2. Phase Overview (table with timeline)
3. Critical Path Analysis (dependency diagram)
4. Detailed Action Items by Phase (include all 11 fields above)
5. Resource Plan
6. Risk Assessment
7. Success Metrics
8. Gantt Chart (ASCII or Mermaid diagram)
9. Assumptions & Constraints
10. Approval & Sign-off Section

Be specific with estimates, and provide rationale for prioritization.
Include specific file paths and code changes needed.
```

---

## Expected Output

A detailed implementation roadmap that includes:

- Prioritized action items with effort estimates
- Phase-based timeline
- Dependency analysis
- Resource requirements
- Risk mitigation strategies
- Success metrics

---

## How to Use the Output

1. Save the generated document to `docs/IMPLEMENTATION-ROADMAP.md`
2. Use for sprint planning and resource allocation
3. Share with team for alignment and estimation validation
4. Track progress against timeline
5. Update roadmap as circumstances change
6. Measure against success metrics

---

## Related Prompts

Complete roadmap with:

- [Prompt 11: Final Consolidation](./11-final-consolidation.md) — Executive summary
- [Prompt 12: Implementation Roadmap](./12-implementation-roadmap.md) — You are here

---

_Part of the sonarft API Code Review Prompt Suite_
