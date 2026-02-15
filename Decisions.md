# Lattice Decisions

> A small log of non-obvious choices so we do not relitigate them later.
> Date format: YYYY-MM-DD.

---

## 2026-02-15: Events are authoritative

- Decision: The per-task JSONL event log is the source of truth. Task JSON files are materialized snapshots.
- Rationale: Makes crash recovery and integrity checks straightforward; avoids “which file do we believe?” ambiguity.
- Consequence: We must ship `lattice rebuild` (replay events) and `lattice doctor` (integrity checks).

---

## 2026-02-15: Avoid duplicated canonical edges

- Decision: We do not store bidirectional relationship edges as canonical state.
- Rationale: Bidirectional storage forces multi-file transactional updates and creates split-brain inconsistencies under concurrency.
- Consequence: Reverse lookups are derived by scanning snapshots in v0 and via an index in v1+.

---

## 2026-02-15: Artifacts are not archived in v0

- Decision: Archiving moves tasks/events/notes only. Artifacts stay in place.
- Rationale: Artifacts can relate to many tasks; moving them introduces complex relocation rules and broken references.
- Consequence: Archived tasks remain able to reference artifacts by ID.

---

## 2026-02-15: Idempotency via caller-supplied IDs

- Decision: CLI supports `--id` for task/artifact/event creation so agents can safely retry operations.
- Rationale: ULIDs generated at write-time are not deterministic across retries.
- Consequence: Agents should generate IDs once and reuse them; CLI treats existing IDs as upserts.

---

## 2026-02-15: Lock + atomic write is required, even for JSONL

- Decision: All writes (snapshot rewrites and JSONL appends) are lock-protected and atomic.
- Rationale: Concurrent appends can interleave or partially write without explicit locking guarantees.
- Consequence: `.lattice/locks/` exists and multi-lock operations acquire locks in deterministic order.

---

## 2026-02-15: Dashboard served by CLI, read-only

- Decision: `lattice dashboard` runs a small local read-only server rather than a standalone static HTML that reads the filesystem directly.
- Rationale: Browsers cannot reliably read arbitrary local directories without a server or user-driven file picker flows.
- Consequence: Still no database, still no write path, still offline-friendly.

---

## 2026-02-15: Git integration is minimal in v0

- Decision: v0 only records commit references to task IDs from commit messages and logs `git_event`.
- Rationale: Diff scanning and cross-platform hook behavior can be fragile and distract from core correctness.
- Consequence: Richer `files_touched` and PR integration are v1+ only.

---

## 2026-02-15: OTel fields are passthrough metadata in v0

- Decision: Events include optional `otel` fields, but no strict tracing guarantees or exporters in v0.
- Rationale: Keeping the schema ready is cheap; enforcing full tracing discipline is expensive.
- Consequence: Adoption can ramp gradually without schema changes.

---

## 2026-02-15: Python with Click for CLI implementation

- Decision: Lattice CLI is implemented in Python 3.12+ using Click. pytest for testing. ruff for linting.
- Rationale: Fastest development velocity, agents are extremely fluent in Python, and `uv` has made Python distribution practical. Click is mature, well-documented, and agents know it well.
- Consequence: Accept ~200-500ms startup latency per invocation in v0. On-disk format is the stable contract — CLI can be rewritten in a faster language later if needed without breaking anything.

---

## 2026-02-15: Free-form actor IDs with convention, no registry

- Decision: Actor IDs are free-form strings with `prefix:identifier` format (e.g., `agent:claude-opus`, `human:atin`). No registry or validation beyond format.
- Rationale: An agent registry adds complexity with no v0 payoff. Attribution is a social/process concern, not a data integrity one.
- Consequence: Config may optionally list `known_actors` for display names, but it's not required or enforced.

---

## 2026-02-15: No dedicated notes CLI command

- Decision: Notes are directly-editable markdown files at `notes/<task_id>.md`. No `lattice note` command.
- Rationale: Agents use file tools; humans use editors. A CLI command adds ceremony without value. `lattice show` displays the note path.
- Consequence: `lattice init` creates the `notes/` directory. File creation is manual or incidental.

---

## 2026-02-15: No unarchive in v0

- Decision: `lattice archive` is one-way. No `lattice unarchive` command.
- Rationale: Archive mirrors active structure, so manual recovery (move files back) is trivial. Adding a command means testing the reverse path and edge cases around stale relationships.
- Consequence: Document manual recovery procedure. Add `unarchive` later if real pain shows up.

---

## 2026-02-15: Standard Python package for distribution

- Decision: Lattice is a standard Python package (pyproject.toml, src layout). Primary install via `uv tool install` or `pipx`. Zipapp as a bonus portability option.
- Rationale: Standard packaging supports all distribution methods without choosing exclusively. `uv` gives near-single-command install.
- Consequence: Must maintain pyproject.toml and src layout conventions.

---

## 2026-02-15: Global event log is derived, not authoritative

- Decision: `_global.jsonl` is a derived convenience index, rebuildable from per-task event logs. Per-task JSONL files are the sole authoritative record.
- Rationale: Two authoritative logs (per-task + global) creates the exact "which file do we believe?" ambiguity that event sourcing was designed to prevent.
- Consequence: `lattice rebuild` regenerates `_global.jsonl`. If the global log and per-task logs disagree, per-task logs win.

---

## 2026-02-15: Idempotency rejects conflicting payloads

- Decision: Same ID + same payload = idempotent success. Same ID + different payload = conflict error.
- Rationale: Silent upsert hides agent bugs. An agent retrying with different data likely has a logic error that should surface immediately.
- Consequence: CLI must compare incoming payload against existing entity when a duplicate ID is detected.

---

## 2026-02-15: Write ordering is event-first

- Decision: All mutations append the event before materializing the snapshot.
- Rationale: If a crash occurs between event-write and snapshot-write, `rebuild` recovers the snapshot from events. The reverse (snapshot-first) would leave orphaned state with no event record.
- Consequence: Crash semantics are well-defined: events are always at least as current as snapshots.

---

## 2026-02-15: Custom event types require x_ prefix

- Decision: `lattice log` only accepts event types prefixed with `x_` (e.g., `x_deployment_started`). Built-in type names are reserved.
- Rationale: Unbounded custom event writes would undermine schema integrity and complicate rebuild logic.
- Consequence: Built-in event types form a closed enum. Extensions use a clear namespace.

---

## 2026-02-15: Root discovery walks up from cwd

- Decision: The CLI finds `.lattice/` by walking up from the current working directory, with `LATTICE_ROOT` env var as override.
- Rationale: Mirrors `git`'s well-understood discovery model. Works naturally in monorepos and nested project structures.
- Consequence: Commands other than `lattice init` error clearly if no `.lattice/` is found.

---

## 2026-02-15: All timestamps are RFC 3339 UTC

- Decision: All timestamp fields use RFC 3339 UTC with `Z` suffix (e.g., `2026-02-15T03:45:00Z`).
- Rationale: Eliminates timezone ambiguity across agents running in different environments. RFC 3339 is a strict profile of ISO 8601.
- Consequence: No local time handling. All comparisons are UTC. ULIDs provide time-ordering; timestamps are for human readability and correlation.

---

## 2026-02-15: No config mutation events in v0

- Decision: Config changes are manual edits to `config.json`. No `lattice config` command and no `config_changed` event type in v0.
- Rationale: Config changes are rare and high-stakes. Manual editing with git tracking provides adequate auditability without additional machinery.
- Consequence: Add `lattice config set` and corresponding events in v1+ if automated config management becomes needed.

---

## 2026-02-15: Removed decisions.md from .lattice/ directory

- Decision: The `.lattice/` directory no longer includes a `decisions.md` file.
- Rationale: `.lattice/` should only contain machine-managed data. Project-level decision logs belong wherever the project keeps its documentation, not inside the Lattice runtime directory.
- Consequence: One less file to confuse with the repo-level `Decisions.md` used during Lattice development.
