# Code Review: LAT-86 — Enhanced Comment System

## Findings (ordered by severity)

1. **High: `unreact` dashboard endpoint records no-op removals as real events**
- **Where:** `src/lattice/dashboard/server.py:1518`, `src/lattice/dashboard/server.py:1578`
- **What:** `_handle_post_task_unreact()` validates `comment_id`/`emoji`/actor and comment existence, but never verifies that the actor currently has that reaction before appending `reaction_removed`.
- **Impact:** Calls that should fail (or no-op) are persisted as new events and can trigger hooks, creating misleading audit history and duplicate automations.
- **Evidence of inconsistency:** CLI and MCP unreact paths explicitly check presence before writing (`src/lattice/cli/task_cmds.py:1006`, `src/lattice/mcp/tools.py:1093`).
- **Recommendation:** Add a pre-write existence check in dashboard unreact (same logic as CLI/MCP), then return `NOT_FOUND` or an explicit idempotent no-op response.

2. **Medium-High: Dashboard `react` is non-idempotent while other surfaces are idempotent**
- **Where:** `src/lattice/dashboard/server.py:1498`
- **What:** `_handle_post_task_react()` always appends `reaction_added`; it does not short-circuit if the same actor already reacted with the same emoji.
- **Impact:** Materialized state deduplicates actors, but event logs and hooks still receive duplicate events, increasing noise and side effects.
- **Evidence of inconsistency:** CLI and MCP implement idempotency checks (`src/lattice/cli/task_cmds.py:922`, `src/lattice/mcp/tools.py:1040`).
- **Recommendation:** Mirror CLI/MCP idempotency behavior in dashboard endpoint before creating the event.

3. **Medium: Comment body validation is inconsistent across write interfaces**
- **Where:**
  - CLI accepts raw comment/edit text: `src/lattice/cli/task_cmds.py:712`, `src/lattice/cli/task_cmds.py:789`
  - MCP accepts raw comment/edit text: `src/lattice/mcp/tools.py:469`, `src/lattice/mcp/tools.py:976`
  - Dashboard rejects empty/whitespace and trims: `src/lattice/dashboard/server.py:1009`, `src/lattice/dashboard/server.py:1323`, `src/lattice/dashboard/server.py:1039`, `src/lattice/dashboard/server.py:1357`
- **What:** CLI/MCP allow empty or whitespace-only bodies that dashboard rejects.
- **Impact:** Same logical operation succeeds/fails depending on entrypoint; blank comments can be persisted through CLI/MCP.
- **Recommendation:** Centralize body validation/normalization in `lattice.core.comments` and reuse it in CLI, dashboard, and MCP.

4. **Medium: CLI/MCP `unreact` error semantics are weaker than `react` (missing comment validation)**
- **Where:** `src/lattice/cli/task_cmds.py:1004`, `src/lattice/mcp/tools.py:1091`
- **What:** Neither path calls `validate_comment_for_react()` before checking for actor-specific reaction presence.
- **Impact:** Missing/deleted comment IDs can return misleading “reaction not found” errors instead of “comment not found/deleted”, and behavior diverges from `react`/dashboard paths.
- **Recommendation:** Validate target comment first (`validate_comment_for_react`) then check actor+emoji presence.

5. **Low: `_event_summary()` can raise on malformed comment/reaction events**
- **Where:** `src/lattice/cli/query_cmds.py:858`, `src/lattice/cli/query_cmds.py:860`, `src/lattice/cli/query_cmds.py:862`, `src/lattice/cli/query_cmds.py:864`
- **What:** Uses `data["comment_id"]` / `data["emoji"]` indexing instead of `.get()`.
- **Impact:** A single malformed event record can crash history rendering.
- **Recommendation:** Use safe `.get()` fallbacks, consistent with the rest of `_event_summary()`.

## Coverage Gaps

1. **No tests in-scope for dashboard comment/reaction endpoints**
- Current scope includes CLI/core tests (`tests/test_core/test_comments.py`, `tests/test_cli/test_comment_cmds.py`), but not dashboard endpoint behavior.
- Missing high-value cases: dashboard `react` idempotency and dashboard `unreact` “reaction absent” handling.

2. **No tests in-scope for MCP comment/reaction tools**
- Missing cases: MCP `unreact` on nonexistent/deleted comments, MCP body validation parity with dashboard, and MCP idempotency parity checks.

3. **No defensive test for malformed event payloads in `_event_summary()`**
- A regression test with comment/reaction events missing keys would prevent runtime KeyErrors.

## Notable Strengths

1. `materialize_comments()` handles key edge cases correctly (edit-after-delete ignored, react-on-deleted ignored, duplicate reactions deduped) (`src/lattice/core/comments.py:54`, `src/lattice/core/comments.py:79`, `src/lattice/core/comments.py:83`).
2. Event model wiring is complete across core enums/no-op handling/hooks typing (`src/lattice/core/events.py:23`, `src/lattice/core/tasks.py:159`, `src/lattice/core/config.py:35`).
3. Shared `read_task_events()` helper reduces duplicated event-reading logic (`src/lattice/storage/readers.py:9`).

## Verification Notes

- I reviewed all files listed in scope.
- I attempted to run scoped tests, but this environment is missing dependency `ulid`, so full CLI/event test execution could not complete.
  - `tests/test_core/test_comments.py` can collect/run with `PYTHONPATH=src`.
  - CLI and events tests fail to import due `ModuleNotFoundError: No module named 'ulid'`.
