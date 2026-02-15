# Outstanding Implementation Items

> Items specified in `ProjectRequirements_v1.md` that are not yet fully implemented. Grouped by area.

---

## Implemented (for reference)

These v0 commands and features are complete:

- `lattice init` — project initialization with default actor prompt
- `lattice create` — task creation with all options (type, priority, urgency, tags, description, assigned-to, caller-supplied ID, idempotency)
- `lattice update` — field updates including custom_fields dot notation
- `lattice status` — status changes with transition validation, `--force --reason`
- `lattice assign` — assignment changes
- `lattice comment` — comment events
- `lattice list` — task listing with filters (status, assigned, tag, type)
- `lattice show` — full task detail with bidirectional relationships, events, notes
- `lattice event` — custom event types (x_ prefix)
- `lattice link` / `lattice unlink` — relationship management
- `lattice attach` — artifact attachment (file and URL)
- `lattice archive` / `lattice unarchive` — task lifecycle
- `lattice doctor` — integrity checks with `--fix` for truncated JSONL
- `lattice rebuild` — snapshot rebuilding from events, lifecycle log regeneration
- `lattice dashboard` — read-only local HTTP server with board/list/detail/activity views
- Event-first write path with atomic writes and file locking
- Multi-lock with deterministic (sorted) ordering
- Root discovery (walk up from cwd, `LATTICE_ROOT` override)
- ULID-based IDs with type prefixes
- JSON/quiet output modes
- Actor resolution (flag > env var > config default)
- Agent telemetry passthrough (model, session)

---

## Not Yet Implemented (v0 scope)

### 1. Git Integration (Section 11.1)

**Spec says:** Optional `post-commit` hook scans commit messages for `task_...` IDs. When found, appends a `git_event` to the task's event log and optionally updates `git_context` cache.

**Status:** `git_event` is defined in `BUILTIN_EVENT_TYPES` but there is no hook installer or commit-scanning logic.

**Work needed:**
- `lattice git-hook install` — copies/links a `post-commit` hook into `.git/hooks/`
- Hook script that greps commit message for `task_` IDs and calls `lattice event` or a dedicated internal API
- Update `git_context` on task snapshot (commits array, branch)
- `lattice git-hook uninstall` to remove the hook

### 2. OTel / Tracing Passthrough (Section 9.4)

**Spec says:** Events include optional `otel` fields (`trace_id`, `span_id`, `parent_span_id`) as passthrough metadata.

**Status:** The event schema supports `agent_meta` (model, session) but the CLI does not accept `--trace_id`, `--span_id`, or `--parent_span_id` flags. The `otel` and `metrics` fields are not wired up.

**Work needed:**
- Add `--trace-id`, `--span-id`, `--parent-span-id` flags to common_options
- Add `--run-id` flag
- Include `otel` and `run_id` fields in event creation when provided
- No exporter required in v0 — just passthrough storage

### 3. Metrics Passthrough (Section 9.2)

**Spec says:** Events include optional `metrics` object (`tokens_in`, `tokens_out`, `cost_usd`, `latency_ms`, `tool_calls`, `retries`, `cache_hits`, `error_type`).

**Status:** Not implemented. No CLI flags for metrics.

**Work needed:**
- Add `--metrics` flag (accepts JSON string) to common_options or specific commands
- Include in event creation when provided

### 4. WIP Limit Warnings (Section 7.3)

**Spec says:** WIP limits are advisory warnings in v0. Config defines optional limits per status.

**Status:** Config schema supports `wip_limits` but no CLI command checks or warns when limits are exceeded.

**Work needed:**
- On `lattice status` transitions, check if the target status has a WIP limit
- If count of tasks in that status >= limit, print a warning (stderr in human mode, `warning` field in JSON mode)
- Do not block the transition — advisory only

### 5. Compact Output Flag (Section 6.2)

**Spec says:** `--compact` output mode returning minimal fields (id, title, status, priority, urgency, type, assigned_to, tags, plus optional counts).

**Status:** `compact_snapshot()` function exists in `core/tasks.py` and is used by the dashboard, but `lattice show --compact` is not implemented as a CLI flag.

**Work needed:**
- Add `--compact` flag to `lattice show`
- Use `compact_snapshot()` for output in compact mode

### 6. Sensitive Artifact Gitignore (Section 16.1)

**Spec says:** If `sensitive: true` on an artifact, payload files are gitignored by default.

**Status:** The `--sensitive` flag is accepted by `lattice attach` and stored in artifact metadata, but no `.gitignore` entry is created.

**Work needed:**
- When attaching a sensitive artifact, append the payload path to `.lattice/.gitignore` (or a project-level `.gitignore`)
- `lattice init` should create a base `.lattice/.gitignore` with `locks/` and sensitive payload patterns

### 7. Search (Section 15.1)

**Spec says:** Scan/grep across task snapshots (title, tags, status, assigned), optionally include notes.

**Status:** `lattice list` supports filtering by individual fields but there is no free-text search command.

**Work needed:**
- `lattice search <query>` — scans task titles, descriptions, tags, and optionally notes for substring/regex matches
- Return matching tasks in the standard list format
- Support `--include-notes` flag

### 8. Event/Artifact Idempotency via CLI

**Spec says (Section 4.2):** CLI supports `--id ev_...` for event appends and `--id art_...` for artifact creation with idempotent retry semantics.

**Status:**
- `lattice create --id task_...` is implemented with full idempotency checking
- `lattice event --id ev_...` — the flag is accepted but idempotency checking (same ID + same data = success, different data = conflict) may not be fully implemented
- `lattice attach --id art_...` — same situation

**Work needed:**
- Verify and implement idempotency checking for `lattice event --id`
- Verify and implement idempotency checking for `lattice attach --id`
- Add tests for both

---

## Deferred (v1+ scope, no action needed now)

These are explicitly v1+ per the spec. Listed here for awareness only:

- Run as first-class entity (currently just `run_id` on events)
- Agent registry (capabilities, health, scheduling)
- Rebuildable local index (SQLite or similar)
- Multiple workflows per team/project
- Cycle detection and critical path computation
- Hash chaining / tamper evidence
- Encryption at rest for sensitive payloads
- Per-agent access controls
- Dashboard: dependency graph visualization, run drilldowns, trace trees, telemetry views
- Full-text search across artifact payloads
- Schema migrations as explicit tools
- Operation-level dedup keys
- Real-time dashboard updates

---

## Suggested Priority Order

1. **Event/Artifact Idempotency** — Critical for agent reliability, small scope
2. **WIP Limit Warnings** — Config already supports it, small scope
3. **Compact Output** — Function exists, just needs CLI wiring
4. **OTel/Metrics Passthrough** — Schema is ready, just need CLI flags
5. **Sensitive Artifact Gitignore** — Small scope, prevents accidental commits
6. **Search** — Useful for humans navigating larger projects
7. **Git Integration** — Most complex, involves hook management and external process interaction
