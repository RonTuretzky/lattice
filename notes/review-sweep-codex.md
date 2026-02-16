# Code Review: needs_human + lattice next

## Summary
This sweep makes solid progress on workflow modernization and agent ergonomics: status naming is aligned, `needs_human` is integrated across CLI/weather/template surfaces, and `lattice next` introduces a clean pure-core selector with substantial test coverage.

The main blocker is correctness in `--claim`: the new write path can create transitions that violate the configured workflow rules. There are also important consistency gaps around claim concurrency semantics and dashboard status-color mapping after the status rename.

## Findings

### Critical (must fix)
- `lattice next --claim` bypasses transition validation and can emit invalid `status_changed` events.
  - `src/lattice/cli/query_cmds.py:350` to `src/lattice/cli/query_cmds.py:358` unconditionally writes `to: "in_progress"` whenever current status is not already `in_progress`.
  - `src/lattice/core/config.py:99` to `src/lattice/core/config.py:102` does **not** allow `in_planning -> in_progress`.
  - The normal status path enforces this (`src/lattice/cli/task_cmds.py:510`), but `next --claim` bypasses that guard.
  - Repro (verified): create task, move to `in_planning`, run `lattice next --actor agent:claude --status in_planning --claim` => task is moved to `in_progress`.

### Important (should fix)
- `--claim` is not atomic at selection time and can race into reassignment/steal behavior.
  - Selection happens before any lock (`src/lattice/cli/query_cmds.py:315` to `src/lattice/cli/query_cmds.py:319`), then mutation happens later (`src/lattice/cli/query_cmds.py:336` onward).
  - If state changes between these phases, current logic can force reassignment (`src/lattice/cli/query_cmds.py:339` to `src/lattice/cli/query_cmds.py:347`) and still push status to `in_progress`.
  - This is especially risky under concurrent agents both running `next --claim`.

- Dashboard lane color mapping is still keyed to legacy statuses, so renamed/new statuses degrade to fallback gray in rendered lanes.
  - Theme maps still use `in_implementation` / `implemented` / `in_review` (`src/lattice/dashboard/static/index.html:2816` to `src/lattice/dashboard/static/index.html:2957`).
  - Rendering uses `getLaneColor(status)` and falls back to `#6c757d` for unknown keys (`src/lattice/dashboard/static/index.html:3738` to `src/lattice/dashboard/static/index.html:3742`).
  - CSS class additions alone (`src/lattice/dashboard/static/index.html:489` to `src/lattice/dashboard/static/index.html:504`) do not fully solve this because board headers are styled inline from `getLaneColor`.

### Minor (nice to have)
- Weather command imports private `core.next` internals (`src/lattice/cli/weather_cmds.py:160`), coupling to `_sort_key` / `_EXCLUDED_STATUSES` implementation details.
- `next --status` accepts arbitrary strings silently (`src/lattice/cli/query_cmds.py:312` to `src/lattice/cli/query_cmds.py:313`), which is less strict than `lattice status` validation behavior.

### Positive
- `core/next.py` cleanly respects layer boundaries (pure logic, no filesystem I/O).
- Resume-first and priority/urgency ordering logic is explicit and readable.
- Test additions are broad and meaningful for baseline behavior (`tests/test_core/test_next.py`, `tests/test_cli/test_next_cmd.py`).
- `needs_human` surfaced in list/weather output improves human triage visibility.

## Test Coverage Assessment
The 46 new tests provide good breadth for selection ordering, assignment filtering, resume behavior, output modes, and basic claim behavior. This is a strong baseline.

Key gaps remain:
- No test that `--claim` respects transition rules when the selected task is `in_planning` (or when `--status` includes states not valid to jump from).
- No race-oriented test for two claimers contending on the same candidate (or stale selection before write).
- No dashboard test guarding lane-color mapping against current canonical statuses (`in_progress`, `review`, `blocked`, `needs_human`).

## Verdict
Needs rework
