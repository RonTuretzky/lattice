# LAT-103 Plan Review: Epics as Derived-Status Bottom-Lane Containers

## Executive Verdict
The core product direction is correct: epics should be rollups, not workflow cards. But the current plan is under-specified in critical areas (status precedence, event semantics, CLI compatibility, and performance boundaries). If implemented as-is, it will create inconsistent behavior across Board/CLI/Stats and regress operability.

My recommendation is to treat this as a read-model change first (effective/derived fields), then tighten write semantics for epics.

## Ground Truth in Current Code
- Board currently groups every task by raw `status`, regardless of `type`, and renders all cards as draggable (`src/lattice/dashboard/static/index.html:5814`, `src/lattice/dashboard/static/index.html:5828`, `src/lattice/dashboard/static/index.html:5984`).
- Dashboard detail UIs allow status change for any non-archived task via `/api/tasks/<id>/status` (`src/lattice/dashboard/static/index.html:5221`, `src/lattice/dashboard/static/index.html:5342`, `src/lattice/dashboard/static/index.html:6151`, `src/lattice/dashboard/static/index.html:6323`).
- Dashboard server `/api/tasks` and `/api/graph` return snapshot `status` directly; no derived status exists (`src/lattice/dashboard/server.py:249`, `src/lattice/dashboard/server.py:383`, `src/lattice/dashboard/server.py:406`).
- Dashboard server `/api/tasks/<id>/status` permits any task type (`src/lattice/dashboard/server.py:709`).
- CLI `lattice status` also allows status transitions for any task (`src/lattice/cli/task_cmds.py:463`).
- CLI `lattice list --status` filters against raw snapshot status (`src/lattice/cli/query_cmds.py:288`, `src/lattice/cli/query_cmds.py:354`).
- Snapshot materialization is status-event driven (`status_changed`) and `status` is a protected field (`src/lattice/core/tasks.py:11`, `src/lattice/core/tasks.py:178`).
- Event model explicitly treats per-task logs as authoritative and lifecycle as derived (`Decisions.md:8`, `Decisions.md:112`, `Decisions.md:128`).
- Three-tier hierarchy is a stated project decision using `subtask_of` relationships (`Decisions.md:437`).

## 1) Derived Status Computation: Where It Should Live + Algorithm
It should live in shared core read logic, not in dashboard-only JS and not in ad hoc CLI filtering.

Recommended placement:
- Add a shared derivation module (for example `lattice/core/derived.py`) used by:
1. Dashboard API handlers (`/api/tasks`, `/api/graph`, task detail)
2. CLI query commands (`list`, `show`, `next`)
3. Stats builder (optional phase 2)

Why this is mandatory:
- Today each surface reads raw snapshot status independently. If derivation is only in Board, semantics will diverge immediately.

Algorithm recommendation (epics):
1. Build a `subtask_of` adjacency map once (`child -> parent`, `parent -> children`) from active snapshots.
2. For each epic, roll up leaf descendants (not only direct children), with cycle detection.
3. Compute:
- `effective_status`
- `progress` (`done_count`, `cancelled_count`, `total_leaf_count`)
- `health` (`blocked_count`, `needs_human_count`, `active_count`)
4. Status precedence should be:
- `needs_human` if any descendant in `needs_human`
- else `blocked` if any descendant in `blocked`
- else `in_progress` if any descendant in active states (`in_progress`, `in_planning`, `review`)
- else `done` if all descendants are terminal (`done` or `cancelled`)
- else `backlog`

Opinionated call: the plan’s proposed precedence (“if any in_progress then in_progress”) is wrong because it hides `blocked`/`needs_human` urgency.

Edge cases that must be explicit:
- Epic with zero descendants: mark as `unscoped` health state; do not silently claim healthy progress.
- Cycles in `subtask_of`: detect and surface warning; break traversal deterministically.
- Archived descendants: decide policy explicitly (recommended: exclude archived from active rollup).

## 2) Backward Compatibility / Migration
No snapshot rewrite migration is required for v1 rollout.

Recommended compatibility model:
- Keep raw `status` field untouched for existing epics.
- Introduce derived fields in read APIs and CLI output:
- `status_raw`
- `status_effective`
- `epic_rollup` object
- UI surfaces read `status_effective` for epics.

This avoids breaking old data and preserves deterministic rebuild behavior.

## 3) Event Model Impact
Do not emit synthetic `status_changed` events for epic rollups.

Why:
- It pollutes history with computed noise.
- It violates “events are authoritative” boundaries by mixing user intent with derived projection churn.
- It creates misleading time-in-status analytics.

Recommended event posture:
- Keep `status_changed` as human/agent intent for actionable tasks.
- For epics, status is projection-only.
- Lifecycle log behavior remains unchanged (still only create/archive/unarchive events).

## 4) CLI Impact
`lattice status <epic> <status>` should be rejected with a clear validation error.

Suggested behavior:
- Error code: `DERIVED_STATUS_TASK_TYPE` (or similar).
- Message: “Epic status is derived from descendants; update subtasks instead.”

`lattice list --status ...`:
- Must define whether filter uses raw or effective status.
- Recommendation: default to effective semantics for epics, but expose raw explicitly in JSON output.

Additional CLI gap not in plan but important:
- `lattice next` currently does not exclude epics by type (`src/lattice/core/next.py:56`). If epics are non-actionable, `next` should exclude `type == epic`.

## 5) Board View: Bottom Lane Design
Current board is pure status-column grid (`src/lattice/dashboard/static/index.html:5828`). A bottom epic lane requires structural layout changes, not just filtering.

Required design specifics:
- Split render into two zones:
1. Main status columns (leaf tasks/tickets)
2. Bottom epic lane (persistent)
- Epic lane behavior with many epics:
- Horizontally scrollable cards
- Fixed-height lane with internal scroll, not unbounded page growth
- Sorting by risk first (`needs_human`, `blocked`, then least-progressed)
- Epic cards should be non-draggable.
- Clicking an epic should open detail view, but status controls should be disabled/read-only for epics.

## 6) Cube View Impact
Current Cube encodes status in both color and X-force positioning (`src/lattice/dashboard/static/index.html:4078`, `src/lattice/dashboard/static/index.html:4127`), with no epic-specific geometry.

Needed changes:
- Distinct epic node rendering (shape/halo/size treatment), not only type badge.
- Keep color based on effective status for epics.
- Increase `subtask_of` cohesion so epic neighborhoods cluster visually.

Risk to call out:
- Status-axis forces and hierarchy forces can conflict. If you add clustering, tune force strengths explicitly or provide layout mode toggle.

## 7) Web View Impact
Web already has explicit epic/ticket/task tiering from `type`/topology (`src/lattice/dashboard/static/index.html:4216`, `src/lattice/dashboard/static/index.html:4245`) and epic-centric rendering (`src/lattice/dashboard/static/index.html:4563`, `src/lattice/dashboard/static/index.html:4604`).

Gaps vs plan:
- No explicit epic progress bar/ratio in node card.
- No bottleneck summary in epic detail pane.
- Activity state still keys off raw status `in_progress` (`src/lattice/dashboard/static/index.html:4317`).

Recommendation:
- Inject rollup metrics into Web node payload and detail pane:
- progress ratio
- blocked/needs_human counts
- oldest active descendant age

## 8) Performance and Caching
Current dashboard already polls every 5s and re-fetches full tasks/config payloads (`src/lattice/dashboard/static/index.html:7139`, `src/lattice/dashboard/static/index.html:7179`) with `JSON.stringify` diffing (`src/lattice/dashboard/static/index.html:7182`).

So derived status computation cannot be a per-card recursive traversal in the browser.

Recommendation:
- Compute rollups server-side once per revision and return ready-to-render fields.
- Reuse graph revision strategy (`src/lattice/dashboard/server.py:440`) for memoization of derived rollups.
- Keep derivation as rebuildable read model; do not persist derived status in snapshots as canonical state.

## 9) Risks / What Is Overlooked
Major risks:
1. Semantic split between surfaces if only Board is updated.
2. Hidden urgency if blocked/needs_human precedence is not defined.
3. Existing manual epic statuses becoming contradictory without a clear `raw` vs `effective` contract.
4. Stats distortion if epics are partially transitioned to derived semantics without filtering in analytics.
5. `subtask_of` graph cycles/dangling references causing incorrect rollups or crashes.
6. “Agnostic hierarchy” decision tension: enforce behavior for epics without over-constraining teams that use flatter structures (`Decisions.md:449`).

## 10) Recommended Implementation Ordering
1. Add shared derivation layer and tests.
- Inputs: active snapshots + relationships.
- Outputs: `status_effective`, rollup metrics, warnings.

2. Expose derived fields in API/CLI read paths.
- `/api/tasks`, `/api/tasks/<id>`, `/api/graph`, `lattice list`, `lattice show`.

3. Gate status writes for epics.
- CLI `status_cmd` and dashboard `/api/tasks/<id>/status` reject epic transitions.

4. Update dashboard interaction safety.
- Disable drag/status dropdown for epics in Board/detail views.

5. Implement Board bottom lane.
- Separate rendering container, overflow behavior, epic cards with progress/health.

6. Enhance Cube/Web epic visuals and rollup data usage.

7. Update `lattice next` and stats semantics.
- Exclude epics from actionable selection.
- Decide whether stats include epics in status/time metrics.

8. Ship compatibility docs.
- Raw vs effective status contract.
- “No-subtasks epic” behavior.

## Final Opinionated Calls
- Do not store derived epic status as canonical snapshot state.
- Do not emit synthetic `status_changed` events for rollup transitions.
- Do not ship Board-only derivation; it must be cross-surface from day one.
- Treat blocked/needs_human as higher priority than in-progress when deriving epic status.
