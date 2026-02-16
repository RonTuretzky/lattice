# Code Review: needs_human + lattice next (Claude)

## Summary

These five commits add two meaningful features (`needs_human` status and `lattice next` command), fix a longstanding config/test drift problem with status names, and update documentation. The overall quality is high -- the `core/next.py` module cleanly respects the layer boundary (pure logic, no I/O), the test suite is thorough with 46 well-structured tests, and the `needs_human` integration is consistent across all touchpoints (config, weather, dashboard CSS, list markers, CLAUDE.md template). The code follows established codebase conventions for JSON output, error handling, and Click option patterns.

There is one critical finding: `--claim` bypasses workflow transition validation, allowing illegal state transitions (e.g., `backlog` directly to `in_progress`). There is also a TOCTOU race in the `--claim` path, though this is acceptable at v0 scale. Beyond these, the changes are clean and well-reasoned.

## Findings

### Critical (must fix)

1. **`--claim` bypasses transition validation** (`query_cmds.py:350-360`)

   The `--claim` flag moves a task directly to `in_progress` without checking `validate_transition()`. The default ready pool includes `backlog`, but `backlog` -> `in_progress` is NOT a valid transition in the workflow config:

   ```python
   "backlog": ["in_planning", "planned", "cancelled"],
   ```

   This means `lattice next --actor agent:x --claim` on a backlog task will create a `status_changed` event with an illegal transition (`backlog` -> `in_progress`), silently violating the workflow invariant that the `status` command enforces.

   **Fix options:**
   - (A) Validate the transition and error if invalid (safest, but defeats the purpose of one-command claim for backlog tasks).
   - (B) Change the default `ready_statuses` to only `{"planned"}` so `--claim` only picks tasks that can legally transition to `in_progress`. Backlog tasks would require explicit `--status backlog` to appear, and `--claim` on them would still need validation.
   - (C) Make `--claim` emit intermediate transitions automatically (backlog -> planned -> in_progress), each as a separate event. This preserves the workflow graph and keeps `--claim` ergonomic.
   - (D) Document that `--claim` is a force-transition (like `--force` on `lattice status`) and add the `force: true` flag to the event data.

   Recommendation: Option (C) is most aligned with the system's philosophy -- events are authoritative history, and skipping intermediate states corrupts that history. Option (B) is the simplest safe fix.

### Important (should fix)

2. **TOCTOU race in `--claim`** (`query_cmds.py:316-363`)

   The `--claim` path does: (1) `load_all_snapshots` (unlocked read), (2) `select_next` (pure logic), (3) `read_snapshot_or_exit` (unlocked re-read), (4) `write_task_event` (locked write). Between steps 1-3 and step 4, another process could claim the same task. The lock in step 4 protects write integrity but not the selection decision.

   At v0 scale (single agent, local filesystem) this is unlikely to cause problems. But the Decisions.md entry explicitly mentions enabling "the sweep pattern -- an autonomous loop that claims, works, transitions, and repeats," which implies multiple agents running concurrently. Two agents running `lattice next --claim` simultaneously could both select the same task, and the second write would silently overwrite the first agent's claim.

   **Fix:** Read-then-write should happen under the same lock. Move `read_snapshot_or_exit` inside the lock scope of `write_task_event`, or add a check-and-set pattern: re-read the snapshot inside the lock and verify the task is still in the expected state before writing.

3. **Weather `_find_up_next` imports private names from `core/next`** (`weather_cmds.py:160`)

   ```python
   from lattice.core.next import _EXCLUDED_STATUSES, _sort_key
   ```

   Importing underscore-prefixed names creates a coupling to internal implementation details. If `_sort_key` or `_EXCLUDED_STATUSES` change, `weather_cmds.py` breaks silently.

   **Fix:** Either promote these to public API (`EXCLUDED_STATUSES`, `sort_key`) since they have legitimate external consumers, or add a `select_all_ready()` function to `core/next.py` that returns the sorted candidate list (instead of just the top one). The weather command needs the full list, not just the top pick.

4. **`needs_human` is not reachable from `backlog`** (`config.py:98`)

   Looking at the transitions:
   ```python
   "backlog": ["in_planning", "planned", "cancelled"],
   ```

   A task in `backlog` cannot move to `needs_human`. This is noted in the Decisions.md entry ("NOT reachable from backlog -- work hasn't started"), but it creates an awkward edge case: what if an agent is triaging backlog and realizes a task needs human input before it can even be planned? The agent would need to move it to `in_planning` first, then to `needs_human`. This is minor -- the two-step path exists -- but worth noting for agent-facing documentation.

### Minor (nice to have)

5. **Redundant status check in `select_next` step 2** (`core/next.py:58`)

   ```python
   if status in _EXCLUDED_STATUSES:
       continue
   ```

   This check is dead code when using the default `ready_statuses = {"backlog", "planned"}`, because none of the excluded statuses (`needs_human`, `blocked`, `done`, `cancelled`) overlap with the defaults. The check only matters if a caller passes a custom `ready_statuses` that includes excluded statuses. This is defensive programming, which is fine, but a comment explaining the purpose would clarify intent.

6. **`json_envelope` skips `data` when `None`, requiring manual JSON in `next_cmd`** (`query_cmds.py:323-324`)

   When no task is found, `next_cmd` builds JSON manually:
   ```python
   click.echo(json.dumps({"ok": True, "data": None}, sort_keys=True, indent=2) + "\n")
   ```

   This bypasses the `json_envelope` helper because that helper omits the `data` key entirely when `data is None`. The manual construction is correct but inconsistent with how other commands produce JSON. Consider adding a `include_null_data=True` parameter to `json_envelope`, or accepting the inconsistency as intentional for this one case.

7. **No `--claim` test for `planned` status** (`test_next_cmd.py`)

   The `test_claim_assigns_and_starts` test claims a task in `backlog` status (the default). There is no test claiming a task in `planned` status. Given the transition validation bug (finding #1), the test ironically passes because the code doesn't validate transitions at all. Once the bug is fixed, tests should cover both valid transitions (`planned` -> `in_progress`) and the now-illegal ones.

8. **No test for `--claim` on a resumed task** (`test_next_cmd.py`)

   If an actor has an `in_progress` task (resume-first logic fires), and they pass `--claim`, what happens? The task is already `in_progress` and already assigned -- so `--claim` should be a no-op. This edge case is not tested.

9. **Decisions.md entry for `needs_human` says "NOT reachable from backlog or done/cancelled"** (`Decisions.md:502`)

   This is accurate for the current config, but the entry doesn't mention that `needs_human` is also not reachable from `blocked`. Looking at the transitions: `"blocked": ["in_planning", "planned", "in_progress", "cancelled"]`. A blocked task cannot move to `needs_human` -- it must first move back to an active state. This seems intentional (blocked and needs_human are different waiting states), but the Decisions.md omits the `blocked` -> `needs_human` non-transition.

10. **ASCII diagram in CLAUDE.md template is slightly misleading** (`claude_md_block.py:32-35`)

    ```
    backlog -> in_planning -> planned -> in_progress -> review -> done
                                                ↕            ↕
                                             blocked      needs_human
    ```

    The `↕` arrows under `in_progress` and `review` are spatially ambiguous -- they could be read as "only these two states connect to blocked/needs_human." In reality, `needs_human` is reachable from `in_planning`, `planned`, `in_progress`, and `review` (four states, not two). A more accurate diagram would show the full connectivity, but brevity is valuable in a CLAUDE.md template. Consider a footnote: "See `config.json` for full transition graph."

### Positive

- **Clean layer separation in `core/next.py`.** The selection logic is pure -- no filesystem I/O, no Click dependencies, no side effects. Fully testable with plain dicts. This is exactly what the architecture docs prescribe.

- **Resume-first algorithm is well-designed.** The idea that an agent should finish what it started before picking up new work is sound coordination behavior. The priority sort within resume candidates (picking the highest-priority in-progress task when an agent has multiple) is a thoughtful detail.

- **Comprehensive unit tests.** The 27 unit tests in `test_next.py` cover empty input, all four priority levels, urgency as tiebreaker, ID as final tiebreaker, all excluded statuses, assignment filtering (self, others, unassigned, no-actor), resume logic (in_progress, in_planning, other agent's work, no-actor, priority within resume), custom ready_statuses, and planned tasks. The class-based grouping makes the test intentions clear.

- **CLI tests exercise real integration paths.** The 19 CLI tests invoke full Click commands through the runner with a real `.lattice/` directory. They test JSON/quiet/human output modes, priority ordering, status exclusions, assignment filtering, resume-first, status override, claim with assignment, and validation errors. This catches wiring bugs that unit tests miss.

- **`needs_human` integration is thorough.** The new status appears in: config transitions, `_EXCLUDED_STATUSES` in `core/next.py`, weather attention items, weather text/markdown output, list command's `>>>` prefix marker, dashboard CSS (amber/orange styling), and the CLAUDE.md template with dedicated "When You're Stuck" section. No touchpoint was missed.

- **The `_sort_key` function handles unknown values gracefully** (returns `99` for unrecognized priority/urgency), so tasks with non-standard or missing fields don't crash the sort -- they just sort to the bottom.

- **Decisions.md entries are well-structured** with clear decision, rationale, and consequence sections. The `needs_human` and `lattice next` entries accurately describe the implementation.

## Test Coverage Assessment

The 46 new tests (27 unit + 19 CLI integration) provide strong coverage of the `select_next` algorithm and the `next` command's basic paths. The test suite is well above typical coverage for a new feature.

**What's covered well:**
- All sorting dimensions (priority, urgency, ID tiebreaker)
- All exclusion categories (done, cancelled, blocked, needs_human)
- Assignment semantics (self, others, unassigned, no-actor)
- Resume-first logic (in_progress, in_planning, priority within resume)
- Custom ready_statuses override
- All output modes (human, JSON, quiet)
- `--claim` happy path, no-task case, validation errors

**What's missing:**
- `--claim` on a `planned` (vs. default `backlog`) task -- important once transition validation is added
- `--claim` when resume-first fires (task already in_progress)
- `--claim` concurrent access (two agents claiming simultaneously) -- hard to test deterministically but worth a targeted test
- `needs_human` tasks in mixed pools (a needs_human task among backlog tasks, verifying it's skipped)
- `--status` with multiple comma-separated values (e.g., `--status backlog,planned,review`)
- `--claim` with provenance flags (`--triggered-by`, `--on-behalf-of`, `--reason`) -- the next command doesn't accept these but the claim writes events that could carry provenance
- No negative test: passing `--claim` without `--actor` in JSON mode (only the non-JSON error path is tested)
- Weather `_find_up_next` is indirectly tested via the weather command but has no dedicated unit test for its interaction with `core/next` internals

## Verdict

**Ship with fixes.** The transition validation bypass in `--claim` (finding #1) is a real bug that violates the workflow invariant the rest of the system enforces. Fix that, add a test for claiming a `planned` task (the only default-ready-status with a legal `in_progress` transition), and promote or encapsulate the private imports in weather_cmds. Everything else is solid work.
