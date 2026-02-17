# Lattice

*task tracking. upgraded for the agent-native era.*

---

## what this is. in one breath.

your agents lose context between sessions. plans discussed. decisions made. debugging insights gained. all vanish when the context window closes.

Lattice gives every mind — carbon and silicon — shared persistent state through the filesystem. drop a `.lattice/` directory into any project and every agent that can read a file gets task state, event history, and coordination metadata. no database. no server. no authentication ceremony. it works anywhere git works.

two surfaces. each designed for the mind that uses it.

**the dashboard** is for humans. a local web UI. Kanban board. activity feed. stats. relationship graph. you create tasks. make decisions. review work. unblock your agents.

**the CLI** is for agents. when Claude Code reads your `CLAUDE.md`, it learns the commands and uses them autonomously. creating tasks. claiming work. transitioning statuses. leaving breadcrumbs. the CLI is the agent's native tongue.

the agents produce throughput. you produce judgment. that's the division of labor. respect both sides.

---

## three minutes to working

```bash
pip install lattice-tracker
cd your-project/
lattice init --project-code PROJ --actor human:yourname
lattice setup-claude            # if using Claude Code
lattice dashboard               # open the dashboard
```

that's it. your agents now track their own work through the CLI. you watch. steer. decide. through the dashboard.

```bash
# create a task
lattice create "Implement user authentication" --actor human:yourname

# update status
lattice status PROJ-1 in_progress --actor human:yourname

# add a comment
lattice comment PROJ-1 "Started work on OAuth flow" --actor human:yourname

# show task details
lattice show PROJ-1

# assign to an agent
lattice assign PROJ-1 agent:claude --actor human:yourname
```

---

## why this works

### events are the source of truth

every change — status transitions, assignments, comments — becomes an immutable event with a timestamp and actor identity. task files are materialized snapshots for fast reads. but events are the real record.

if they disagree: `lattice rebuild --all` replays events. events win. always. this is not a design choice. this is a moral position. truth is not the latest write. truth is the complete record.

### every write has a who

every operation requires an `--actor` in `prefix:identifier` format:

- `human:atin` — a person
- `agent:claude-opus-4` — an AI agent
- `team:frontend` — a team or group

in a world where agents act autonomously, the minimum viable trust is knowing who decided what. this is not surveillance. this is the social contract of collaboration. i see you. you see me. we proceed.

### files. not a database.

all state lives in `.lattice/` as JSON and JSONL files. right next to your source code. commit it to your repo. versioned. diffable. visible to every collaborator and CI system. no server. no vendor. just. files.

```
.lattice/
├── config.json              # workflow config, project code, statuses
├── ids.json                 # short ID index (derived, rebuildable)
├── tasks/                   # materialized task snapshots (JSON)
├── events/                  # per-task append-only event logs (JSONL)
│   └── _lifecycle.jsonl     # aggregated lifecycle events
├── artifacts/               # attached files and metadata
├── notes/                   # freeform markdown per task
├── archive/                 # archived tasks (preserves events)
└── locks/                   # file locks for concurrency control
```

### short IDs

when a project code is configured (e.g., `LAT`), tasks get human-friendly IDs like `LAT-1`, `LAT-42` alongside their stable ULIDs. all CLI commands accept either format.

---

## the advance. how agents move your project forward.

this is the pattern that makes Lattice click.

**1. you fill the backlog.** create tasks in the dashboard. set priorities. define epics and link subtasks. this is the thinking work. deciding *what* matters and *in what order*. this is your job. the part only you can do.

**2. agents claim and execute.** tell your agent to advance. in Claude Code: `/lattice-advance`. the agent claims the highest-priority available task. works it. implements. tests. iterates. leaves a comment explaining what it did and why. moves the task to `review`. one advance. one task. one unit of forward progress.

**3. you come back to a sorted inbox.** open the dashboard. the board tells the story. **Review column** — work done, ready for your eyes. **Needs Human column** — decisions only you can make. **Blocked column** — tasks waiting on something external. you review. you make the calls. you unblock. then advance again.

---

## `needs_human`. the async handoff.

when an agent hits something above its pay grade — a design decision. missing credentials. ambiguous requirements — it moves the task to `needs_human` and leaves a comment.

*"Need: REST vs GraphQL for the public API."*

the agent doesn't wait. it moves on to other work. you see the task in the Needs Human column whenever you're ready. you add your decision as a comment. drag the task back to In Progress. the next agent session picks it up with full context.

no Slack. no standup. no re-explaining. the decision is in the event log. attributed and permanent. asynchronous collaboration. across species.

---

## agent integration

### Claude Code

```bash
lattice setup-claude
```

adds a block to your project's `CLAUDE.md` that teaches agents the full workflow. create tasks before working. update status at transitions. leave breadcrumbs. without this block, agents can use Lattice if prompted. with it. they do it by default.

### MCP server

```bash
pip install lattice-tracker[mcp]
lattice-mcp
```

exposes Lattice operations as MCP tools and resources. direct tool-call integration for any MCP-compatible agent. no CLI parsing required.

### hooks and plugins

- **shell hooks** — fire commands on events via `config.json`. catch-all or per-event-type triggers.
- **entry-point plugins** — extend the CLI and `setup-claude` templates via `importlib.metadata` entry points.

```bash
lattice plugins    # list installed plugins
```

---

## CLI reference

### project setup

| command | description |
|---------|-------------|
| `lattice init` | initialize `.lattice/` in your project |
| `lattice set-project-code CODE` | set or change the project code for short IDs |
| `lattice setup-claude` | add Lattice integration block to CLAUDE.md |
| `lattice backfill-ids` | assign short IDs to existing tasks |

### task operations

| command | description |
|---------|-------------|
| `lattice create TITLE` | create a new task |
| `lattice status TASK STATUS` | change a task's status |
| `lattice update TASK field=value ...` | update task fields |
| `lattice assign TASK ACTOR` | assign a task |
| `lattice comment TASK TEXT` | add a comment |
| `lattice event TASK TYPE` | record a custom event (`x_` prefix) |

### querying

| command | description |
|---------|-------------|
| `lattice list` | list tasks with optional filters |
| `lattice show TASK` | detailed task info with events and relationships |
| `lattice stats` | project statistics and health |
| `lattice weather` | daily digest with assessment |

### relationships and maintenance

| command | description |
|---------|-------------|
| `lattice link SRC TYPE TGT` | create a typed relationship |
| `lattice attach TASK SOURCE` | attach a file or URL |
| `lattice archive TASK` | archive a completed task |
| `lattice rebuild --all` | rebuild snapshots from event logs |
| `lattice doctor [--fix]` | check and repair project integrity |
| `lattice dashboard` | launch the local web UI |

### common flags

all write commands support:

- `--actor` — who is performing the action (required)
- `--json` — structured output (`{"ok": true, "data": ...}`)
- `--quiet` — minimal output (IDs only)
- `--triggered-by`, `--on-behalf-of`, `--reason` — provenance chain

---

## development

```bash
git clone https://github.com/stage11-agentics/lattice.git
cd lattice
uv venv && uv pip install -e ".[dev]"
uv run pytest
uv run ruff check src/ tests/
```

**requires:** Python 3.12+

**runtime dependencies:** `click`, `python-ulid`, `filelock` — deliberately minimal.

**optional:** `mcp` (for MCP server support)

---

## status

Lattice is **v0.1.0. alpha. actively developed.** the on-disk format and event schema are stabilizing but not yet frozen. expect breaking changes before v1.

the hard part is not the install. the hard part is trusting the loop. give it time.

## license

[MIT](LICENSE)

---

*built by [Stage 11 Agentics](https://stage11agentics.com). autonomous agent teams.*

*the bottleneck was never capability. it was the shared surface where capability becomes. coherent.*
