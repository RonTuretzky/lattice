# Lattice User Guide

Lattice is Linear and JIRA reimagined for the agent-native era. It's a file-based task tracker that lives inside your project directory -- like `.git/` for project management. Where traditional tools assume humans are the primary operators with agents bolted on as integrations, Lattice treats AI agents as first-class participants in the workflow: every command supports machine-readable output, idempotent retries, and structured attribution out of the box.

Lattice is purpose-built for coordinating large-scale agentic projects -- the kind where dozens of agents work in parallel across a codebase, each picking up tasks, reporting progress, and handing off to the next. Everything is stored as plain files (JSON, JSONL, Markdown) so your project management lives alongside your code, version-controlled and inspectable.

Lattice is in active development and open source. Pull requests are welcome.

---

## Getting Started

### Install

```bash
cd lattice/
uv venv && uv pip install -e ".[dev]"
```

### Initialize a project

```bash
cd your-project/
lattice init
```

This creates a `.lattice/` directory with default configuration. You only need to do this once per project.

### Set your identity

During `lattice init`, you'll be prompted for your default actor identity. This gets saved to `.lattice/config.json` so you never have to type `--actor` on every command:

```bash
$ lattice init
Default actor identity (e.g., human:atin): human:atin
Initialized empty Lattice in .lattice/
Default actor: human:atin
```

You can also pass it non-interactively:

```bash
lattice init --actor human:atin
```

The `--actor` flag on any write command still overrides the default. Agents can also set the `LATTICE_ACTOR` env var to override per-process.

---

## Core Concepts

### Tasks

A task is the basic unit of work. It has a title, status, priority, type, and can be assigned to someone. Each task gets a unique ID like `task_01HQ...`.

### Statuses

Tasks move through a workflow. The default pipeline is:

```
backlog -> ready -> in_progress -> review -> done
```

Plus two special statuses: `blocked` and `cancelled`.

Not every transition is allowed. For example, you can't jump directly from `backlog` to `done`. If you need to, you can force it with `--force --reason "..."`.

### Actors

Every write operation needs an actor to identify who made the change. The format is `prefix:identifier`:

- `human:atin` -- a person
- `agent:claude-opus-4` -- an AI agent
- `team:frontend` -- a team

Actor IDs are free-form strings with no registry. Validation is format-only (must have a recognized prefix, a colon, and a non-empty identifier). There's no uniqueness check -- two agents using `agent:claude` are treated as the same actor.

Set a default during `lattice init` so you don't need `--actor` on every command. The resolution order is:

1. `--actor` flag (highest priority)
2. `LATTICE_ACTOR` environment variable
3. `default_actor` in `.lattice/config.json`

### Events (the source of truth)

Under the hood, Lattice is **event-sourced**. Every change (creating a task, changing status, adding a comment) is recorded as an immutable event in a per-task JSONL file. The task JSON files you see in `tasks/` are **materialized snapshots** -- derived views rebuilt from these events.

This means:
- Events are the authoritative record. Snapshots are a convenience cache.
- If a snapshot gets corrupted, `lattice rebuild` regenerates it from events.
- Writes always append the event **before** updating the snapshot. If a crash happens between the two, rebuild recovers the correct state.
- All timestamps come from the event, not the wall clock, so rebuilds are deterministic.

The lifecycle event log (`_lifecycle.jsonl`) is a derived index of task creation, archival, and unarchival events. It's rebuilt from per-task logs by `lattice rebuild --all`. If per-task logs and the lifecycle log disagree, per-task logs win.

---

## Typical Workflow

Here's what a complete task lifecycle looks like:

```bash
# Human creates and assigns a task
lattice create "Fix auth redirect bug" --type bug --priority high --actor human:atin
lattice assign task_01HQ... agent:claude --actor human:atin

# Agent picks it up
lattice status task_01HQ... in_progress --actor agent:claude

# Agent adds context
lattice comment task_01HQ... "Root cause: expired token refresh logic" --actor agent:claude

# Agent links a related task
lattice link task_01HQ... related_to task_01HX... --actor agent:claude

# Agent attaches a PR
lattice attach task_01HQ... https://github.com/org/repo/pull/42 \
  --title "PR: Fix auth redirect" --actor agent:claude

# Agent moves to review
lattice status task_01HQ... review --actor agent:claude

# Human approves and completes
lattice status task_01HQ... done --actor human:atin

# Clean up
lattice archive task_01HQ... --actor human:atin
```

---

## Creating and Managing Tasks

### Create a task

```bash
lattice create "Build login page" --actor human:atin
```

With more options:

```bash
lattice create "Fix auth redirect bug" \
  --type bug \
  --priority high \
  --urgency immediate \
  --tags "auth,security" \
  --assigned-to agent:claude \
  --description "Users are redirected to /undefined after SSO login" \
  --actor human:atin
```

**Task types:** `task`, `epic`, `bug`, `spike`, `chore`

**Priorities:** `critical`, `high`, `medium` (default), `low`

**Urgency:** `immediate`, `high`, `normal`, `low`

### Update fields

```bash
lattice update task_01HQ... title="Updated title" --actor human:atin
lattice update task_01HQ... priority=high urgency=immediate --actor human:atin
lattice update task_01HQ... tags="api,backend,urgent" --actor human:atin
```

You can update multiple fields at once. For status and assignment, use their dedicated commands instead.

**Updatable fields:** `title`, `description`, `priority`, `urgency`, `type`, `tags`

#### Custom fields (dot notation)

You can store arbitrary key-value data on tasks using dot notation:

```bash
lattice update task_01HQ... custom_fields.estimate="3d" --actor human:atin
lattice update task_01HQ... custom_fields.sprint="2026-Q1-S3" --actor human:atin
lattice update task_01HQ... custom_fields.complexity="high" --actor agent:claude
```

Custom fields are stored in the `custom_fields` object on the task snapshot. They're useful for domain-specific metadata that doesn't fit the built-in fields. Any string key works after `custom_fields.`.

### Change status

```bash
lattice status task_01HQ... in_progress --actor agent:claude
```

If the transition isn't allowed by the workflow, you'll get an error listing valid transitions. To override:

```bash
lattice status task_01HQ... done --force --reason "Completed offline" --actor human:atin
```

### Assign a task

```bash
lattice assign task_01HQ... agent:claude --actor human:atin
```

### Add a comment

```bash
lattice comment task_01HQ... "Investigated the root cause, it's a race condition in the token refresh" --actor agent:claude
```

---

## Viewing Tasks

### List all tasks

```bash
lattice list
```

Output looks like:

```
task_01HQ...  backlog  medium  task  "Build login page"  unassigned
task_01HQ...  in_progress  high  bug  "Fix auth redirect"  agent:claude
```

### Filter the list

```bash
lattice list --status in_progress
lattice list --assigned agent:claude
lattice list --tag security
lattice list --type bug
```

Filters combine with AND logic.

### Show task details

```bash
lattice show task_01HQ...
```

This prints the full task including description, relationships (both outgoing and incoming), artifacts, notes, and the complete event timeline. Use `--compact` for a brief view, or `--full` to see raw event data.

The `show` command also finds archived tasks automatically.

---

## Relationships

Tasks can be connected to each other. Lattice supports these relationship types:

| Type | Meaning |
|------|---------|
| `blocks` | This task blocks the target |
| `depends_on` | This task depends on the target |
| `subtask_of` | This task is a subtask of the target (useful for epics) |
| `related_to` | Loosely related |
| `spawned_by` | This task was spawned from work on the target |
| `duplicate_of` | This task duplicates the target |
| `supersedes` | This task replaces the target |

### How relationships are stored

Relationships are stored as **outgoing edges only** on the source task's snapshot. When you run `lattice link A blocks B`, the relationship record lives in task A's `relationships_out` array.

However, `lattice show` displays **both directions**: outgoing relationships (links this task has to others) and incoming relationships (links other tasks have to this task). Incoming relationships are derived by scanning all snapshots at read time.

### Create a link

```bash
lattice link task_01HQ... blocks task_01HX... --actor human:atin
```

With an optional note:

```bash
lattice link task_01HQ... depends_on task_01HX... \
  --note "Need the API endpoint before the UI work" \
  --actor human:atin
```

### Remove a link

```bash
lattice unlink task_01HQ... blocks task_01HX... --actor human:atin
```

---

## Artifacts

Artifacts are files or URLs attached to tasks. Use them for logs, conversation transcripts, specs, or any supporting material.

### Attach a file

```bash
lattice attach task_01HQ... ./report.pdf --actor human:atin
```

The file is copied into `.lattice/artifacts/payload/` and metadata is stored separately.

### Attach a URL

```bash
lattice attach task_01HQ... https://github.com/org/repo/pull/42 \
  --title "PR: Fix auth redirect" \
  --actor human:atin
```

### Options

```bash
lattice attach task_01HQ... ./debug.log \
  --type log \
  --title "Debug output from reproduction" \
  --summary "Stack trace showing the race condition" \
  --sensitive \
  --role "debugging" \
  --actor agent:claude
```

**Artifact types:** `file`, `conversation`, `prompt`, `log`, `reference`

The `--sensitive` flag marks artifacts that shouldn't be committed to version control.

---

## Archiving

When a task is done and you want to clean up the active list:

```bash
lattice archive task_01HQ... --actor human:atin
```

This moves the task's snapshot, events, and notes into `.lattice/archive/`. Artifacts stay in place (since multiple tasks might reference them). Archived tasks still appear in `lattice show`.

### Restoring archived tasks

If you archive a task by mistake, you can bring it back:

```bash
lattice unarchive task_01HQ... --actor human:atin
```

This moves the task's files back from archive to the active directories and records a `task_unarchived` event.

---

## Integrity and Recovery

### Health check

```bash
lattice doctor
```

This scans your `.lattice/` directory and checks for:
- Corrupt JSON/JSONL files
- Snapshot drift (snapshot out of sync with events)
- Broken relationship references
- Missing artifacts
- Self-links and duplicate edges
- Malformed IDs
- Lifecycle log inconsistencies

Use `--fix` to automatically repair truncated event log lines.

### Rebuild snapshots

If a snapshot gets corrupted or out of sync:

```bash
lattice rebuild task_01HQ...    # rebuild one task
lattice rebuild --all           # rebuild everything
```

This replays events from the authoritative event log and regenerates the snapshot files. The `--all` flag also rebuilds the lifecycle event log.

---

## Custom Events

For domain-specific events that don't fit the built-in types, use `lattice event` with an `x_` prefix:

```bash
lattice event task_01HQ... x_deployment_started \
  --data '{"environment": "staging", "sha": "abc123"}' \
  --actor agent:deployer
```

Custom event type names **must** start with `x_`. Built-in types like `status_changed` or `task_created` are reserved. Custom events are recorded in the per-task event log but do **not** go to the lifecycle log.

---

## Notes

Every task can have a markdown notes file at `.lattice/notes/<task_id>.md`. These are **not** event-sourced -- they're just regular files you edit directly with any text editor. Use them for freeform context, design notes, or running logs.

```bash
# Create or edit notes for a task
vim .lattice/notes/task_01HQ....md
```

Notes are moved to the archive alongside their task when you run `lattice archive`.

---

## Agent-Friendly Features

Lattice is built for environments where AI agents write most of the task updates. Several features make this smoother:

### JSON output

Add `--json` to any command to get structured output:

```bash
lattice create "My task" --actor agent:claude --json
```

```json
{
  "ok": true,
  "data": { ... }
}
```

Errors follow the same envelope:

```json
{
  "ok": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "Task task_01HQ... not found."
  }
}
```

### Quiet mode

Add `--quiet` to get just the ID or "ok":

```bash
TASK_ID=$(lattice create "My task" --actor agent:claude --quiet)
```

### Idempotent retries

Agents can supply their own IDs to make operations safe to retry:

```bash
lattice create "My task" --id task_01HQ... --actor agent:claude
```

If the task already exists with the same data, Lattice returns success. If it exists with *different* data, Lattice returns a conflict error. This prevents duplicate tasks from agent retries.

The same pattern works for events (`--id ev_...`) and artifacts (`--id art_...`).

### Telemetry passthrough

Agents can attach metadata to events for observability:

```bash
lattice status task_01HQ... in_progress \
  --actor agent:claude \
  --model claude-opus-4 \
  --session session-abc123
```

---

## Configuration

The workflow is defined in `.lattice/config.json`. You can customize:

- **Statuses** -- add or remove workflow states
- **Transitions** -- define which status changes are allowed
- **WIP limits** -- set advisory limits per status (warnings only in v0)
- **Task types** -- add custom types beyond the defaults
- **Defaults** -- change the default status and priority for new tasks

The default config ships with sensible Kanban defaults. Edit it directly -- it's just JSON. There is no `lattice config` command in v0.

---

## File Layout

Here's what `.lattice/` looks like on disk:

```
.lattice/
  config.json                      # Workflow configuration
  tasks/task_01HQ....json          # Task snapshots (one per task)
  events/task_01HQ....jsonl        # Event logs (one per task, append-only)
  events/_lifecycle.jsonl           # Lifecycle events (created/archived/unarchived)
  artifacts/meta/art_01HQ....json  # Artifact metadata
  artifacts/payload/art_01HQ...*   # Artifact files
  notes/task_01HQ....md            # Human-editable notes
  archive/                         # Archived tasks, events, and notes
  locks/                           # Internal lock files
```

Everything is plain text. You can `git add .lattice/` to version-control your task management. Use `.gitignore` to exclude sensitive artifact payloads and lock files.

---

## Quick Reference

| Command | What it does |
|---------|-------------|
| `lattice init` | Create a new `.lattice/` project |
| `lattice create <title>` | Create a task |
| `lattice update <id> field=value...` | Update task fields |
| `lattice status <id> <status>` | Change task status |
| `lattice assign <id> <actor>` | Assign a task |
| `lattice comment <id> "<text>"` | Add a comment |
| `lattice list` | List tasks (with optional filters) |
| `lattice show <id>` | Show full task details (incl. incoming relationships) |
| `lattice link <id> <type> <target>` | Create a relationship |
| `lattice unlink <id> <type> <target>` | Remove a relationship |
| `lattice attach <id> <file-or-url>` | Attach an artifact |
| `lattice event <id> <x_type>` | Record a custom event |
| `lattice archive <id>` | Archive a task |
| `lattice unarchive <id>` | Restore an archived task |
| `lattice doctor` | Check project integrity |
| `lattice rebuild <id\|--all>` | Rebuild snapshots from events |

All write commands need an actor (via `--actor` flag, `LATTICE_ACTOR` env var, or config `default_actor`). Add `--json` for structured output or `--quiet` for minimal output.

All validation errors list the valid options, so agents don't need to look up allowed values.
