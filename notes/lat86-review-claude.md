# LAT-86 Code Review: Enhanced Comment System

**Reviewer:** Claude Opus 4.6
**Date:** 2026-02-16
**Scope:** New comment materialization, edit/delete/react/unreact commands, dashboard endpoints, MCP tools

---

## Overall Assessment

This is a well-structured feature addition that follows Lattice's established event-sourced patterns. The separation of pure materialization logic in `core/comments.py` from I/O in CLI/dashboard/MCP is clean. The test coverage is solid for the happy paths and core edge cases. There are a few issues ranging from a significant code duplication problem to minor API design considerations.

**Verdict:** Approve with requested changes (1 must-fix, several should-fix).

---

## 1. Correctness

### 1.1 MUST-FIX: Massive code duplication in `_flat_comments` vs `materialize_comments`

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/core/comments.py`
**Lines:** 177-249 vs 16-107

`_flat_comments()` is a near-exact copy of the event processing loop from `materialize_comments()`, minus the threading step and minus the `replies` field on each comment dict. This is ~70 lines of duplicated logic that will drift over time. If a new comment event type is added or the materialization logic changes, both functions must be updated in lockstep.

**Fix:** Extract the shared event-processing loop into a single private function, then have both `materialize_comments()` and `_flat_comments()` call it. For example:

```python
def _build_comments_map(events: list[dict]) -> dict[str, dict]:
    """Process events into a {comment_id: comment_dict} map."""
    comments_by_id: dict[str, dict] = {}
    for ev in events:
        # ... shared processing ...
    return comments_by_id

def materialize_comments(events: list[dict]) -> list[dict]:
    comments_by_id = _build_comments_map(events)
    # Add empty replies list, then thread
    for c in comments_by_id.values():
        c.setdefault("replies", [])
    # ... threading logic ...
    return top_level

def _flat_comments(events: list[dict]) -> list[dict]:
    return list(_build_comments_map(events).values())
```

### 1.2 OK: Edit-after-delete correctly ignored

The `comment_edited` handler checks `not comment["deleted"]` before applying the edit. This is correct and tested in `test_edit_after_delete_ignored`.

### 1.3 OK: Reaction on deleted comment correctly ignored

The `reaction_added` handler checks `not comment["deleted"]`. Tested in `test_reaction_on_deleted_ignored`.

### 1.4 OK: Nested reply rejection

`validate_comment_for_reply()` correctly checks `parent["parent_id"] is not None` to reject replies-to-replies. Tested in `test_reply_to_reply_rejected`.

### 1.5 MINOR: `reaction_removed` does not check `deleted` status

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/core/comments.py`
**Line:** 91

In `materialize_comments()`, the `reaction_removed` handler does NOT check `comment["deleted"]`:

```python
elif etype == "reaction_removed":
    # ...
    comment = comments_by_id.get(target_id)
    if comment is not None:  # <-- no "and not comment['deleted']" check
```

This is actually fine for materialization (if a comment was reacted to before deletion, and then the reaction is removed, the removal should apply). However, the asymmetry with `reaction_added` (which checks deleted) is worth a comment explaining the intentional design. Currently it looks like it might be an oversight.

### 1.6 NOTE: `comment_added` event uses event `id` as comment ID

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/core/comments.py`
**Line:** 34

```python
comment_id = ev["id"]
```

The comment ID is the event ID itself (e.g., `ev_01HQ...`). This is a deliberate design choice that avoids needing a separate comment ID namespace. It works well since each `comment_added` event is unique. Worth noting in the docstring for future maintainers, since it means `comment_id` parameters in `comment_edited`, `comment_deleted`, and `reaction_added`/`reaction_removed` all refer to event IDs.

### 1.7 MINOR: `_flat_comments` doesn't include a `replies` field

In `_flat_comments()` the comment dicts lack a `replies` key, while `materialize_comments()` includes one. The validation functions use `_flat_comments()` and only access `id`, `body`, `deleted`, `parent_id` -- so this is fine. But if a caller ever expects `replies` from `_flat_comments`, it will KeyError. Since `_flat_comments` is private, this is acceptable.

---

## 2. Consistency with Codebase Patterns

### 2.1 GOOD: Event-first writes

All new commands follow the established pattern: create event -> apply to snapshot -> `write_task_event()` which handles lock, event append, snapshot write, lifecycle, and hooks. No deviations.

### 2.2 GOOD: New event types in `_NOOP_EVENT_TYPES`

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/core/tasks.py`
**Lines:** 157-168

All four new event types (`comment_edited`, `comment_deleted`, `reaction_added`, `reaction_removed`) are correctly added to `_NOOP_EVENT_TYPES` since they don't modify the task snapshot (only update `last_event_id` and `updated_at`). `comment_added` was already there.

### 2.3 GOOD: Hook entries in config

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/core/config.py`
**Lines:** 35-39

All four new event types are added to `HooksOnConfig`, enabling per-event-type hook configuration. This is consistent with how existing event types have hook support.

### 2.4 SHOULD-FIX: `storage/readers.py` duplicates existing patterns

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/storage/readers.py`

This new module provides `read_task_events()` which is functionally identical to:
- `_read_events()` in `query_cmds.py` (lines 600-616)
- `_read_events()` in `mcp/tools.py` (lines 121-137)
- `_read_task_events()` in `dashboard/server.py` (lines 1622-1637)

The new shared helper is the right idea, but the old duplicates in `query_cmds.py`, `mcp/tools.py`, and `dashboard/server.py` were NOT replaced. The result is *more* duplication, not less. Some call sites use the new shared helper (`task_cmds.py`, `query_cmds.py` comments command, `dashboard/server.py` comment endpoints), while others still use their local `_read_events()`.

**Fix:** Replace all remaining local `_read_events` / `_read_task_events` functions with the shared `read_task_events` from `storage/readers.py`. The `_read_events` in `query_cmds.py` (line 600), `_read_task_events` + `_read_task_events_archive` in `dashboard/server.py` (lines 1622-1655), and `_read_events` in `mcp/tools.py` (line 121) should all be removed in favor of the new shared reader. The dashboard's `_read_task_events` returns `None` for missing files while the shared reader returns `[]`, so callers need minor adjustment.

### 2.5 GOOD: JSON output format

The `comments` command's JSON output uses `json_envelope(True, data=comments)` which matches the standard `{"ok": true, "data": ...}` envelope.

---

## 3. Error Handling

### 3.1 GOOD: Validation errors surface properly

All validation functions in `core/comments.py` raise `ValueError` with descriptive messages. CLI commands catch these with `try/except ValueError` and route through `output_error()`, which correctly handles both JSON and human-readable output modes.

### 3.2 MINOR: CLI `comment-edit` has unreachable `return` statement

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/cli/task_cmds.py`
**Line:** 781

```python
    except ValueError as exc:
        output_error(str(exc), "VALIDATION_ERROR", is_json)
        return  # unreachable -- output_error exits, but keeps type checker happy
```

This is acknowledged with a comment. The pattern is fine but inconsistent -- other handlers in the same file (e.g., `comment_delete` at line 848) do NOT have this `return`. Either add it everywhere for consistency or remove it. Since `output_error` has return type `NoReturn`, the type checker should be fine without it.

### 3.3 SHOULD-FIX: Dashboard `unreact` validates with `validate_comment_for_react` instead of checking reaction existence

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/dashboard/server.py`
**Lines:** 1571-1576

```python
events = read_task_events(ld, task_id)
try:
    validate_comment_for_react(events, comment_id)
except ValueError as exc:
    self._send_json(400, _err("VALIDATION_ERROR", str(exc)))
    return
```

The unreact endpoint validates that the comment exists and isn't deleted (via `validate_comment_for_react`), but it does NOT verify that the actor actually has the reaction being removed. Compare with the CLI `unreact` command (task_cmds.py lines 1004-1021) which explicitly checks reaction existence. The dashboard endpoint will silently write a `reaction_removed` event even if the actor never had that reaction, creating a "phantom removal" event.

**Fix:** Add reaction-existence checking in the dashboard unreact handler, matching the CLI behavior. Alternatively, extract this check into a `validate_comment_for_unreact()` function in `core/comments.py`.

### 3.4 NOTE: Dashboard comment-edit/delete POST endpoints read snapshot outside lock

All dashboard POST endpoints read the snapshot outside the lock (noted in comments as "acceptable TOCTOU at v0 scale"). This is consistent with existing dashboard patterns (e.g., status change). Not a current issue but worth noting -- two simultaneous edits could both succeed based on stale validation state.

---

## 4. Test Coverage

### 4.1 GOOD: Core materialization tests cover key edge cases

`test_core/test_comments.py` covers:
- Empty events
- Single comment
- Threaded replies
- Edit with history
- Delete
- Reactions (add, remove, idempotent, multiple reactors)
- Edit after delete (ignored)
- Reaction on deleted (ignored)
- Non-comment events ignored

### 4.2 GOOD: CLI integration tests cover command surface

`test_cli/test_comment_cmds.py` covers:
- Reply to top-level, to nonexistent, to reply (rejected)
- Edit comment, nonexistent, deleted
- Delete comment, already deleted
- React, idempotent reaction, invalid emoji
- Unreact, unreact nonexistent
- Comments read: empty, with content, JSON output, threaded, deleted placeholder

### 4.3 SHOULD-ADD: Missing test for `_flatten_comments` helper in `task_cmds.py`

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/cli/task_cmds.py`
**Lines:** 1046-1052

The `_flatten_comments()` helper (used by `react` and `unreact` CLI commands) is untested directly. While it's exercised indirectly through the idempotent reaction test, a direct test would catch regressions.

### 4.4 SHOULD-ADD: Missing test for edit history accumulation (multiple edits)

The tests verify a single edit produces one `edit_history` entry. There's no test verifying that two sequential edits produce two history entries with correct ordering. This is important for the edit audit trail.

### 4.5 SHOULD-ADD: Missing test for reaction on reply comments

All reaction tests use top-level comments. There's no test verifying reactions work correctly on reply comments (which are nested inside `replies`). The MCP `lattice_react` tool's idempotency check explicitly searches replies (lines 1049-1053), but this code path is untested.

### 4.6 SHOULD-ADD: Missing test for `read_task_events` with malformed JSONL

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/storage/readers.py`

The reader silently skips `JSONDecodeError` on individual lines and `OSError` on the whole file. A test verifying this resilience would be valuable -- e.g., a JSONL file with one valid line and one corrupt line should return only the valid event.

### 4.7 MINOR: No dashboard or MCP endpoint tests

The new dashboard endpoints (`comment-edit`, `comment-delete`, `react`, `unreact`, `comments`) and MCP tools (`lattice_comment_edit`, `lattice_comment_delete`, `lattice_react`, `lattice_unreact`, `lattice_comments`) have no dedicated tests. The CLI tests provide confidence in the core logic, but the dashboard/MCP wiring has distinct validation paths (e.g., the dashboard unreact bug noted in 3.3).

---

## 5. Security / Safety

### 5.1 GOOD: Emoji validation

`_EMOJI_RE = re.compile(r"^[a-zA-Z0-9_-]{1,50}$")` is a solid allowlist. Rejects colons, spaces, Unicode, and length > 50. Used consistently in CLI, dashboard, and MCP.

### 5.2 GOOD: Actor validation

All write paths validate actor format via `validate_actor()` or `_validate_actor()` before any writes.

### 5.3 GOOD: Comment body handling

The dashboard endpoints strip whitespace from comment bodies (`comment_body.strip()`, `new_body.strip()`). The CLI does not strip, which is a minor inconsistency but not a security concern. Empty/whitespace-only bodies are rejected in the dashboard via `not comment_body.strip()` checks.

### 5.4 NOTE: No length limit on comment bodies

There's no maximum length validation on comment bodies in any layer (CLI, dashboard, MCP). An actor could write an arbitrarily large comment body that gets stored in the event log. The dashboard has the global `MAX_REQUEST_BODY_BYTES = 1_048_576` limit on POST body size, which provides implicit protection for that path. The CLI and MCP have no such limit.

This is acceptable for v0 but worth noting as a future hardening item.

### 5.5 NOTE: No authorization on edit/delete

Any actor can edit or delete any comment. There's no check that the editing/deleting actor is the original comment author. This is consistent with the v0 design philosophy ("no authentication or multi-user access control" per CLAUDE.md), but it's worth documenting that comment operations are not author-restricted.

---

## 6. API Design

### 6.1 GOOD: CLI command naming

The naming convention is consistent: `comment`, `comment-edit`, `comment-delete`, `react`, `unreact`, `comments` (read). Hyphenated names follow Click conventions and are discoverable.

### 6.2 GOOD: `--reply-to` on existing `comment` command

Adding `--reply-to` to the existing `comment` command (instead of a separate `reply` command) is the right choice. It keeps the command count low and models the reality that a reply is just a comment with a parent.

### 6.3 GOOD: Dashboard endpoint design

The REST-like pattern (`POST /api/tasks/<id>/comment-edit`, etc.) is consistent with existing endpoints (`POST /api/tasks/<id>/status`, `POST /api/tasks/<id>/assign`).

### 6.4 GOOD: `GET /api/tasks/<id>/comments` returns materialized tree

The dashboard comments endpoint returns the fully materialized threaded comment tree, which is exactly what a frontend needs to render. Good API design -- callers don't need to materialize client-side.

### 6.5 MINOR: MCP `lattice_react` idempotency search misses deeply-nested structure

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/mcp/tools.py`
**Lines:** 1041-1054

The MCP tool searches for the target comment in the threaded tree (top-level + replies). However, the search uses a `break` after the inner loop that would exit the outer loop prematurely if the comment is a reply:

```python
for comment in comments:
    if comment["id"] == comment_id:
        # check...
        break
    for reply in comment.get("replies", []):
        if reply["id"] == comment_id:
            # check...
            break  # <-- only breaks inner loop
```

The outer `break` is never reached when the match is in a reply -- the inner `break` exits the inner `for`, but the outer `for` continues to the next comment. This means:
1. If the target is a reply in the first comment's replies, the search continues unnecessarily.
2. If the target is a reply, the outer `for` will not `break`, and execution falls through correctly to the event creation below.

This is not a correctness bug (the idempotency check still works because the inner match sets the right state and returns), but the control flow is confusing. The CLI's `_flatten_comments` approach in `task_cmds.py` is cleaner -- flatten first, then search linearly.

### 6.6 GOOD: `lattice_comments` read-only MCP tool

Having a dedicated read-only `lattice_comments` tool is good for agent workflows that need to inspect comment threads without needing to parse raw events.

### 6.7 SHOULD-FIX: Dashboard `react` endpoint does not check idempotency

**File:** `/Users/atin/Projects/Fractal Agentics/PROJECTS/Lattice/src/lattice/dashboard/server.py`
**Lines:** 1438-1512

The dashboard `react` endpoint validates the comment exists and isn't deleted, then writes a `reaction_added` event unconditionally. It does NOT check if the actor already has this reaction (unlike the CLI and MCP tools which check for idempotency). This means duplicate reactions from the dashboard will create redundant events in the log. The materialization is idempotent (duplicate actors in the same emoji are deduped), so the materialized state will be correct, but the event log will have noise.

**Fix:** Add the same idempotency check used in the CLI (`task_cmds.py` lines 922-935) to the dashboard endpoint.

---

## 7. Summary of Action Items

### Must-Fix (1)
1. **Extract shared event-processing loop** in `core/comments.py` to eliminate the `_flat_comments` / `materialize_comments` duplication (Section 1.1)

### Should-Fix (3)
2. **Replace remaining local event readers** with shared `storage/readers.py` helper (Section 2.4)
3. **Dashboard unreact: validate reaction existence** before writing removal event (Section 3.3)
4. **Dashboard react: add idempotency check** to avoid duplicate events (Section 6.7)

### Should-Add Tests (4)
5. Multiple sequential edits producing correct `edit_history` (Section 4.4)
6. Reactions on reply comments (Section 4.5)
7. `read_task_events` resilience with malformed JSONL (Section 4.6)
8. Dashboard/MCP endpoint wiring tests (Section 4.7)

### Nice-to-Have (3)
9. Comment explaining intentional asymmetry in `reaction_removed` deleted check (Section 1.5)
10. Remove unreachable `return` or add consistently (Section 3.2)
11. Document that comment IDs are event IDs in the docstring (Section 1.6)
