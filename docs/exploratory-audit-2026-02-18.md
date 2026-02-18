# Lattice Exploratory Audit — Validated

Date: 2026-02-18 18:10 EST (original), validated 2026-02-18 (second pass)
Scope: `src/`, `tests/`, `scripts/`, `docs/`, site/package shape
Checks run:
- `uv run mypy src` -> **412 errors across 33 files**
- `uv run ruff check src tests` -> **pass**
- `uv run pytest` -> **1 failed, 1535 passed** (`tests/test_dashboard/test_server.py:510`)

Validation method: Five parallel research agents traced every line-number claim back to the source code. Items marked CONFIRMED were verified against the actual codebase. Items that were false, overstated, or aspirational with no concrete finding were removed.

---

## Validated Actions

### Tier 1 — Real Bugs and Contract Violations

1. **[CHANGE] Unify completion-policy enforcement across CLI and MCP.**
   MCP status writes (`src/lattice/mcp/tools.py:359`) share `validate_status()` and `validate_transition()` with the CLI — but **skip `validate_completion_policy()`** entirely. The CLI enforces evidence-gating at `src/lattice/cli/task_cmds.py:566`; MCP does not. This means an MCP caller can transition to `done` without satisfying evidence requirements. The drift is narrow (completion policy only) but real.

2. **[EDIT] Fix dashboard bind-error contract mismatch.**
   Test expects `BIND_ERROR` but runtime emits `PORT_IN_USE` for `errno.EADDRINUSE` (`src/lattice/cli/dashboard_cmd.py:97`). Test at `tests/test_dashboard/test_server.py:510` asserts the wrong code. Quick fix — align the test or the error code.

3. **[ADD] Add CLI/MCP parity tests for completion policy.**
   The drift in item 1 should be enforced by contract tests. Without them, the gap will reopen even if fixed today.

### Tier 2 — Structural Issues (Dashboard)

The dashboard server (`src/lattice/dashboard/server.py`, 2215 LOC) is the largest coupling hotspot. All claims confirmed:

4. **[CHANGE] Extract task mutation logic out of HTTP handlers.**
   Status changes (line 819), task updates (line 1328), and reactions (line 1710) all embed event creation, snapshot application, and `write_task_event()` calls directly inside handler methods. Should flow through a shared domain service.

5. **[CHANGE] Move archive transaction flow out of HTTP layer.**
   `_handle_post_task_archive` (line 1467) implements its own lock/event/write/move sequence inline — unlike other handlers that delegate to `write_task_event()`. Mixes lock lifecycle, event creation, file moves (`shutil.move`), and hook execution in one handler.

6. **[REMOVE] Remove OS shell-launch side effects from dashboard API.**
   `_handle_post_open_notes` (line 1906) and `_handle_post_open_plans` (line 1949) directly call `subprocess.Popen(["open", ...])` from inside HTTP handlers. Move launch behavior to client-side or CLI.

7. **[CHANGE] Centralize config loading for dashboard writes.**
   `config.json` is read from disk independently in at least 5 handlers (lines 263, 1484, 1751, 1846, and others). No central config cache or loader.

8. **[CHANGE] Move activity aggregation/filtering into shared core module.**
   `_collect_events()` (line 2005), `_build_facets()` (line 2040), and `_apply_activity_filters()` (line 2078) are server-module-only utilities with no abstraction to core/ or storage/ layers. Grep confirmed no definitions exist outside server.py.

### Tier 3 — Structural Issues (CLI)

9. **[CHANGE] Refactor `resource acquire` into a dedicated resource service.**
    One ~200-line handler (`src/lattice/cli/resource_cmds.py:170`) owns locking, stale eviction, force eviction, exponential backoff with timeout, and write semantics. All responsibilities in one function.

10. **[CHANGE] Move archive/unarchive file orchestration into storage/core API.**
    `_archive_one` (line 80) and `_unarchive_one` (line 416) in `src/lattice/cli/archive_cmds.py` call `shutil.move()`, `atomic_write()`, and `jsonl_append()` directly under `multi_lock()`. No storage-layer abstraction.

### Tier 4 — Module Size

11. **[INFO] Large module inventory (confirmed line counts).**
    These are real and worth tracking, but are consequences of the structural issues above, not independent problems:
    - `src/lattice/dashboard/server.py` — 2215 LOC
    - `src/lattice/mcp/tools.py` — 1338 LOC
    - `src/lattice/cli/query_cmds.py` — 1319 LOC
    - `src/lattice/cli/main.py` — 1176 LOC
    - `src/lattice/cli/task_cmds.py` — 1148 LOC
    - `src/lattice/cli/demo_cmd.py` — 1479 LOC

### Tier 5 — Surface Area Trimming

12. **[REMOVE] Move weather command behind optional plugin boundary.**
    `src/lattice/cli/weather_cmds.py` (449 lines) is wired in at `src/lattice/cli/main.py:1163`. Not core to the task-tracking primitive.

13. **[REMOVE] Move demo scaffolding behind optional plugin boundary.**
    `src/lattice/cli/demo_cmd.py` (1479 lines) is wired in at `src/lattice/cli/main.py:1165`. Significant code surface for a demo/onboarding feature.

14. **[EDIT] Replace default Astro starter README.**
    `site/README.md` still contains unmodified Astro "Starter Kit: Minimal" boilerplate with "Delete this file. Have fun!" Trivial cleanup.

15. **[INFO] Playful scripts in `scripts/`.**
    `dead_letters.py`, `fizzbuzz.py`, `status_haikus.py`, `lattice_art.py` all exist. Non-essential but they live in `scripts/`, not in core — low harm. Consider whether they belong in the repo long-term.

### Tier 6 — Minor Confirmed Issues

16. **[CHANGE] Deduplicate hook execution for task/resource events.**
    `execute_hooks()` (line 14) and `execute_resource_hooks()` (line 134) in `src/lattice/storage/hooks.py` are structurally similar. The resource version omits transition handling. Reasonable given different event domains, but worth consolidating if hooks grow.

17. **[CHANGE] `init` bundles multiple concerns.**
    The `init` command at `src/lattice/cli/main.py:585` handles infrastructure setup, agent-doc updates, CLAUDE.md updates, and dashboard auto-start in one function. This is intentional UX (onboarding should be holistic), but makes the init path harder to test or compose. Not a blocker — more of a note for when init gets more complex.

---

## Removed Items (Not Validated)

The following items from the original audit were removed after investigation:

| Original # | Claim | Why Removed |
|-------------|-------|-------------|
| 6 | `next --claim` duplicates low-level persistence | **Necessary for correctness.** Manual lock/read/mutate/write avoids deadlocks — `write_task_event()` acquires its own locks internally. Not a defect. |
| 13 | Duplicate snapshot listing/filter across MCP and CLI | **Not duplication.** MCP has basic listing (~25 lines, no filtering). CLI has advanced filtering (5 filters, AND logic). Different feature levels, not parallel implementations. |
| 14 | Parallel task detail assembly in MCP and CLI | **Not duplication.** MCP detail is 25 lines (snapshot + events). CLI detail is 135+ lines with transitions, relationships, artifacts, branch links, commits. Intentionally different depth. |
| 16 | Evidence-role extraction helpers re-loop similarly | **Intentional backward compatibility.** Three functions handle new `evidence_refs` field with fallback to legacy `artifact_refs` / `comment_role_refs`. This is a migration bridge, not redundant logic. |
| 17 | Comment map rebuild happens repeatedly | **Once per call, not repeated.** `_build_comments_map()` is called once per validation function. No tight-loop rebuilding. Negligible overhead. |
| 18 | Epic status derivation rebuilds graph links per call | **False.** Graph links are built once and traversed recursively. No per-call rebuilding occurs. |
| 19 | Staleness checks repeatedly parse timestamps | **Mostly false.** Staleness checks use string comparisons. Timestamp parsing only occurs in display-formatting functions, called on demand. |
| 22 | Plugin loading should catch `BaseException` | **Edge case.** `SystemExit` killing startup during plugin load is theoretically possible but not a practical concern for v0. |
| 23 | Static import block is brittle | **Not brittle.** Uses underscore-prefixed aliases with explicit `# noqa: F401`. This is standard Click pattern — imports register commands via decorators as side effects. |
| 24 | Plugin load timing reduces composability | **Standard pattern.** Loading plugins after built-in command registration is the expected approach for Click apps. |
| 25 | `init` side effects should be optional | Merged into item 17 above with accurate framing. |
| 28 | Agent assets ship with runtime | **Partially true but not a v0 concern.** Templates ship via `claude_md_block.py`; skills directory is a stub. Separating into an optional package is premature. |
| 29, 30, 37, 38, 40 | Aspirational recommendations (guardrails, CI checks, API versioning, minimal-core mode, boundary map) | **No concrete findings.** These are architecture ideals with nothing broken behind them. Good ideas for a future roadmap doc, not audit findings. |
| 31 | Dashboard fixtures use handcrafted JSON | **Partially true.** Event records use canonical `create_event()`. Some artifact metadata uses raw JSON. Mixed, not systematic. |
| 32, 33 | Missing recursion stress tests, archive parity tests | **Reasonable suggestions but not findings.** No existing bug or drift was demonstrated. Nice-to-haves for test coverage expansion. |
| 34 | Stale docs in `archive/` | **Working as designed.** CLAUDE.md explicitly documents `archive/` as "off-limits, historical record only." Versioned docs there are intentional. |
| 11 (original) | 412 mypy failures as "Blocker" | **Valid observation, wrong severity.** The project works fine without mypy gating. This belongs in a separate type-safety initiative, not an audit blocker. Mypy adoption is a strategic choice, not a bug. |

---

## Suggested Execution Order

1. **Quick wins:** Items 2 (bind-error fix), 14 (Astro README).
2. **Close the policy gap:** Items 1 (completion policy in MCP), 3 (parity tests).
3. **Extract shared mutation service:** Items 4, 5, 8, 10 — the dashboard and CLI archive paths converge on a single task-write-transaction abstraction.
4. **Dashboard decomposition:** Items 6, 7, 8 — remove side effects and repeated loading from HTTP handlers.
5. **Resource service extraction:** Item 9.
6. **Trim surface area:** Items 12, 13 (weather + demo to plugins), 15 (scripts audit).
7. **Consolidation:** Item 16 (hooks), 17 (init).
