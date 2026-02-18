# Lattice Exploratory Audit (Simplicity + Extensibility + Recursive Primitive)

Date: 2026-02-18 18:10 EST  
Scope: `src/`, `tests/`, `scripts/`, `docs/`, site/package shape  
Checks run:
- `uv run mypy src` -> **412 errors across 33 files**
- `uv run ruff check src tests` -> **pass**
- `uv run pytest` -> **1 failed, 1535 passed** (`tests/test_dashboard/test_server.py:510`)

## Prioritized Numbered Actions

1. **[Blocker][CHANGE] Unify status-transition policy across CLI and MCP.** MCP status writes (`src/lattice/mcp/tools.py:359`) can drift from CLI policy enforcement (`src/lattice/cli/task_cmds.py:469`, `src/lattice/core/config.py:326`). Move validation into one shared write pipeline.
2. **[Blocker][CHANGE] Extract task mutation logic out of HTTP handlers.** Dashboard task writes currently live in transport handlers (`src/lattice/dashboard/server.py:819`, `src/lattice/dashboard/server.py:1328`, `src/lattice/dashboard/server.py:1710`) instead of a shared domain service.
3. **[Blocker][CHANGE] Split the dashboard monolith into router + services.** `LatticeHandler` centralizes routing, validation, storage writes, and response shaping (`src/lattice/dashboard/server.py:75`, `src/lattice/dashboard/server.py:114`). This is the largest hidden coupling point.
4. **[Blocker][CHANGE] Move archive transaction flow out of HTTP layer.** `_handle_post_task_archive` mixes lock lifecycle, events, file moves, and hooks (`src/lattice/dashboard/server.py:1467`). Extract to reusable archive operation.
5. **[Blocker][REMOVE] Remove OS shell-launch side effects from dashboard API.** HTTP endpoints open editors/filesystem tools directly (`src/lattice/dashboard/server.py:1906`, `src/lattice/dashboard/server.py:1949`). Keep server pure; move launch behavior to client/CLI.
6. **[Blocker][CHANGE] Refactor `next --claim` to use one atomic storage/core operation.** Current implementation manually does lock/read/mutate/write/hook orchestration (`src/lattice/cli/query_cmds.py:443`) and duplicates low-level persistence paths.
7. **[Blocker][CHANGE] Refactor `resource acquire` into a dedicated resource service.** One handler owns locking, eviction, wait/backoff, and write semantics (`src/lattice/cli/resource_cmds.py:170`), making policy changes brittle.
8. **[Blocker][CHANGE] Move archive/unarchive file orchestration into storage/core API.** Raw filesystem lifecycle logic remains in CLI commands (`src/lattice/cli/archive_cmds.py:125`, `src/lattice/cli/archive_cmds.py:458`).
9. **[Blocker][EDIT] Resolve dashboard bind-error contract mismatch.** Test expects `BIND_ERROR` but runtime emits `PORT_IN_USE` (`tests/test_dashboard/test_server.py:483`, `tests/test_dashboard/test_server.py:510`). Standardize one public error contract.
10. **[Blocker][ADD] Add CLI/MCP parity tests for status policy and transition rules.** Current drift risk is architectural; contract tests should enforce identical invariants on both interfaces (`src/lattice/cli/task_cmds.py:469`, `src/lattice/mcp/tools.py:359`).
11. **[Blocker][CHANGE] Decide and enforce a type-safety strategy.** Project advertises strict typing but currently has 412 mypy failures; either gate on targeted modules first or reduce claim of strictness.
12. **[Blocker][CHANGE] Break up ultra-large modules that accumulate mixed concerns.** Largest hotspots are `src/lattice/dashboard/server.py` (2215 LOC), `src/lattice/mcp/tools.py` (1338), `src/lattice/cli/query_cmds.py` (1256), `src/lattice/cli/main.py` (1176), `src/lattice/cli/task_cmds.py` (1148).

13. **[Important][CHANGE] Remove duplicate snapshot listing/filter logic across interfaces.** MCP and CLI both implement similar traversal/filtering (`src/lattice/mcp/resources.py:40`, `src/lattice/cli/query_cmds.py:307`).
14. **[Important][CHANGE] Consolidate task detail assembly in one reader path.** MCP detail route and CLI show path are parallel but separate (`src/lattice/mcp/resources.py:85`, `src/lattice/cli/query_cmds.py:627`).
15. **[Important][CHANGE] Deduplicate hook execution orchestration for task/resource events.** Two near-identical flows diverge over time risk (`src/lattice/storage/hooks.py:14`, `src/lattice/storage/hooks.py:134`).
16. **[Important][CHANGE] Collapse duplicate evidence-role extraction helpers into one iterator model.** Three helper functions currently re-loop and fallback similarly (`src/lattice/core/tasks.py:342`, `src/lattice/core/tasks.py:365`, `src/lattice/core/tasks.py:384`).
17. **[Important][CHANGE] Stop rebuilding comment state for each comment validation call.** Comment map rebuild happens repeatedly via wrapper path (`src/lattice/core/comments.py:33`, `src/lattice/core/comments.py:146`).
18. **[Important][CHANGE] Avoid rebuilding relationship adjacency on each epic status derivation.** Current recursive derivation rebuilds graph links per call (`src/lattice/core/tasks.py:430`).
19. **[Important][CHANGE] Parse holder timestamps once per resource evaluation pass.** Staleness and availability checks repeatedly parse timestamps (`src/lattice/core/resources.py:58`, `src/lattice/core/resources.py:71`, `src/lattice/core/resources.py:84`).
20. **[Important][CHANGE] Centralize config loading for dashboard writes.** `config.json` is repeatedly loaded across handlers (`src/lattice/dashboard/server.py:263`, `src/lattice/dashboard/server.py:1751`, `src/lattice/dashboard/server.py:1846`).
21. **[Important][CHANGE] Move dashboard activity aggregation/filtering into shared core module.** Event collection/faceting/filtering lives only in server module (`src/lattice/dashboard/server.py:2005`, `src/lattice/dashboard/server.py:2040`, `src/lattice/dashboard/server.py:2078`).
22. **[Important][CHANGE] Harden plugin loading against `BaseException` shutdown paths.** Plugin/template discovery catches `Exception` only (`src/lattice/plugins.py:30`, `src/lattice/plugins.py:58`), so `SystemExit` can kill startup.
23. **[Important][CHANGE] Replace manual command-module side-effect imports with registry/discovery.** Static import block is brittle (`src/lattice/cli/main.py:1152`).
24. **[Important][CHANGE] Decouple plugin load timing from import-time CLI construction.** Plugin loading happens immediately after manual imports (`src/lattice/cli/main.py:1169`), reducing composability.
25. **[Important][CHANGE] Make `init` side effects explicit/optional.** `init` mixes setup with agent-doc updates/dashboard behavior (`src/lattice/cli/main.py:585`). Keep base initialization minimal.
26. **[Important][REMOVE] Move non-core reporting commands behind optional plugin boundary.** Weather command expands surface area beyond core primitive (`src/lattice/cli/weather_cmds.py:435`, wired in `src/lattice/cli/main.py:1163`).
27. **[Important][REMOVE] Move demo scaffolding behind optional plugin boundary.** Demo command should not inflate the default operator surface (`src/lattice/cli/demo_cmd.py`, wired in `src/lattice/cli/main.py:1165`).
28. **[Important][CHANGE] Separate runtime package from agent/docs payload.** Agent skill/template assets ship with runtime (`src/lattice/skills/lattice/SKILL.md`, `src/lattice/templates/claude_md_block.py`); consider optional extra package.
29. **[Important][ADD] Add architecture guardrails around interface boundaries.** Establish explicit rule: core/storage owns mutation semantics; CLI/MCP/dashboard only adapt IO + formatting.
30. **[Important][ADD] Add complexity budget checks in CI for key modules.** Prevent further growth of already-large files listed in item 12.

31. **[Potential][CHANGE] Rebuild dashboard fixtures using canonical event writers instead of handcrafted JSON.** Current fixture path can drift from real contracts (`tests/test_dashboard/conftest.py:20`).
32. **[Potential][ADD] Add recursion stress tests for deep parent/child and nested comments.** Current recursive intent is strong, but should be protected with explicit depth/performance tests (`src/lattice/core/tasks.py:430`, `src/lattice/core/comments.py:33`).
33. **[Potential][ADD] Add contract tests for archive lifecycle parity across CLI/dashboard.** Archive semantics are implemented in multiple surfaces (`src/lattice/cli/archive_cmds.py:125`, `src/lattice/dashboard/server.py:1467`).
34. **[Potential][EDIT] Prune or relocate stale documentation variants in `archive/`.** Multiple versioned philosophy/user-guide docs can obscure canonical guidance (`archive/Philosophy_v1.md`, `archive/user-guide-v0.md`).
35. **[Potential][EDIT] Prune or relocate playful scripts from core repo root workflow.** Scripts appear non-essential and lightly integrated (`scripts/dead_letters.py`, `scripts/fizzbuzz.py`, `scripts/status_haikus.py`, `scripts/lattice_art.py`).
36. **[Potential][EDIT] Replace default Astro starter README with project-specific docs.** `site/README.md:1` still contains template content, which reduces signal for contributors.
37. **[Potential][ADD] Introduce explicit API versioning for plugin/template extension points.** Helps preserve mutation space without breaking adopters (`src/lattice/plugins.py:30`, `src/lattice/plugins.py:58`).
38. **[Potential][ADD] Introduce a minimal-core mode profile (`task`, `status`, `assign`, `link`, `query`) for default installs.** Keeps opinions strong but surface area small; optional modules can layer on top.
39. **[Potential][ADD] Create a single “task write transaction” abstraction used by CLI, MCP, and dashboard.** This is the key recursion/extensibility primitive and removes duplicate lock/write/hook choreography.
40. **[Potential][ADD] Publish and enforce a boundary map in docs (`core`, `storage`, `interfaces`, `optional`).** This will make future mutation intentional instead of accidental sprawl.

## Suggested Execution Order

1. Stabilize contracts: items 1, 9, 10.
2. Carve out shared mutation service: items 2, 4, 6, 7, 8, 39.
3. Reduce interface duplication: items 13, 14, 15, 20, 21, 23, 24.
4. Trim optional/non-core surface: items 5, 26, 27, 28, 34, 35, 36.
5. Lock in maintainability guardrails: items 11, 12, 29, 30, 31, 32, 33, 37, 40.
