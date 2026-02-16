# Harness Engineering: Leveraging Codex in an Agent-First World

**Source:** Ryan Lopopolo, Member of Technical Staff, OpenAI
**Published:** Feb 11, 2026
**URL:** [openai.com/index/harness-engineering/](https://openai.com/index/harness-engineering/)

---

## Executive Summary

OpenAI built and shipped an internal beta product with **zero manually-written code** over five months. Every line — application logic, tests, CI, docs, observability, internal tooling — was written by Codex agents. ~1 million lines of code, ~1,500 PRs, 3 engineers initially (3.5 PRs/engineer/day), throughput increasing as team grew to 7.

The central thesis: when agents write all the code, the engineer's job shifts from *writing code* to **designing environments, specifying intent, and building feedback loops** that allow agents to do reliable work.

---

## Key Concepts

### 1. The Engineer's New Role: Environment Design

The bottleneck was never agent capability — it was that the environment was underspecified. The primary job became **enabling agents to do useful work**:

- Break larger goals into smaller building blocks
- When something fails, ask: "what capability is missing, and how do we make it both legible and enforceable for the agent?"
- Humans steer. Agents execute.

### 2. Repository Knowledge as System of Record

The most architecturally significant pattern in the post. Everything an agent needs must live **in the repo**, because anything it can't access in-context effectively doesn't exist.

- Slack discussions, Google Docs, knowledge in people's heads = **illegible to agents**
- Code, markdown, schemas, executable plans = **the only things agents can see**
- If a Slack thread aligned the team on a pattern, it must be captured in-repo or it's lost

### 3. AGENTS.md as Table of Contents, Not Encyclopedia

They tried a monolithic instruction file and it failed because:

- **Context is scarce** — a giant file crowds out the actual task and code
- **Too much guidance becomes non-guidance** — when everything is important, nothing is
- **It rots instantly** — becomes a graveyard of stale rules
- **Hard to verify mechanically** — drift is inevitable

The fix: AGENTS.md (~100 lines) serves as a **map with pointers**, not the territory itself.

### 4. Structured Knowledge Directory

The in-repo knowledge base follows a deliberate hierarchy:

```
docs/
├── design-docs/
│   ├── index.md
│   ├── core-beliefs.md
│   └── ...
├── exec-plans/
│   ├── active/
│   ├── completed/
│   └── tech-debt-tracker.md
├── generated/
│   └── db-schema.md
├── product-specs/
│   ├── index.md
│   ├── new-user-onboarding.md
│   └── ...
├── references/
│   ├── design-system-reference-llms.txt
│   ├── nixpacks-llms.txt
│   ├── uv-llms.txt
│   └── ...
├── DESIGN.md
├── FRONTEND.md
├── PLANS.md
├── PRODUCT_SENSE.md
├── QUALITY_SCORE.md
├── RELIABILITY.md
└── SECURITY.md
```

Key properties:
- **Design docs are catalogued and indexed** with verification status
- **Core beliefs** define agent-first operating principles
- **Plans are first-class artifacts** — active, completed, and tech debt are versioned and co-located
- **References** include LLM-optimized versions of external docs (`.txt` format)
- **Progressive disclosure** — agents start with a small stable entry point and learn where to look next

### 5. Architecture Enforcement via Mechanical Rules

Agents work best in environments with strict boundaries and predictable structure:

- Rigid architectural model: each domain has fixed layers (Types -> Config -> Repo -> Service -> Runtime -> UI)
- Dependency directions are strictly validated
- Custom linters (written by Codex) enforce invariants
- Linter error messages include **remediation instructions** injected into agent context
- Enforce boundaries centrally, allow autonomy locally

Key invariants enforced:
- Structured logging
- Naming conventions for schemas and types
- File size limits
- Platform-specific reliability requirements
- Parse data shapes at boundaries (not prescriptive on how — Codex chose Zod)

### 6. Agent Legibility as Primary Design Goal

Code is optimized for **agent legibility first**, not human aesthetic preferences:

- Favor dependencies that can be fully internalized and reasoned about in-repo
- "Boring" technologies are better — composable, stable APIs, well-represented in training data
- Sometimes cheaper to reimplement than work around opaque upstream behavior
- Example: built own concurrency helper instead of using generic library, tightly integrated with their OpenTelemetry instrumentation

### 7. Making the Application Directly Inspectable

As throughput increased, bottleneck shifted to human QA. Solution: make the app itself legible to agents:

- **App bootable per git worktree** — each Codex task gets its own isolated instance
- **Chrome DevTools Protocol wired into agent runtime** — DOM snapshots, screenshots, navigation
- **Ephemeral observability stack per worktree** — logs (LogQL), metrics (PromQL), traces
- Stacks tear down after task completion
- Single Codex runs regularly work **6+ hours** on a single task (often while humans sleep)

### 8. Full End-to-End Agent Autonomy

At maturity, given a single prompt, Codex can:

1. Validate current codebase state
2. Reproduce a reported bug
3. Record a video demonstrating the failure
4. Implement a fix
5. Validate the fix by driving the application
6. Record a second video demonstrating the resolution
7. Open a pull request
8. Respond to agent and human feedback
9. Detect and remediate build failures
10. Escalate to human only when judgment is required
11. Merge the change

### 9. Entropy Management ("Garbage Collection")

Agents replicate patterns that exist — including suboptimal ones. This creates drift.

- Initial approach: 20% of week (every Friday) manually cleaning up "AI slop" — didn't scale
- Better approach: **"Golden principles"** encoded in repo + recurring cleanup process
  - Background Codex tasks scan for deviations
  - Update quality grades
  - Open targeted refactoring PRs (reviewable in under a minute, automerged)
- Two specific golden principles mentioned:
  1. Prefer shared utility packages over hand-rolled helpers (centralize invariants)
  2. No "YOLO-style" data probing — validate at boundaries or use typed SDKs
- Technical debt treated like a high-interest loan — continuous small payments, never let it compound

### 10. Doc-Gardening Agent

A recurring agent process that:
- Scans for stale or obsolete documentation
- Identifies docs that don't reflect actual code behavior
- Opens fix-up PRs automatically
- Keeps the knowledge base fresh without human maintenance burden

### 11. Merge Philosophy at Scale

Conventional engineering norms became counterproductive at high throughput:

- Minimal blocking merge gates
- Short-lived pull requests
- Test flakes addressed with follow-up runs rather than blocking progress
- Corrections are cheap, waiting is expensive
- Would be irresponsible in low-throughput; right tradeoff at agent scale

### 12. Open Questions (Their Honest Unknowns)

- How does architectural coherence evolve over **years** in a fully agent-generated system?
- Where does human judgment add the most leverage?
- How to encode judgment so it compounds?
- How will the system evolve as models become more capable?

---

## Core Terminology

| Term | Definition |
|---|---|
| **Harness Engineering** | The discipline of designing environments, feedback loops, and control systems for agent-driven development |
| **Agent Legibility** | Optimizing code, docs, and infrastructure so agents can reason about the full business domain from the repository alone |
| **Progressive Disclosure** | Agents start with small stable entry point (AGENTS.md) and follow pointers to deeper sources of truth |
| **Golden Principles** | Opinionated mechanical rules that keep the codebase legible and consistent for future agent runs |
| **Doc-Gardening** | Recurring agent process that scans for and fixes stale documentation |
| **Execution Plans** | First-class versioned artifacts (active/completed) with progress and decision logs, checked into the repo |
| **Garbage Collection** | Continuous background process to find and fix pattern drift, code slop, and accumulating tech debt |

---

## Quotable Insight

The discipline shows up more in the scaffolding rather than the code.

---

*Captured 2026-02-16 for Stage 11 Agentics research. See LAT-68.*
