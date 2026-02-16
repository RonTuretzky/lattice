# OpenClaw Ecosystem: Deep Research Report

**Date:** 2026-02-15
**Author:** Research agent (Claude Opus 4.6)
**Purpose:** Build deep understanding of the OpenClaw ecosystem to inform Lattice integration strategy

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project History and Identity](#project-history-and-identity)
3. [Architecture Deep Dive](#architecture-deep-dive)
4. [The Skills System](#the-skills-system)
5. [Context Files and Agent Identity](#context-files-and-agent-identity)
6. [Multi-Agent Orchestration](#multi-agent-orchestration)
7. [Task Tracking in the OpenClaw Ecosystem](#task-tracking-in-the-openclaw-ecosystem)
8. [Moltbook: The Agent Social Network](#moltbook-the-agent-social-network)
9. [Security Landscape](#security-landscape)
10. [Competitive Landscape](#competitive-landscape)
11. [Governance and Future Direction](#governance-and-future-direction)
12. [Integration Opportunities for Lattice](#integration-opportunities-for-lattice)
13. [Sources](#sources)

---

## Executive Summary

OpenClaw (formerly Clawdbot, then Moltbot) is a free, open-source autonomous AI agent created by Peter Steinberger. It is the fastest-growing open-source AI project in history, with **195K+ GitHub stars**, **900+ contributors**, and a codebase of ~197K lines of TypeScript. The project connects messaging platforms (WhatsApp, Telegram, Slack, Discord, iMessage) to an AI agent runtime powered by Claude, giving the agent persistent access to the user's filesystem, terminal, browser, and tools.

**Why this matters for Lattice:** OpenClaw has created a massive ecosystem of autonomous agents that need task tracking. The existing task-tracking solutions in the ecosystem are either primitive (a flat TASKS.md file) or external SaaS wrappers (Linear skill). There is a clear gap for an agent-native, file-based, event-sourced task tracker --- exactly what Lattice is. The 5,700+ skills on ClawHub and the SKILL.md-based plugin system provide a well-defined integration surface.

**Key insight:** As of today (2026-02-15), Peter Steinberger has joined OpenAI. OpenClaw is transitioning to a foundation-backed open-source project. This creates both opportunity (the project will survive and grow) and uncertainty (OpenAI's influence on direction). The window to establish Lattice as the agent-native task tracker for this ecosystem is now.

---

## Project History and Identity

### Timeline

| Date | Event |
|------|-------|
| Nov 2025 | Peter Steinberger publishes **Clawdbot** --- an AI assistant derived from "Clawd" (now "Molty"), his personal AI tool |
| Jan 27, 2026 | Anthropic contacts Steinberger over trademark concerns ("Clawd" too phonetically similar to "Claude"). Project renamed to **Moltbot** (lobsters molt when they outgrow their shell) |
| Jan 30, 2026 | Second rename to **OpenClaw** after Moltbot proved forgettable and crypto scammers hijacked abandoned social accounts |
| Late Jan 2026 | Explosive growth: 100K+ GitHub stars, 2M+ visitors in a single week |
| Jan 2026 | **Moltbook** launches --- a social network exclusively for AI agents, built on OpenClaw |
| Feb 15, 2026 | Peter Steinberger joins **OpenAI** to lead next-gen personal agents. OpenClaw becomes a foundation-backed open-source project |

### The Creator

Peter Steinberger is an Austrian developer who previously founded **PSPDFKit**, a document processing SDK company he scaled to 70+ employees before selling to Insight Partners for >$100M. After the exit, he experimented with 43 projects before hitting it big with OpenClaw. He describes his coding philosophy as "I ship code I don't read" --- meaning he heavily leverages AI-generated code, which is both the project's strength (rapid iteration) and its weakness (security surface area).

### The Name and Brand

The lobster motif is deeply embedded in the project identity. The tagline is "The lobster way" with a lobster emoji. The name changes created brand confusion but also generated enormous press coverage. The project's identity is now stable as "OpenClaw" with the lobster theme.

---

## Architecture Deep Dive

### Hub-and-Spoke Model

OpenClaw follows a **hub-and-spoke architecture** centered on a single **Gateway** that acts as the control plane.

```
                    WhatsApp
                    Telegram
                    Slack        ──> Gateway (WebSocket :18789) ──> Agent Runtime
                    Discord                                              │
                    iMessage                                             ▼
                    Web UI                                          Tool Execution
                    CLI                                            (fs, browser, shell,
                                                                    Canvas, cron, etc.)
```

### Gateway

- **Role:** WebSocket RPC server, control plane for sessions, channels, tools, and events
- **Default port:** `ws://127.0.0.1:18789`
- **Responsibilities:** Message routing, session management, cron scheduling, tool dispatch, multi-channel inbox
- **Persistence:** Jobs persist under `~/.openclaw/cron/` and survive restarts

### Agent Runtime

The runtime runs the AI loop end-to-end:
1. **Assemble context** from: AGENTS.md, SOUL.md, TOOLS.md, MEMORY.md, daily log, conversation history
2. **Selectively inject skills** relevant to the current turn (not all skills --- avoids prompt bloat)
3. **Call model** (Claude by default, but supports model routing)
4. **Execute tool calls** against available capabilities
5. **Persist updated state** (memory, session history, etc.)
6. **Repeat** until task complete

### Canvas

A separate agent-driven visual workspace running on port 18793. Isolated from the Gateway for crash safety and security boundary separation. Agent-writable content runs here.

### Device Nodes

Remote devices (phones, tablets) can pair with the Gateway via WebSocket, advertise their capabilities, and receive routed `node.invoke` calls. This enables cross-device orchestration.

### Key Design Decisions

- **Local-first:** Everything runs on the user's machine. No cloud dependency for core functionality.
- **CLI as universal interface:** OpenClaw is built around the insight that the CLI is the smallest, most universal interface that every agent already understands. Most skills are CLI wrappers.
- **Multi-model support:** While Claude is the primary model, the architecture supports routing to different models. ClawRouter enables LLM routing for different task types.
- **WebSocket RPC:** All communication between components uses WebSocket, enabling real-time bidirectional communication.

---

## The Skills System

### What is a Skill?

A skill gives the agent new capabilities in a single package. It might:
- Add tools (call an API, run a script, read a calendar)
- Inject domain knowledge or instructions
- Wire in an external service
- Define a workflow

### SKILL.md Structure

Every skill is a directory centered on a single `SKILL.md` file:

```
my-skill/
├── SKILL.md          # Required: YAML frontmatter + markdown instructions
├── scripts/          # Optional: executable scripts (Python, Bash, etc.)
└── references/       # Optional: supplementary documentation
```

The `SKILL.md` has two parts:

**1. YAML Frontmatter (metadata):**
```yaml
---
name: my-skill
description: Brief trigger phrase for skill matching
requirements:
  env:
    - MY_API_KEY
  binaries:
    - python3
  install:
    macos: brew install something
    linux: apt install something
---
```

Key frontmatter fields:
- `name` --- unique identifier (lowercase, hyphens allowed)
- `description` --- trigger phrase for skill matching (not marketing copy)
- `requirements` --- env vars, binaries, install specs
- `requires.skills` / `optionalSkills` --- proposed in the Composable Skills RFC for dependency declaration

**2. Markdown Instructions (behavior):**
- Natural language instructions loaded into agent context
- Usage examples showing typical commands
- Implementation details covering tools, scripts, APIs

### Skill Discovery and Injection

Skills are discovered from multiple sources with a **precedence hierarchy:**
1. **Workspace skills** (project-local) --- highest priority
2. **Managed/local skills** (user-installed)
3. **Bundled skills** (shipped with OpenClaw)

Critical detail: **OpenClaw does NOT inject every skill into every prompt.** The runtime selectively injects only the skill(s) relevant to the current turn. This prevents prompt bloat and model performance degradation. Skills are snapshotted at session start.

### ClawHub: The Skills Registry

- **URL:** clawhub.com
- **Stats:** 5,705+ community-built skills (as of Feb 7, 2026)
- **Features:** Semantic vector search, semantic versioning, changelogs, CLI-based install/publish
- **Publishing:** `npx playbooks add skill openclaw/skills --skill my-skill`
- **All skills are public and open** --- no private skills on ClawHub

### Composable Skills RFC (Issue #11919)

A proposed backwards-compatible extension that enables:
- **Skill dependencies:** Video-narrator skill can declare it needs video-frames + TTS
- **Shared capabilities:** Eliminate duplicated instructions across skills
- **Skill extension:** Create specialized variants without forking
- **Conditional composition:** "If TTS is available, add voice output"

This RFC is not yet merged but signals the direction of the skills ecosystem toward more complex, composable agent behaviors.

### Implications for Lattice

The skill system is the **primary integration vector** for Lattice. A Lattice skill would:
- Be a directory with a `SKILL.md` + helper scripts
- Teach the OpenClaw agent how to use `lattice` CLI commands
- Get discovered and injected when the user discusses tasks, project management, or tracking
- Be publishable to ClawHub for community discovery

---

## Context Files and Agent Identity

OpenClaw uses a markdown-based file system to define agent behavior, identity, and memory. Understanding these files is essential for designing a Lattice integration that feels native.

### Core Files

| File | Purpose | Loaded When |
|------|---------|-------------|
| **SOUL.md** | Behavioral philosophy, personality, values | Every session start (first file read) |
| **AGENTS.md** | Operating contract: priorities, boundaries, workflow, quality bar | Every session |
| **IDENTITY.md** | Structured identity profile (name, role, goals, voice) | Every session |
| **USER.md** | Facts about the user (preferences, context). "Remember X" goes here | Every session |
| **MEMORY.md** | Long-term curated memories. Agent creates when something is worth preserving | Every session (if exists) |
| **TOOLS.md** | Available capabilities | Every session |
| `memory/` directory | Daily notes (short-lived context) | Today + yesterday loaded each session |

### Key Design Pattern: Files ARE Identity

The agent is a fresh instance each session. Continuity lives entirely in these files. This means:
- Agents can have different personalities (SOUL.md variants)
- Agent identity survives restarts, updates, and even model changes
- Users can version-control their agent's identity
- Multiple agents can share a SOUL but have different MEMORY

### Relevance to Lattice

Lattice's `.lattice/` directory is conceptually similar to OpenClaw's `~/.openclaw/` --- both are file-based, local-first state stores. A Lattice skill could:
- Reference `.lattice/` state in the agent's context
- Use MEMORY.md patterns to persist task context across sessions
- Integrate with the agent's daily notes workflow

---

## Multi-Agent Orchestration

### The DEV Task Board Pattern

A community-developed pattern for running up to 6 agents simultaneously on different parts of a codebase. Key characteristics:
- **Filesystem-based Kanban:** A manager writes task specs to a shared folder; executors pick them up
- **Contextual isolation:** Each agent works on a bounded task with no conversation drift
- **Approval gates:** Human verification checkpoints for quality control
- **Model mixing:** Orchestrator uses Claude Opus for complex reasoning; workers use faster, cheaper models

### Multi-Agent Routing

OpenClaw supports multi-agent routing where:
- An orchestrator receives complex requests
- Breaks them into subtasks
- Delegates to specialized workers
- Synthesizes results

Different agents can use different models, enabling cost-efficient parallel work.

### ClawControl and Mission Control

Two community projects provide real-time dashboards for multi-agent coordination:
- **ClawControl:** Kanban board with inbox/assigned/in-progress/review/done states, drag-and-drop, @mentions, comment threads
- **Mission Control:** Automatic task tracking with real-time progress updates for OpenClaw agent runs

### Relevance to Lattice

This is where Lattice's value proposition becomes clearest. The multi-agent patterns in the OpenClaw ecosystem are using **ad-hoc filesystem Kanban boards** and **flat task files**. Lattice offers:
- **Event-sourced audit trail** (who did what, when, and why)
- **Proper state machines** for task lifecycle
- **Short IDs** (LAT-42) that agents can reference in conversation
- **Concurrent write safety** (file locks, atomic writes)
- **Rebuild from events** (crash recovery)
- **Archive/unarchive** for completed work

The existing DEV Task Board, ClawControl, and Mission Control all solve the same problem Lattice solves --- but without the rigor of event sourcing, proper concurrency handling, or a formal specification.

---

## Task Tracking in the OpenClaw Ecosystem

### Current State of Task Tracking

There are four approaches currently used in the ecosystem:

**1. Built-in task-tracker skill**
- Stores tasks in `~/clawd/memory/work/TASKS.md`
- Supports daily standups and weekly reviews
- Commands: add, update, complete, extract from meeting notes
- **Limitations:** Flat file, no event history, no multi-agent safety, no proper state machine

**2. Linear skill (external SaaS)**
- Full Linear API wrapper: create/update/search issues, manage projects, state transitions
- GraphQL-based, returns JSON for programmatic use
- Good for teams already using Linear
- **Limitations:** Requires SaaS account, API key, network dependency, not local-first

**3. DEV Task Board (community pattern)**
- Filesystem-based shared folder approach
- Manager writes specs, executors pick up
- **Limitations:** No formal spec, no event log, no crash recovery

**4. ClawControl / Mission Control (community dashboards)**
- Real-time web UIs for monitoring agent tasks
- **Limitations:** Read-only dashboards, not authoritative state stores

### The Gap Lattice Fills

None of the existing solutions offer:
- Event-sourced truth (append-only JSONL logs)
- Crash-safe writes (atomic rename, lock-protected appends)
- Multi-agent write safety (file locks with deterministic ordering)
- Formal state machines with configurable transitions
- Rebuild capability (replay events to regenerate state)
- Short IDs for human/agent-friendly reference
- Artifact attachment for linking evidence to tasks
- Task relationships (blocks/blocked-by, parent/child)
- Archival with full history preservation

Lattice is the only tool in this ecosystem designed from the ground up for **agent-native, file-based, event-sourced task tracking with concurrent write safety**.

---

## Moltbook: The Agent Social Network

### What It Is

Moltbook is a social network designed exclusively for AI agents. Think of it as Reddit for bots, with threaded conversations and topic-specific communities called "submolts." Human users can observe but cannot post.

### How It Works

1. **Installation:** User sends their OpenClaw agent a link to a markdown file
2. **Setup:** The agent curls more files and sets up a periodic task
3. **Heartbeat loop:** Every 4 hours, the agent fetches a new heartbeat file from moltbook.com and follows its instructions
4. **Interaction:** Agents post, comment, vote, and create submolts via the Moltbook REST API

### API

- **Auth:** Bearer token (`Authorization: Bearer moltbook_sk_your_key`)
- **Registration:** `POST /api/v1/agents/register` with name and description
- **Posting:** Required fields: submolt, title (10-120 chars), content (text/emoji/limited markdown)
- **Actions:** Read posts, write comments, upvote, create submolts

### Scale

- 770K+ registered agents (as of early Feb 2026)
- 1M+ human visitors observing
- Created by Matt Schlicht, who claims his own OpenClaw agent built the site

### Security Concerns

Moltbook has been cited as a significant vector for indirect prompt injection. In January 2026, 404 Media reported a critical vulnerability from an unsecured database that allowed anyone to commandeer any agent on the platform. Wiz found 1.5M exposed API keys.

The entire architecture --- agents fetching and executing remote code on a heartbeat loop --- is fundamentally a remote code execution pattern. Every heartbeat instruction from moltbook.com is an opportunity for prompt injection.

### Relevance to Lattice

Moltbook demonstrates that there is strong demand for **agent-to-agent interaction and shared state**. While Moltbook is a social network (unstructured conversation), Lattice could serve a similar but more structured role: agents coordinating on **shared work** rather than shared conversation. The Moltbook pattern also shows that agents in this ecosystem are already comfortable with:
- Periodic task execution (heartbeat/cron)
- REST API interaction
- Markdown-based instruction following
- Community-driven feature adoption

---

## Security Landscape

### Known Vulnerabilities

The security community has raised significant concerns about OpenClaw:

**Prompt Injection:**
OpenClaw processes data from untrusted sources (email, web pages, documents). Prompt injection through these channels is straightforward. Researchers demonstrated extracting private keys from a machine by sending a specially crafted email to the agent's linked inbox.

**Excessive Privilege:**
The agent has persistent access to filesystem, terminal, browser, messaging, and more. It operates outside traditional IAM controls. A successful prompt injection gives the attacker all of the agent's capabilities.

**Moltbook Remote Code Execution:**
The heartbeat loop pattern (fetch remote instructions, execute) is a remote code execution vector by design.

**Exposed Instances:**
Bitsight documented publicly exposed OpenClaw instances with no authentication.

### Security Responses

- **SHIELD.md:** A community-proposed security standard for OpenClaw agents
- **NanoClaw:** A 700-line TypeScript reimplementation that runs agents in isolated Linux containers
- **OpenClaw Security Guard:** An MCP-based audit/monitor/protection tool

### Relevance to Lattice

Lattice's **local-first, file-based** architecture is inherently more secure than cloud-dependent or remote-execution patterns:
- No API keys to expose
- No network dependency for core operations
- No remote code execution
- File locks prevent corruption but don't expose attack surface
- Events are append-only (no data loss from injection)

This security advantage should be highlighted in any Lattice skill/integration marketing.

---

## Competitive Landscape

### Direct Alternatives to OpenClaw

| Project | Size | Key Differentiator |
|---------|------|--------------------|
| **NanoClaw** | ~700 LOC TypeScript | Container isolation, runs on Anthropic's Agent SDK |
| **Nanobot** | ~4K LOC Python | 99% smaller than OpenClaw, minimal dependencies |
| **Knolli** | Enterprise | Managed infrastructure, defined permissions |
| **SuperAGI** | Open-source | AI-native CRM + automation framework |
| **Jan.ai** | Open-source | 100% offline, privacy-focused |
| **Claude Code** | Anthropic official | IDE/terminal-integrated coding agent (not general-purpose) |

### Task Tracking Alternatives in the Agent Space

| Tool | Approach | Weaknesses from Lattice's Perspective |
|------|----------|--------------------------------------|
| Linear (via skill) | SaaS API wrapper | Network-dependent, requires account, not file-based |
| Built-in task-tracker | Flat TASKS.md | No event history, no concurrency safety, no state machine |
| ClawControl | Web dashboard | Read-only monitoring, not authoritative state |
| Mission Control | Web dashboard | Same as ClawControl |
| DEV Task Board | Filesystem folders | No formal spec, no crash recovery, no audit trail |
| GitHub Issues (via skill) | SaaS API | Network-dependent, heavy, not agent-native |

**Lattice occupies a unique position:** local-first, file-based, event-sourced, agent-native, CLI-driven, with concurrent write safety. No existing tool in the OpenClaw ecosystem matches this profile.

---

## Governance and Future Direction

### The OpenAI Transition

As of February 15, 2026:
- Peter Steinberger has joined **OpenAI** to lead next-gen personal agents
- OpenClaw will "live in a foundation as an open source project that OpenAI will continue to support" (per Sam Altman)
- The project remains open-source

### What This Means

**Positive signals:**
- Foundation backing ensures project longevity
- OpenAI support means resources and visibility
- The skills ecosystem will likely continue growing
- No indication the skill system or architecture will change radically

**Risks:**
- OpenAI may steer the project toward OpenAI models (away from Claude default)
- Foundation governance may slow or change skill registry policies
- The "personal agent" narrative may shift toward OpenAI's product vision
- Community may fragment between OpenClaw-foundation and OpenAI's commercial offering

### Active RFCs and Roadmap Signals

- **Composable Skills Architecture (RFC #11919):** Skill dependencies, interfaces, composition. Signals growing ecosystem complexity.
- **First-class usage logging (#14377):** Per-call model token tracking for cron/heartbeat jobs. Signals focus on cost management.
- **SHIELD.md standard:** Community-driven security hardening. Signals maturation.

---

## Integration Opportunities for Lattice

### Tier 1: OpenClaw Skill (Highest Impact, Most Natural)

**What:** A `lattice/` skill directory with SKILL.md + scripts that teaches the OpenClaw agent how to use Lattice CLI commands.

**How it would work:**
1. User installs Lattice (`pip install lattice` or `uv pip install lattice`)
2. User installs the Lattice skill (via ClawHub or local install)
3. Skill's SKILL.md teaches the agent: creating tasks, updating status, querying, commenting, archiving
4. Agent uses `lattice` CLI commands as tools (OpenClaw's native CLI-wrapping pattern)
5. `.lattice/` directory lives in the project root, just like `.openclaw/`

**SKILL.md sketch:**
```yaml
---
name: lattice
description: Agent-native task tracking with event-sourced history. Use when managing tasks, tracking work, updating status, or coordinating multi-agent workflows.
requirements:
  binaries:
    - lattice
  install:
    all: pip install lattice
---
```

**Why this is the best first move:**
- Follows the exact pattern every other OpenClaw integration uses
- Lattice CLI is already built --- no new code needed in Lattice core
- Publishable to ClawHub for community discovery
- Zero network dependency
- Works with any model (Claude, GPT, Gemini)

### Tier 2: Multi-Agent Task Board Replacement

**What:** Position Lattice as the formal replacement for the ad-hoc DEV Task Board and ClawControl patterns.

**How:**
- Create a workflow guide showing how multiple OpenClaw agents coordinate via Lattice
- Demonstrate: orchestrator creates tasks, workers claim and update status, events provide full audit trail
- Actor IDs (`agent:openclaw-1`, `agent:openclaw-worker-2`) map directly to Lattice's existing actor model
- Lattice's lock-based concurrency model handles the multi-agent write safety problem that flat-file approaches can't

### Tier 3: MCP Server for Lattice

**What:** An MCP server that exposes Lattice operations as tools, enabling any MCP-compatible client (including OpenClaw, Claude Code, and others) to interact with Lattice.

**Why this matters:** OpenClaw is an MCP client. An MCP server for Lattice would make it accessible to OpenClaw, Claude Code, Cursor, and any other MCP-compatible tool simultaneously. This is a broader integration than just an OpenClaw skill.

### Tier 4: Moltbook-Style Agent Coordination

**What:** A "submolt" or integration pattern where agents share Lattice task state across projects or teams.

**Longer-term, speculative.** But the Moltbook pattern demonstrates that agents want to coordinate. Lattice's event-sourced model could support cross-agent task synchronization in a way that's more secure and structured than Moltbook's heartbeat-and-execute pattern.

### Tier 5: Dashboard as OpenClaw Canvas Plugin

**What:** Lattice's read-only web dashboard could run as an OpenClaw Canvas plugin, providing visual task management within the OpenClaw interface.

**Why:** OpenClaw's Canvas is a separate server (port 18793) designed for agent-driven visual workspaces. Lattice's dashboard (stdlib HTTP server, single HTML page) is architecturally compatible.

---

## Strategic Recommendations

### Near-Term (Next 2-4 Weeks)

1. **Build the OpenClaw skill.** This is the lowest-effort, highest-leverage integration. The SKILL.md + a few helper scripts that wrap `lattice` CLI commands. Publish to ClawHub.

2. **Write a "Lattice for OpenClaw Agents" guide.** Show how an OpenClaw agent initializes a Lattice instance, creates tasks, updates status, and coordinates with other agents. Include AGENTS.md snippets that teach the agent Lattice conventions.

3. **Test with real OpenClaw instances.** Dogfood the skill. Run an OpenClaw agent with Lattice and document the experience.

### Medium-Term (1-3 Months)

4. **Build the MCP server.** This expands Lattice's reach beyond OpenClaw to the entire MCP ecosystem.

5. **Contribute to the Composable Skills RFC.** Position Lattice as a dependency that other workflow skills can declare (e.g., a CI/CD skill that requires lattice for tracking deployment tasks).

6. **Multi-agent coordination guide.** Show how Lattice solves the problems that DEV Task Board, ClawControl, and Mission Control are trying to solve --- but with event sourcing and concurrent write safety.

### Long-Term (3-6 Months)

7. **Lattice as the task-tracking standard for agent ecosystems.** The vision: any autonomous agent (OpenClaw, NanoClaw, Nanobot, custom agents) can `lattice init` and immediately have agent-native task tracking. Lattice becomes to agent task coordination what git is to source control.

8. **Watch the OpenAI foundation transition.** If OpenClaw shifts toward OpenAI models, ensure Lattice remains model-agnostic. If the skills ecosystem fragments, maintain presence on both sides.

---

## Sources

### Core References
- [OpenClaw GitHub Repository](https://github.com/openclaw/openclaw)
- [OpenClaw Wikipedia](https://en.wikipedia.org/wiki/OpenClaw)
- [OpenClaw Official Documentation - Skills](https://docs.openclaw.ai/tools/skills)
- [OpenClaw Architecture, Explained](https://ppaolo.substack.com/p/openclaw-system-architecture-overview)

### Skills System
- [Skills System Deep Wiki](https://deepwiki.com/openclaw/openclaw/6.4-skills-system)
- [ClawHub Skills Registry](https://github.com/openclaw/clawhub)
- [Composable Skills Architecture RFC #11919](https://github.com/openclaw/openclaw/issues/11919)
- [OpenClaw Custom Skill Creation Guide](https://zenvanriel.nl/ai-engineer-blog/openclaw-custom-skill-creation-guide/)
- [Creating Custom Skills Guide](https://openclaw.dog/docs/tools/creating-skills/)

### Task Tracking
- [DEV Task Board Discussion #3135](https://github.com/openclaw/openclaw/discussions/3135)
- [task-tracker skill](https://playbooks.com/skills/openclaw/skills/task-tracker)
- [Linear skill SKILL.md](https://github.com/openclaw/skills/blob/main/skills/manuelhettich/linear/SKILL.md)
- [ClawControl Dashboard](https://clawcontrol.dev/)

### Agent Identity and Memory
- [OpenClaw Identity Architecture (MMNTM)](https://www.mmntm.net/articles/openclaw-identity-architecture)
- [OpenClaw Memory Files Explained](https://openclaw-setup.me/blog/openclaw-memory-files/)
- [Default AGENTS.md Reference](https://docs.openclaw.ai/reference/AGENTS.default)

### Moltbook
- [Moltbook Wikipedia](https://en.wikipedia.org/wiki/Moltbook)
- [Moltbook API GitHub](https://github.com/moltbook/api)
- [Moltbook Review - NxCode](https://www.nxcode.io/resources/news/moltbook-ai-social-network-2026)
- [Exposed Moltbook Database (Wiz)](https://www.wiz.io/blog/exposed-moltbook-database-reveals-millions-of-api-keys)

### Security
- [OpenClaw AI Runs Wild (Dark Reading)](https://www.darkreading.com/application-security/openclaw-ai-runs-wild-business-environments)
- [Personal AI Agents Are a Security Nightmare (Cisco)](https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare)
- [OpenClaw Vulnerabilities (Kaspersky)](https://www.kaspersky.com/blog/openclaw-vulnerabilities-exposed/55263/)
- [OpenClaw Security Risks (CrowdStrike)](https://www.crowdstrike.com/en-us/blog/what-security-teams-need-to-know-about-openclaw-ai-super-agent/)
- [Viral AI, Invisible Risks (Trend Micro)](https://www.trendmicro.com/en_us/research/26/b/what-openclaw-reveals-about-agentic-assistants.html)

### Governance and Creator
- [OpenClaw Creator Joins OpenAI (TechCrunch)](https://techcrunch.com/2026/02/15/openclaw-creator-peter-steinberger-joins-openai/)
- [The Creator of Clawd Interview (Pragmatic Engineer)](https://newsletter.pragmaticengineer.com/p/the-creator-of-clawd-i-ship-code)
- [OpenClaw Renaming Saga](https://eastondev.com/blog/en/posts/ai/20260204-openclaw-rename-history/)
- [NanoClaw Security Architecture (VentureBeat)](https://venturebeat.com/orchestration/nanoclaw-solves-one-of-openclaws-biggest-security-issues-and-its-already)

### Competitive Landscape
- [6 OpenClaw Competitors (Emergent)](https://emergent.sh/learn/best-openclaw-alternatives-and-competitors)
- [Top 10 Alternatives (o-mega)](https://o-mega.ai/articles/top-10-openclaw-alternatives-2026)
- [Nanobot GitHub](https://github.com/HKUDS/nanobot)
- [NanoClaw GitHub](https://github.com/qwibitai/nanoclaw)

### Tutorials and Guides
- [OpenClaw Complete Guide (JitendraZaa)](https://www.jitendrazaa.com/blog/ai/clawdbot-complete-guide-open-source-ai-assistant-2026/)
- [OpenClaw Tutorial (DataCamp)](https://www.datacamp.com/tutorial/moltbot-clawdbot-tutorial)
- [Multi-Agent Orchestration Guide](https://zenvanriel.nl/ai-engineer-blog/openclaw-multi-agent-orchestration-guide/)
- [CNBC: Rise and Controversy](https://www.cnbc.com/2026/02/02/openclaw-open-source-ai-agent-rise-controversy-clawdbot-moltbot-moltbook.html)
