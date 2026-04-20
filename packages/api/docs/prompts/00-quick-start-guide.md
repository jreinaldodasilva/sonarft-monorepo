# Quick Start Guide — Using the API Prompt Suite

**Time:** 5 minutes  
**Goal:** Get up and running with the sonarft API code review prompts  
**For:** Developers new to the prompt suite

---

## What You Need

1. **Access to an AI** (Claude, ChatGPT, Claude with file uploads, etc.)
2. **The sonarft API codebase** (from packages/api/src/)
3. **The prompt files** (from this directory)

---

## 30-Second Setup

### Option A: Chat-Based AI (Recommended)

1. Start a conversation with your AI
2. Copy [00-master-instruction.md](./00-master-instruction.md)
3. Paste it into the chat, hit enter
4. Wait for AI to say it's ready
5. Paste a prompt (e.g., [01-architecture-structure.md](./01-architecture-structure.md))
6. AI generates your documentation

### Option B: AI with File Upload

1. Create a new conversation
2. Upload all API source files (packages/api/src/)
3. Paste [00-master-instruction.md](./00-master-instruction.md)
4. Paste your chosen prompt
5. AI generates documentation with full codebase context

---

## Choosing Your Review Path

### 🏃 Quick Audit (30 minutes) — Fast Health Check

Perfect for: "Is this code ready for production?"

Run only **Prompt 10**: [10-code-quality-python.md](./10-code-quality-python.md)

### 🔍 Complete Audit (2-3 hours)

Perfect for: "Give me a comprehensive review"

Run prompts in order:

1. [01-architecture-structure.md](./01-architecture-structure.md)
2. [02-api-endpoints-design.md](./02-api-endpoints-design.md)
3. [03-data-models-validation.md](./03-data-models-validation.md)
4. [04-authentication-security.md](./04-authentication-security.md)
5. [05-websocket-realtime.md](./05-websocket-realtime.md)
6. [06-error-handling-logging.md](./06-error-handling-logging.md)
7. [07-database-persistence.md](./07-database-persistence.md)
8. [08-performance-optimization.md](./08-performance-optimization.md)
9. [09-testing-quality.md](./09-testing-quality.md)
10. [10-code-quality-python.md](./10-code-quality-python.md)

### 🔒 Security Review (2 hours)

Perfect for: "Is this secure and safe?"

Run these prompts:

1. [04-authentication-security.md](./04-authentication-security.md) — Authentication & JWT
2. [06-error-handling-logging.md](./06-error-handling-logging.md) — Error handling & observability
3. [01-architecture-structure.md](./01-architecture-structure.md) — Overall architecture security

### 🚀 Production Readiness (4-5 hours)

Perfect for: "Is this production-ready?"

Run **all** prompts 1-10, then: 11. [11-final-consolidation.md](./11-final-consolidation.md) — Executive summary 12. [12-implementation-roadmap.md](./12-implementation-roadmap.md) — Action plan

---

## The Prompts Explained

### Foundation

- **00-master-instruction** — Context for all reviews (read once)
- **00-quick-start-guide** — This file (you're reading it now)

### Core Reviews (Pick What Matters)

| Prompt            | Focus                          | When to Use                 |
| ----------------- | ------------------------------ | --------------------------- |
| 01-architecture   | How the API is structured      | Always first                |
| 02-endpoints      | API endpoint design            | Building/reviewing REST API |
| 03-models         | Pydantic models & validation   | Data handling & contracts   |
| 04-security       | Authentication & authorization | Security-first reviews      |
| 05-websocket      | Real-time data streaming       | WebSocket implementation    |
| 06-error-handling | Error handling & logging       | Observability & debugging   |
| 07-database       | Data persistence & queries     | Database design             |
| 08-performance    | Speed, scaling, caching        | Performance-focused reviews |
| 09-testing        | Test coverage & strategy       | Quality assurance           |
| 10-code-quality   | Python best practices          | Code organization           |

### Summary Documents

| Document                  | Purpose                                   |
| ------------------------- | ----------------------------------------- |
| 11-final-consolidation    | Executive summary of all findings         |
| 12-implementation-roadmap | Prioritized action items                  |
| 99-best-practices         | FastAPI & Python best practices reference |

---

## Typical Workflow

```
1. Read Master Instruction → AI acknowledges
2. Upload codebase → "Files received"
3. Run Prompt 1 → "Here's the architecture..."
4. Run Prompt 2 → "Here are endpoint issues..."
5. Run Prompt 3-10 → Keep asking specific questions
6. Run Final Consolidation → Get executive summary
7. Run Implementation Roadmap → Get action plan
8. Save all outputs → Store in docs/ folder
```

---

## Tips & Tricks

### Pro Tip #1: Keep the Conversation Open

Don't start a new conversation for each prompt. Keep the same chat open and paste new prompts. This helps the AI maintain consistency.

### Pro Tip #2: Ask Follow-Up Questions

After each prompt, you can ask clarifying questions:

- "Explain the security issue in Prompt 4 more detail"
- "Give specific code examples for the performance issues"
- "What tests should we add?"

### Pro Tip #3: Skip Irrelevant Prompts

If your API doesn't use WebSocket, skip Prompt 5. If there's no database, skip Prompt 7. Tailor the review to your codebase.

### Pro Tip #4: Consolidate Results

After all prompts, run [11-final-consolidation.md](./11-final-consolidation.md) to get an executive summary.

### Pro Tip #5: Use Implementation Roadmap

After reviews, run [12-implementation-roadmap.md](./12-implementation-roadmap.md) to get a prioritized list of things to fix.

---

## Common Questions

**Q: How long does a full review take?**  
A: 4-5 hours of AI time, but you can run prompts in parallel by opening multiple conversations.

**Q: Can I use just one prompt?**  
A: Yes! Each prompt is independent. Use only what you need.

**Q: Do I need to upload the entire codebase?**  
A: The more you upload, the better the review. At minimum: src/, tests/, requirements.txt, Dockerfile.

**Q: Can I use this for the entire monorepo?**  
A: Each package (bot, api, web) has its own prompt suite. For full-stack reviews, start with [bot prompts](../../bot/docs/prompts/), then [api prompts](./README.md), then [web prompts](../../web/docs/prompts/).

**Q: What if the AI ignores something in the prompts?**  
A: Re-paste the master instruction and say "Let me re-do this prompt with better context."

---

## Next Steps

1. **Read** the [Master Instruction](./00-master-instruction.md)
2. **Choose** your review path (Quick, Complete, Security, Production)
3. **Pick** your first prompt from the list above
4. **Paste** it into your AI chat
5. **Save** the output

---

## Need More Help?

- **Don't know which prompts to run?** → Read [Recommended Review Paths](#choosing-your-review-path)
- **Want specific focus?** → Pick individual prompts from the table
- **Need best practices?** → Read [99-best-practices.md](./99-best-practices.md)
- **Want context?** → Read [00-master-instruction.md](./00-master-instruction.md)

---

_Let's improve the sonarft API together! 🚀_

# Quick Start Guide  API and Bot Review

**Purpose:** Rapid setup for reviewing sonarft API and bot codebases  
**Time:** 10-15 minutes  
**Next:** Proceed to [01-architecture-structure.md](./01-architecture-structure.md) for API architecture review or [bot/README.md](../../bot/README.md) for bot structure review.

---

## Step 1: Set Up Your Environment

1. Clone the sonarft-monorepo repository:
   ```bash
   git clone https://github.com/your-org/sonarft-monorepo.git
   ```
2. Navigate to the monorepo root:
   ```bash
   cd sonarft-monorepo
   ```
3. Set up the Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install dependencies for both API and bot packages:
   ```bash
   pip install -r packages/api/requirements.txt
   pip install -r packages/bot/requirements.txt
   ```

## Step 2: Understand the Codebase

- **API:** Review the FastAPI-based backend service in `packages/api`.
- **Bot:** Explore the modular trading bot system in `packages/bot`.

## Step 3: Choose Your Review Path

| Your Goal             | Time      | Path                    |
| --------------------- | --------- | ----------------------- |
| Quick health check    | 30 min    | Quick Audit             |
| Comprehensive review  | 2-3 hours | Complete Audit          |
| Production deployment | 4-5 hours | Production Ready        |
| Specific area review  | 30-60 min | Pick individual prompts |

## Step 4: Cross-Package Review

- **Integration Points:** Focus on how the API and bot interact, especially subprocess communication and data flow.
- **Shared Modules:** Check `shared/` for schemas and types used across packages.

---

For detailed instructions, refer to the [Master Instruction](./00-master-instruction.md).
