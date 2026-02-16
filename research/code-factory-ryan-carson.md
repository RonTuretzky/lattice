# Code Factory: Agent-Driven Code Writing & Review

**Source:** Ryan Carson ([@ryancarson](https://x.com/ryancarson)), Feb 16 2026
**Post:** [x.com/ryancarson/status/2023452909883609111](https://x.com/ryancarson/status/2023452909883609111)
**Inspiration:** Ryan Lopopolo (OpenAI), ["Harness engineering: leveraging Codex in an agent-first world"](https://openai.com/index/harness-engineering-leveraging-codex-in-an-agent-first-world/)

---

## Executive Summary

A pattern for setting up a repository so that AI agents can **write and review 100% of the code** with deterministic, auditable standards. The core idea: one continuous loop where a coding agent writes code, the repo enforces risk-aware checks before merge, a review agent validates the PR, and evidence (tests + browser + review) is machine-verifiable.

The approach is **implementation-agnostic** — the control-plane pattern stays the same regardless of which specific code review agent (Greptile, CodeRabbit, CodeQL, custom LLM) or coding agent (Codex, Claude, etc.) is used.

---

## The 10-Step Pattern

### 1. One Machine-Readable Contract

A single JSON contract defines the entire merge policy:

- **Risk tiers by path** — which directories are high-risk vs. low-risk
- **Required checks by tier** — high-risk paths need more gates (review agent, browser evidence, smoke tests); low-risk paths need fewer
- **Docs drift rules** — control-plane changes must keep docs in sync
- **Evidence requirements** — UI/critical flows need proof artifacts

**Why it matters:** Removes ambiguity. Prevents silent drift between scripts, workflow files, and policy docs. Everything derives from one source of truth.

### 2. Preflight Gate Before Expensive CI

Run cheap policy checks first, expensive CI second:

1. Run `risk-policy-gate` first
2. Verify deterministic policy + review-agent state
3. Only then start `test/build/security` fanout jobs

**Why it matters:** Avoids wasting CI minutes on PRs already blocked by policy or unresolved review findings.

### 3. Current-Head SHA Discipline

Treat review state as valid **only** when it matches the current PR head commit:

- Wait for the review check run on `headSha`
- Ignore stale summary comments tied to older SHAs
- Fail if the latest review run is non-success or times out
- Require reruns after each synchronize/push
- Clear stale gate failures by rerunning policy gate on the same head

**Why it matters:** Without this, you can merge a PR using stale "clean" evidence — the biggest practical lesson from real PR loops.

### 4. Single Rerun-Comment Writer with SHA Dedupe

When multiple workflows can request reruns, duplicate bot comments and race conditions appear. Solution:

- Use exactly **one workflow** as the canonical rerun requester
- Dedupe by marker + `sha:<head>`
- Prevent duplicate bot comments from cluttering PRs

### 5. Automated Remediation Loop (Optional, High Leverage)

If review findings are actionable, trigger a coding agent to:

1. Read review context
2. Patch code
3. Run focused local validation
4. Push fix commit to the same PR branch
5. Let PR synchronize trigger the normal rerun path

**Guardrails:** Pin model + effort for reproducibility. Skip stale comments not matching current head. Never bypass policy gates.

### 6. Auto-Resolve Bot-Only Threads After Clean Rerun

After a clean current-head rerun:

- Auto-resolve unresolved threads where **all comments are from the review bot**
- Never auto-resolve human-participated threads
- Rerun policy gate so required-conversation-resolution reflects the new state

### 7. Browser Evidence as First-Class Proof

For UI or user-flow changes, require evidence manifests and assertions in CI (not just screenshots in PR text):

- Required flows exist
- Expected entrypoint was used
- Expected account identity is present for logged-in flows
- Artifacts are fresh and valid

### 8. Incident Memory via Harness-Gap Loop

```
production regression -> harness gap issue -> case added -> SLA tracked
```

Keeps fixes from becoming one-off patches. Grows long-term coverage. Every production incident becomes a test case.

### 9. Key Lessons from Running This in PRs

1. **Deterministic ordering matters** — preflight gate must complete before CI fanout
2. **Current-head SHA matching is non-negotiable**
3. **Review rerun requests need one canonical writer**
4. **Review summary parsing** should treat vulnerability language and weak-confidence summaries as actionable
5. **Auto-resolving bot-only threads** reduces friction, but only after clean current-head evidence
6. **A remediation agent** can shorten loop time significantly if guardrails stay strict

### 10. General Pattern vs. Specific Implementation

| General Pattern Term | One Concrete Implementation (Carson's) |
|---|---|
| Code review agent | Greptile |
| Remediation agent | Codex Action |
| Canonical rerun workflow | `greptile-rerun.yml` |
| Stale-thread cleanup | `greptile-auto-resolve-threads.yml` |
| Preflight policy | `risk-policy-gate.yml` |

Swap integration points, keep control-plane semantics.

---

## Core Concepts & Terminology

| Concept | Definition |
|---|---|
| **Code Factory** | A repo configured so agents can implement, validate, and be reviewed with deterministic, auditable standards |
| **Risk Tier** | Classification of code paths by sensitivity (high: API routes, DB schemas, legal; low: everything else) |
| **Policy Gate** | Pre-CI check that validates policy compliance before expensive jobs run |
| **SHA Discipline** | Only trusting review/evidence state that matches the exact current commit hash |
| **Harness Engineering** | Building test harnesses that agents can execute to prove correctness (term from Lopopolo/OpenAI) |
| **Evidence Manifest** | Machine-verifiable proof of UI/flow correctness (browser screenshots, assertions, identity checks) |
| **Remediation Loop** | Agent reads review findings, patches code, validates, pushes — closing the feedback loop autonomously |
| **Harness Gap** | When a production incident reveals a missing test case — tracked as debt with SLAs |

---

## The Closed Loop (Summary Pattern)

```
1. Put risk + merge policy into one contract
2. Enforce preflight gate before expensive CI
3. Require clean code-review-agent state for current head SHA
4. If findings exist, remediate in-branch and rerun deterministically
5. Auto-resolve only bot-only stale threads after clean rerun
6. Require browser evidence for UI/flow changes
7. Convert incidents into harness cases and track loop SLOs
```

---

## Useful Command Set (from Carson's Implementation)

```bash
npm run typecheck
npm test
npm run build:ci
npm run harness:legal-chat:smoke
npm run harness:ui:pre-pr
npm run harness:risk-tier
npm run harness:weekly-metrics
```

---

*Captured 2026-02-16 for Stage 11 Agentics research. See LAT-68.*
