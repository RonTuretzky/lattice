# LAT-103 Plan Review: Epics as Derived-Status Bottom-Lane Containers

**Reviewer:** agent:claude-opus-4-6
**Date:** 2026-02-17
**Status:** Review of design plan, not a code review

---

## Executive Summary

The plan is directionally correct. Epics should not flow through Kanban columns like leaf tasks. The bottom-lane concept and derived status are good ideas. But the plan is underspecified in several critical areas that will cause implementation trouble: the derived status algorithm has unhandled edge cases, the backward compatibility story is missing, the event model implications are unresolved, and the CLI changes are vague. This review details each gap and proposes concrete resolutions.

---

## 1. Derived Status Computation

### Where It Should Live

The derived status computation **must live in `core/`** — specifically as a pure function in `core/tasks.py` (or a new `core/epics.py`). It must not live in the dashboard JavaScript or the CLI layer alone. Three consumers need it:

1. **Dashboard** — for Board bottom lane, Cube, and Web views
2. **CLI** — for `lattice show` and `lattice list` output
3. **Server API** — for `/api/tasks` and `/api/graph` responses

If this logic lives only in the dashboard JS (as the plan's emphasis on "three dashboard surfaces" might imply), the CLI and API will disagree with the dashboard. That is unacceptable in an event-sourced system that prizes ground truth.

**Recommendation:** A function like `compute_epic_status(epic_snapshot, subtask_snapshots) -> dict` in `core/tasks.py` that returns a structure containing:
- `derived_status`: one of the standard statuses (for filtering)
- `progress`: `{"done": N, "total": M, "cancelled": K}`
- `health`: a signal derived from subtask statuses (e.g., "healthy", "at_risk", "blocked")

### The Algorithm

The plan says "If all subtasks are backlog, the epic is effectively backlog. If any are in_progress, the epic is in_progress. If all are done/cancelled, the epic is done." This is an incomplete specification. Here is the full decision table that needs to be defined:

| Subtask statuses present | Derived epic status |
|---|---|
| All `backlog` | `backlog` |
| Any `in_planning` or `planned` (but nothing active) | `planned` |
| Any `in_progress` | `in_progress` |
| Any `review` (and nothing in_progress) | `review` |
| Any `blocked` | `blocked` (or `at_risk`?) |
| Any `needs_human` | `needs_human` (or `at_risk`?) |
| All `done` | `done` |
| All `done` or `cancelled` | `done` |
| All `cancelled` | `cancelled` |
| Mix of done + cancelled + active | `in_progress` |

**Open questions the plan must resolve:**
1. **Blocked vs. at_risk:** If one subtask is `blocked` but others are `in_progress`, is the epic `blocked` or `in_progress`? I argue it should be `in_progress` with a health indicator of "at_risk", not `blocked`. The epic is not blocked; a subtask is.
2. **Priority ordering:** When multiple statuses are present, which wins? The plan needs an explicit precedence order. I propose: `in_progress` > `review` > `blocked` > `needs_human` > `planned` > `in_planning` > `backlog`.
3. **Cancelled subtasks:** Are they excluded from the total count? They should be. An epic with 5 subtasks where 3 are done and 2 are cancelled should show 3/3 (100%), not 3/5 (60%).

### Edge Cases

**Epic with zero subtasks:** The plan does not address this. An epic with no `subtask_of` relationships pointing to it has no subtasks to derive from. Options:
- (a) Show its manually-set status as-is (my recommendation — graceful degradation)
- (b) Show "No subtasks" with a warning indicator
- (c) Treat it as `backlog` always

I strongly recommend (a). This is the safest backward-compatible choice and handles the transition period where epics exist but relationships haven't been wired up yet.

**Deeply nested epics:** An epic whose subtasks are tickets, which themselves have task subtasks. Does the derived status look only at direct children, or does it recurse? The plan is silent. I recommend **direct children only** for v0. Recursive traversal is more correct but expensive and introduces cycle-detection complexity. The direct children of an epic are tickets; if a ticket is done, the epic should count it as done regardless of that ticket's sub-tasks.

**Orphaned subtasks:** What if a subtask's `subtask_of` relationship points to an epic that has been archived? This is already handled by the existing archive system (relationships persist), but the derived status computation needs to only look at *active* subtasks.

---

## 2. Backward Compatibility

This is the biggest gap in the plan. Today:

- Epics have manually-set statuses via `lattice status`
- Events like `status_changed` exist in epic event logs
- Existing code filters by `status` field on snapshots

### Migration Path

I see three options:

**Option A: Dual-mode (recommended).** Keep the `status` field on epic snapshots as-is. Add a `derived_status` field that is computed on read. The `status` field becomes "frozen" at whatever it was last set to. Consumers choose which to display. Over time, the derived status becomes primary and the manual status becomes vestigial.

Pros: Zero migration. No breaking changes. Existing events remain valid.
Cons: Two sources of truth temporarily. Consumers must know to prefer `derived_status`.

**Option B: Compute-on-write.** Whenever a subtask's status changes, recompute the parent epic's derived status and store it in the snapshot. This requires a new event type or updating the epic's snapshot as a side effect of subtask status changes.

Pros: One source of truth. Consumers always read `status`.
Cons: Cross-task side effects violate the current write model (one task per transaction). Crash recovery becomes more complex. Requires new event types.

**Option C: Compute-on-read only.** The `status` field on epic snapshots is ignored by consumers. Derived status is computed fresh every time.

Pros: Clean.
Cons: `lattice list --status in_progress` would need to load all tasks and compute epic derivations before filtering. Breaks existing scripts that read snapshot JSON directly.

**My recommendation is Option A.** It has the lowest blast radius. The dashboard already has all the data it needs (it loads all tasks for the board anyway). The CLI can add a `--derived` flag or just compute it for epics automatically in `lattice show`.

### What Happens to `lattice status <epic> <status>`?

Three options:
1. **Allow it but with a warning** ("Note: this epic's display status is derived from subtasks. Manual status has no effect on the board.")
2. **Reject it for epics** (error: "Cannot manually set status for epics. Status is derived from subtasks.")
3. **Allow it as an override** ("Manual status overrides derived status. Use --derive to revert to automatic.")

I recommend option 1 for v0. Rejecting it (option 2) is a breaking change. Allowing with override (option 3) is overly complex. A warning lets users discover the new behavior without breaking their workflows.

---

## 3. Event Model Impact

### Should `status_changed` events still be recorded for epics?

**Yes, if someone explicitly runs `lattice status` on an epic.** The event model records what happened. If a user forces a status change on an epic, that is a real event that should be preserved. The derived status computation can coexist with manual status events.

What should NOT happen: automatic `status_changed` events on the epic when a subtask's status changes. That would be a side effect crossing task boundaries, and it violates the current write model's single-task-per-transaction guarantee.

### What about the lifecycle log?

No change needed. `_lifecycle.jsonl` records `task_created`, `task_archived`, `task_unarchived`. Epic status derivation is a read-side concern, not a write-side concern.

### New event types?

Not needed for v0. Derived status is computed at read time from existing data. If Option B (compute-on-write) is chosen later, a new `epic_status_derived` event type could be introduced, but that is premature now.

---

## 4. CLI Impact

### `lattice list`

Currently `lattice list --status in_progress` checks `snap.get("status")` directly (line 354 of `query_cmds.py`). For epics, this would not match if the epic's stored status is `backlog` but its derived status is `in_progress`.

**Two approaches:**
1. **Compute derived status during list filtering.** This requires loading all tasks (for subtask resolution) even when listing a single status. At v0 scale this is fine.
2. **Exclude epics from status filtering unless `--type epic` is specified.** Simpler but less useful.

I recommend approach 1. The `list_cmd` already loads all snapshots. Adding a post-pass to compute derived status for epics before filtering is straightforward.

### `lattice show`

For epics, `lattice show` should display:
- The derived status with a progress bar (e.g., "Status: in_progress (derived: 4/7 subtasks done)")
- The list of subtasks with their statuses
- Health indicators if any subtasks are blocked/needs_human

This requires `show_cmd` to detect `type == "epic"` and load subtask snapshots. The current `_find_incoming_relationships` already scans all snapshots (line 709), so the infrastructure for this exists.

### `lattice next`

Epics should be excluded from `lattice next` results. The `select_next` function picks the highest-priority actionable task. Epics are not actionable — they are containers. Currently there is no type filter in `select_next` (in `core/next.py`). Adding `if snap.get("type") == "epic": continue` is trivial but important.

---

## 5. Dashboard Board View — Bottom Lane

### Rendering

The current `renderBoard()` function (line 5515) creates a grid of columns, one per status. The bottom lane requires a fundamentally different layout: the status columns above, then a horizontal divider, then the epic lane below.

**Concrete approach:**
1. Filter epics out of the `tasks` array before grouping by status
2. After rendering the status columns, append a new `<div class="board-epic-lane">` below the grid
3. Each epic card in the lane shows: title, short_id, progress bar, subtask count, health indicator

### Progress Bar

A horizontal bar showing done/total, colored segments by subtask status. CSS-only implementation (no library needed):

```
[||||||||    ] 6/9
 green  grey
```

Green = done, orange = in_progress, red = blocked, grey = remaining.

### Scrolling and Layout

With many epics, the lane should be horizontally scrollable. Each epic card is a fixed-width element. The lane has a fixed height (roughly 2 card heights) with `overflow-x: auto`.

### Click Behavior

Clicking an epic in the bottom lane should open the same `openDetailPanel()` that regular cards use. The detail panel for epics should show the subtask breakdown.

### Drag and Drop

Epics in the bottom lane are NOT draggable (no status transitions). This is a key difference from regular cards. The `draggable="true"` attribute should be omitted for epic cards.

---

## 6. Dashboard Cube View

### Current State

The Cube view (line 3657, `renderCube()`) uses `force-graph` with status-constrained X-axis positioning. Nodes are colored by status and sized by priority. Relationship types are edge-colored.

### Epic Nodes

Epic nodes should be visually distinct:
- **Larger size** (already partially handled — `CUBE_PRIORITY_SIZE` could be overridden by type)
- **Different shape or border** — a double ring, a diamond, or a hexagonal shape to distinguish from leaf tasks. The canvas-based rendering in `nodeCanvasObject` supports custom shapes.
- **Status-independent positioning** — if epic status is derived, the X-axis position should be based on the derived status, not the stored status. This means the Cube view needs the same derived status computation as the board.

### Subtask Clustering

The plan mentions "subtask clustering visible." This is vague. Two options:

1. **Visual grouping via force:** Apply a strong attractive force between epics and their subtasks (via the `subtask_of` links). The `d3.forceLink` distance for `subtask_of` edges could be shorter than other relationship types. This naturally clusters subtasks around their epic.

2. **Explicit bounding box:** Draw a translucent hull around each epic and its subtasks. More explicit but expensive to compute and render.

I recommend option 1 for v0. The link distance for `subtask_of` is already handled in the Cube view (line 3646, `CUBE_EDGE_COLORS` includes `subtask_of`), so tightening the distance would create natural clustering.

### Scattered Subtasks

The plan asks about "epics with subtasks scattered across different status clusters." This is inherent in the status-constrained X layout. An epic's subtasks will be spread across multiple X positions if they are in different statuses. This is correct — it visually communicates that the epic spans multiple stages. The epic node itself should be positioned at the centroid of its subtasks (or at its derived status position).

---

## 7. Dashboard Web View

### Current State

The Web view (line 3901, `buildWebHierarchy()`) already treats epics as hubs and uses the three-tier hierarchy. It:
- Detects epic/ticket/task tiers from type or topology (line 3928-3947)
- Renders epics as larger nodes (`WEB_TIER_RADIUS.epic = 20`)
- Uses hub-and-spoke layout with `subtask_of` links

### What Changes

The Web view is already closest to the desired epic visualization. Changes needed:
1. **Progress indicator on epic hub nodes:** The canvas rendering should show a ring or arc around epic nodes indicating progress (like a circular progress bar).
2. **Derived status coloring:** Epic nodes should be colored by their derived status, not their stored status. Currently `getLaneColor(node.status)` is used.
3. **Bottleneck visibility:** If any spoke (ticket) has a blocked subtask, the spoke should be colored red/orange to indicate a bottleneck.

### Interaction with Existing Design

The Web view's `buildWebHierarchy()` already builds `parentMap` and `childrenMap` from `subtask_of` links. The derived status computation is a natural extension: iterate over `childrenMap[epicId]` to compute progress.

The Web view is the natural home for epic-level detail. Clicking an epic hub should show a sidebar with the full subtask breakdown, timeline, and bottleneck analysis. This is consistent with the plan's "Web — epic detail with full timeline, subtask breakdown, bottleneck visibility."

---

## 8. Performance

### The Core Concern

Derived status requires traversing `subtask_of` relationships for every epic on every render/query. This means:

1. **Loading all tasks** — cannot compute epic status without loading subtask snapshots
2. **Building a parent-child index** — scanning all `relationships_out` for `subtask_of` entries
3. **Computing status for each epic** — iterating its children

### At v0 Scale

This is a non-issue. The dashboard already loads all tasks on every refresh. The `/api/graph` endpoint already builds a full relationship index. The CLI `lattice list` already loads all snapshots. Adding a derived status pass over 10-50 epics with 5-20 subtasks each is negligible.

### At Future Scale (1000+ tasks)

The computation becomes O(N) where N is total tasks (to build the index) plus O(E*C) where E is epic count and C is average children per epic. With 1000 tasks and 50 epics averaging 20 children, this is ~2000 operations — still negligible.

### Should Derived Status Be Cached in the Snapshot?

**Not in v0.** Caching introduces a consistency problem: the cached value goes stale whenever a subtask changes status, and there is no mechanism to invalidate it without cross-task side effects. Compute-on-read is correct and fast enough.

**In v1+**, if performance becomes measurable, a `derived_status` field in the snapshot could be updated by a post-event hook (when any `status_changed` event fires, check if the affected task has a `subtask_of` relationship and recompute the parent's derived status). But this is premature optimization.

---

## 9. Risks and Concerns

### Risk 1: Orphaned Epics (High Impact, Medium Probability)

Epics created before the three-tier hierarchy existed may have no `subtask_of` relationships pointing to them. They would appear in the bottom lane with 0/0 progress. This looks broken.

**Mitigation:** For epics with zero subtasks, fall back to the manually-set status. Display a subtle indicator ("No subtasks linked") to prompt the user to wire up relationships.

### Risk 2: The "Epics Don't Move" Principle Breaks CLI Workflows (Medium Impact, High Probability)

If `lattice status <epic> in_progress` starts printing warnings or errors, agents with hardcoded workflows will break. The CLAUDE.md template tells agents to update status before work. If an agent tries to update an epic's status and gets rejected, it may thrash.

**Mitigation:** Keep `lattice status` working for epics in v0. Add the warning but do not error. Update the CLAUDE.md template to teach agents that epic status is derived. Add a `--type` filter to `lattice next` to skip epics.

### Risk 3: Dashboard Monolith Complexity (Medium Impact, High Probability)

`index.html` is already a large monolithic file. Adding bottom-lane rendering, epic progress computation in JS, and modifications to Cube/Web views will increase its size significantly. There is a real risk of introducing bugs in the board view's drag-and-drop logic when adding the epic lane.

**Mitigation:** Implement the epic lane as a cleanly separated function (`renderEpicLane()`) that runs after `renderBoard()`. Keep epic filtering out of the main column rendering loop to minimize interaction with existing drag/drop code.

### Risk 4: Inconsistency Between Stored and Derived Status (High Impact, Medium Probability)

If the board shows "in_progress" (derived) but `lattice show` displays "backlog" (stored), users will be confused. All surfaces must agree on which status to display.

**Mitigation:** The `compact_snapshot()` function in `core/tasks.py` (used by `lattice list --compact` and the API) should be the single place where derived status is injected. If the snapshot is for an epic, compute and inject the derived status there.

### Risk 5: Relationship Data Quality (Medium Impact, High Probability)

Derived status is only as good as the `subtask_of` relationships. If a ticket is a subtask of an epic but the relationship was never created, the epic's progress will be wrong. There is no validation that forces subtask relationships to be created.

**Mitigation:** This is an inherent limitation of a convention-based hierarchy. Document it clearly. Consider a `lattice doctor` check that flags epics with no subtasks and tasks/tickets with no parent.

---

## 10. Implementation Ordering

The following sequence minimizes risk and allows incremental validation:

### Phase 1: Core Logic (No UI Changes)
1. **Add `compute_epic_derived_status()` in `core/tasks.py`** — pure function, takes epic snapshot + list of subtask snapshots, returns derived status + progress dict
2. **Add tests** — unit tests for all edge cases (zero subtasks, mixed statuses, all done, all cancelled, etc.)
3. **Wire into `compact_snapshot()`** — when the task is type "epic", compute and include derived status

### Phase 2: CLI Changes
4. **Update `lattice show` for epics** — display derived status, progress bar, subtask list
5. **Update `lattice list` filtering** — use derived status for epics when filtering by `--status`
6. **Add warning to `lattice status` for epics** — print advisory message that status is derived
7. **Exclude epics from `lattice next`** — add type filter to `select_next()`

### Phase 3: Dashboard Board Bottom Lane
8. **Filter epics out of board columns** — in `renderBoard()`, separate epics before grouping
9. **Render bottom lane** — new `renderEpicLane()` function with progress bars
10. **Wire click handlers** — clicking an epic card opens the detail panel
11. **Omit drag-and-drop for epic cards** — epics are not draggable

### Phase 4: Dashboard Cube and Web Enhancements
12. **Cube: epic node styling** — larger size, distinct visual treatment, derived status for X position
13. **Web: progress indicators on epic hubs** — circular progress arc around hub nodes
14. **Web: bottleneck coloring** — red/orange spokes for blocked subtask chains

### Phase 5: API and Server
15. **Update `/api/tasks` response** — include derived status for epics
16. **Update `/api/graph` response** — include derived status and progress in epic nodes

---

## 11. What the Plan Gets Right

- **The core insight is correct.** Epics are containers, not workflow items. "Epics reflect — they don't move" is the right mental model.
- **Bottom lane is the right UI pattern.** It avoids cluttering Kanban columns with non-actionable items.
- **Derived status from subtask completion is the right approach.** Manual status management for epics is busywork that agents and humans both skip.
- **Three-surface approach (Board, Cube, Web) is thorough.** Each surface serves a different question, and the plan identifies the right question for each.

---

## 12. What the Plan Gets Wrong or Misses

1. **No backward compatibility story.** This is the biggest gap. Existing epics with manual statuses need a migration path.
2. **No algorithm specification.** "If any are in_progress, the epic is in_progress" is one rule, but a full precedence table with edge cases is needed.
3. **No answer on where the logic lives.** The plan focuses on dashboard surfaces but the core computation needs to be in Python, not JavaScript.
4. **No answer on CLI behavior changes.** Will `lattice status` error? Warn? Silently work?
5. **No health indicator definition.** The plan mentions "health indicators" without defining what health means or how it is computed.
6. **No `lattice next` consideration.** Epics should be excluded from the next-task selection algorithm.
7. **The Cube section is vague.** "Epic nodes rendered distinctly" needs concrete visual specifications.
8. **No `lattice doctor` integration.** The doctor command should validate epic-subtask relationship integrity.

---

## 13. Recommended Next Steps

1. Resolve the algorithm and edge cases (Section 1) into a concrete specification
2. Choose a backward compatibility strategy (Section 2 — I recommend Option A)
3. Implement Phase 1 (core logic + tests) as the first deliverable
4. Use the working core logic to validate the design before touching the dashboard
5. Break the remaining phases into separate LAT tickets under LAT-103
