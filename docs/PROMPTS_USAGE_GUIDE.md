# Getting the Most Out of SonarFT Code Review Prompts

**Purpose:** Practical techniques for running effective AI-assisted code reviews  
**Audience:** Anyone using the SonarFT prompt suite with an AI assistant  
**Time:** 15-minute read, then reference as needed

---

## How the Prompts Work

Each prompt in this suite is a structured instruction that tells an AI assistant exactly what to analyze and how to format the output. The system has three layers:

1. **Master Instruction** — Sets the AI's persona and rules (paste once per session)
2. **Core Prompts (01-10)** — Each targets a specific domain (architecture, security, etc.)
3. **Summary Prompts (11-12)** — Consolidate findings into actionable plans

The AI doesn't remember between sessions. Every new conversation starts from zero — that's why the Master Instruction exists.

---

## Setting Up a Review Session

### Step 1: Choose Your AI Tool

Any AI that accepts long text input works. Recommended options:

| Tool | Best For | Tip |
|------|----------|-----|
| Amazon Q Developer (IDE) | Reviewing code you're actively working on | Use `@file` and `@folder` to include context |
| Claude | Long, detailed reviews with large codebases | Upload files directly — handles 200K+ tokens |
| ChatGPT (GPT-4) | General reviews, good with diagrams | Use file upload for best results |

### Step 2: Paste the Master Instruction

Open the Master Instruction for your package:
- Bot: `packages/bot/docs/prompts/00-master-instruction.md`
- API: `packages/api/docs/prompts/00-master-instruction.md`
- Web: `packages/web/docs/prompts/00-master-instruction.md`

Copy the text inside the ` ```text ``` ` code block and paste it into your AI chat. Wait for acknowledgment before continuing.

### Step 3: Provide the Code

The more code the AI sees, the better the review. At minimum:

| Package | Must Include | Nice to Have |
|---------|-------------|--------------|
| Bot | All `sonarft_*.py` files | `sonarftdata/*.json`, `tests/`, `requirements.txt` |
| API | All files under `src/` | `tests/`, `requirements.txt`, `.env.example` |
| Web | All files under `src/` | `package.json`, `vite.config.js`, `tsconfig.json` |

### Step 4: Run a Prompt

Copy the prompt text (inside the ` ```text ``` ` block) from any prompt file and paste it into the same conversation. The AI generates a Markdown document as output.

---

## Techniques That Improve Results

### Keep One Conversation Per Package

Don't start a new chat for every prompt. The AI builds context as you go — prompt 05 benefits from what the AI learned during prompts 01-04. Start a new conversation only when:
- The chat is getting very long (30+ exchanges)
- You're switching to a different package (bot → api)
- The AI starts confusing details from earlier prompts

### Run Architecture First

Always run Prompt 01 (Architecture) before anything else. It gives the AI a mental map of the codebase that makes every subsequent prompt more accurate. Without it, the AI may misidentify module boundaries or miss dependency relationships.

### Ask Follow-Up Questions

Prompts generate broad analysis. Drill into specifics:

```
"Expand on the race condition you found in sonarft_search.py. 
Show the exact code path and a concrete fix."
```

```
"You rated the auth implementation as 'Medium' risk. 
What specific attack would exploit this? Show the request."
```

```
"Create a before/after code example for your top 3 recommendations."
```

### Request Missing Sections

If the AI skips a section or gives a shallow answer:

```
"You didn't cover WebSocket reconnection logic. 
Please analyze the reconnection strategy in useWebSocket.tsx 
and identify any gaps."
```

### Combine Related Prompts

For focused reviews, paste two related prompts together:

- **Security deep-dive:** Combine Prompt 04 (Security) + Prompt 06 (Error Handling) for API
- **Trading safety:** Combine Prompt 03 (Trading Engine) + Prompt 04 (Financial Math) for Bot
- **Integration review:** Combine Web Prompt 02 (API Integration) + Web Prompt 05 (Real-Time)

### Use the "Not Found" Signal

When the AI writes `⚠️ Not Found in Source Code`, that's valuable information — it means a feature is missing. Ask:

```
"You noted that rate limiting is not implemented. 
What's the impact of this gap? Provide a minimal implementation 
using FastAPI middleware."
```

---

## Common Mistakes to Avoid

### Mistake: Skipping the Master Instruction

Without it, the AI doesn't know it's reviewing a trading system. It will miss financial precision issues, trading safety concerns, and domain-specific patterns.

### Mistake: Uploading Partial Code

If you only upload 3 of 10 Python files, the AI will write "⚠️ Not Found" for everything in the missing files. Upload the complete package source.

### Mistake: Running All 10 Prompts When You Only Need 2

The full suite takes 2-5 hours. If you only care about security, run:
- Prompt 01 (Architecture) — 20 min for context
- The security prompt for your package — 30-45 min

That's 50 minutes instead of 5 hours.

### Mistake: Ignoring Severity Ratings

The AI rates issues as Low, Medium, High, or Critical. Focus on Critical and High first. A codebase with 50 Low issues and 0 Critical issues is in much better shape than one with 5 Critical issues.

### Mistake: Not Saving Outputs

Each prompt generates a document. Save it immediately to the location specified in the prompt's frontmatter (`Output Location` field). You'll need these for the Final Consolidation (Prompt 11).

---

## Review Paths by Time Budget

### 30 Minutes — Quick Health Check

Run only Prompt 10 (Code Quality) for any package. It covers naming, organization, testing, and common anti-patterns. No other prompts needed.

**Output:** One document with a prioritized issues list.

### 90 Minutes — Focused Security Audit

1. Prompt 01 — Architecture (20 min)
2. Security prompt for your package (45 min):
   - Bot: Prompt 08 (Security & Trading Risk)
   - API: Prompt 04 (Authentication & Security)
   - Web: Prompt 06 (Authentication & Security)
3. Follow-up questions on Critical findings (25 min)

**Output:** Architecture overview + security audit with remediation steps.

### 3 Hours — Complete Single-Package Audit

1. Prompt 01 — Architecture (20 min)
2. Prompts 02-10 in order (15-30 min each)
3. Prompt 11 — Final Consolidation (20 min)

**Output:** Complete documentation suite with executive summary.

### 8-12 Hours — Full-Stack Review

Follow the sequence: Bot → API → Web. Each package gets a complete audit. Then cross-reference findings:
- Do API endpoints match what the web frontend calls?
- Does the bot's error handling propagate correctly through the API?
- Are WebSocket message formats consistent between API and web?

See [CROSS_PACKAGE_NAVIGATION.md](../CROSS_PACKAGE_NAVIGATION.md) for the detailed workflow.

---

## Working with Amazon Q Developer

If you're using these prompts inside Amazon Q Developer in your IDE, the workflow is slightly different:

### Using @file and @folder References

Instead of uploading files, reference them directly:

```
@packages/bot/sonarft_search.py @packages/bot/sonarft_prices.py

[paste prompt 03 text here]
```

### Using @workspace for Broad Context

For architecture prompts that need to see the whole package:

```
@workspace

[paste the Master Instruction]
[paste prompt 01 text here]
```

### Saving Prompts for Reuse

Save frequently-used prompts to `~/.aws/amazonq/prompts/` and reference them with `@prompt`:

```
@sonarft-security-review
```

### IDE-Specific Tips

- Use `/review` for quick code reviews of specific files
- The active file is automatically included — no need to reference it if you're asking about the current file
- For multi-file analysis, use `@folder` to include an entire directory

---

## Interpreting AI Output

### What "Critical" Actually Means

| Severity | Definition | Action |
|----------|-----------|--------|
| Critical | Can cause data loss, financial loss, or security breach | Fix before any deployment |
| High | Significant risk under load or edge cases | Fix before production |
| Medium | Should be fixed but won't cause immediate harm | Plan for next sprint |
| Low | Code quality improvement, not a risk | Backlog |

### When the AI Is Wrong

The AI can make mistakes. Common false positives:
- **"Missing error handling"** — when error handling exists but in a parent function
- **"Potential race condition"** — when the code is single-threaded or properly locked
- **"Security vulnerability"** — when the flagged code is only used in simulation mode

Always verify Critical and High findings against the actual code before acting on them.

### When the AI Misses Something

The AI reviews what it can see. It may miss:
- Issues in binary/compiled files
- Runtime behavior that depends on external services
- Configuration problems in deployment environments
- Issues that only appear under specific data conditions

Use the AI review as a starting point, not a complete audit.

---

## Organizing Review Output

Save generated documents using this structure:

```
docs/
├── architecture/          ← Prompt 01 output
├── trading/               ← Prompts 03, 04, 05, 06 output (bot)
├── endpoints/             ← Prompt 02 output (api)
├── security/              ← Security prompt output
├── performance/           ← Performance prompt output
├── code-quality/          ← Prompt 10 output
├── review/
│   └── final-audit-report.md  ← Prompt 11 output
└── roadmap/
    └── implementation-roadmap.md  ← Prompt 12 output
```

Each prompt's frontmatter has an `Output Location` field that tells you exactly where to save it.

---

## After the Review

### Prioritize with the Roadmap

Run Prompt 12 (Implementation Roadmap) after the Final Consolidation. It converts findings into sprint-ready tasks with effort estimates.

### Track Progress

After fixing issues, re-run the relevant prompts to verify:
- Did the fix address the finding?
- Did it introduce new issues?
- Has the severity rating changed?

### Share with the Team

The Final Consolidation (Prompt 11) produces an executive summary suitable for:
- Sprint planning meetings
- Stakeholder updates
- Production readiness decisions
- New team member onboarding

---

## Quick Reference

| I want to... | Do this |
|--------------|---------|
| Start a review | Paste Master Instruction → upload code → run Prompt 01 |
| Check security only | Prompt 01 + security prompt for your package |
| Quick health check | Prompt 10 only |
| Full audit | Prompts 01-10 → Prompt 11 → Prompt 12 |
| Review integration | Web Prompt 02 + API Prompt 02 + API Prompt 05 |
| Find all prompts | See package README or [PROMPTS_INDEX](./PROMPTS_INDEX.md) |
| Understand cross-package flow | See [CROSS_PACKAGE_NAVIGATION](../CROSS_PACKAGE_NAVIGATION.md) |

---

**Last Updated:** July 2025
