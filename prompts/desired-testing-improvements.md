# Desired Testing Improvements

> Testing backlog for Lattice. Items are grouped by priority. Hand this to an agent to work through systematically.

---

## Priority 1: Critical Safety Tests

These test categories protect against data loss and corruption — the highest-stakes failures for a task tracker.

### Concurrent Write Safety

Multiple agents writing simultaneously is the primary use case. Verify no corruption occurs.

- **Same-task concurrent appends:** Two threads/processes both appending events to the same task's JSONL file simultaneously. Verify no interleaved or lost lines.
- **Same-task concurrent snapshot rewrites:** Two threads both rewriting a task snapshot at the same time. Verify atomic write (temp + rename) prevents partial reads.
- **Multi-lock deadlock resistance:** Two processes acquiring overlapping lock sets (e.g., process A locks `events_task1` then `tasks_task1`, process B does the reverse). Verify sorted lock ordering prevents deadlocks.
- **Concurrent create with same ID:** Two agents call `lattice create --id task_XXX` at the same time with identical payloads. Verify exactly one task is created and no duplicate events.
- **Concurrent status changes on same task:** Two agents both try to change status simultaneously. Verify no event is lost and snapshot reflects both events in order.
- **Lock contention under load:** 10+ threads writing events to different tasks simultaneously. Verify all events are recorded and no file corruption occurs.

### Crash Recovery

Simulate failures between event-write and snapshot-write to verify the event-first invariant holds.

- **Crash after event append, before snapshot write:** Manually append an event to a JSONL file without updating the snapshot. Run `lattice rebuild`. Verify the snapshot is regenerated correctly.
- **Crash after partial snapshot write:** Write a truncated JSON file to `tasks/`. Run `lattice doctor`. Verify it detects the corruption. Run `lattice rebuild`. Verify recovery.
- **Crash after event append, before lifecycle log append:** Append an event to a task log but not to `_lifecycle.jsonl`. Run `lattice rebuild --all`. Verify lifecycle log is regenerated correctly.
- **Crash during archive (mid-move):** Simulate a state where the event log has been moved to `archive/events/` but the snapshot hasn't moved yet. Verify `lattice doctor` detects the inconsistency and `lattice rebuild` can recover.

### Rebuild Determinism

The rebuild command must produce identical output regardless of execution order.

- **Single task rebuild is byte-identical:** Create a task, add several events. Rebuild. Compare output byte-for-byte with the original snapshot. They must match.
- **Full rebuild is idempotent:** Run `lattice rebuild --all` twice. The second run should produce byte-identical output to the first.
- **Rebuild order independence:** Rebuild tasks in random order vs. sorted order. Verify identical snapshots.
- **Lifecycle log rebuild is deterministic:** Rebuild lifecycle log multiple times. Verify byte-identical output (events sorted by ts, then id).

---

## Priority 2: Idempotency and Conflict Tests

### Create Idempotency

- **Same ID + same payload:** `lattice create --id task_X "Title"` called twice with identical options returns success both times. Verify only one event in the log.
- **Same ID + different payload:** `lattice create --id task_X "Title A"` then `lattice create --id task_X "Title B"` returns a CONFLICT error on the second call.
- **Same ID + different tags:** Tags order shouldn't matter — `--tags "a,b"` and `--tags "b,a"` should be treated as different payloads (since they're stored as ordered lists).

### Event Idempotency

- **Custom event with same ID:** `lattice event task_X x_deploy --id ev_X --data '{...}'` called twice with same data returns success. Different data returns CONFLICT.

### Artifact Idempotency

- **Attach with same ID:** `lattice attach task_X file.txt --id art_X` called twice. Same file content = success. Different content = CONFLICT.
- **Attach URL with same ID:** Same pattern for URL attachments.

---

## Priority 3: Edge Cases and Validation

### Relationship Integrity

- **Bidirectional display correctness:** Create `A blocks B`. Run `lattice show A` and verify "blocks B" in outgoing. Run `lattice show B` and verify "blocked by A" in incoming.
- **Relationship with archived target:** Create a link to a task, then archive the target. Verify `lattice show` still displays the relationship and `lattice doctor` doesn't flag it as broken.
- **Duplicate relationship rejection:** Try to add the same relationship twice. Verify the second attempt is handled gracefully (either rejected or idempotent).
- **Self-link prevention:** `lattice link task_X blocks task_X` should be rejected.

### Archive/Unarchive Round-Trip

- **Archive then unarchive:** Full round-trip: create task → add events → archive → unarchive. Verify all events and snapshot are intact.
- **Unarchive with notes:** Verify notes are moved back correctly.
- **Unarchive already-active task:** Should return a CONFLICT error.
- **Archive already-archived task:** Should return a CONFLICT error.
- **Show finds archived tasks:** `lattice show task_X` should work for both active and archived tasks.

### Doctor Completeness

- **Doctor detects all documented issues:** Create a `.lattice/` directory with each type of corruption (invalid JSON, truncated JSONL, missing relationship targets, self-links, duplicate edges, malformed IDs, lifecycle log inconsistencies). Run `lattice doctor` and verify all are detected.
- **Doctor --fix repairs truncated JSONL:** Create a JSONL file with a truncated final line. Run `lattice doctor --fix`. Verify the line is removed and the file is otherwise intact.

---

## Priority 4: Output Format Tests

### JSON Envelope Consistency

- **Every write command returns valid JSON with `--json`:** Iterate all write commands (`create`, `update`, `status`, `assign`, `comment`, `link`, `unlink`, `attach`, `event`, `archive`, `unarchive`). Verify each returns `{"ok": true, "data": {...}}` on success.
- **Every error returns valid JSON with `--json`:** Verify each error case returns `{"ok": false, "error": {"code": "...", "message": "..."}}`.
- **Error codes are consistent:** Document and test the error code vocabulary (NOT_FOUND, CONFLICT, VALIDATION_ERROR, INVALID_ACTOR, INVALID_ID, INVALID_TRANSITION).

### Quiet Mode

- **`--quiet` on create returns only the ID:** Verify output is exactly the task ID with no extra text.
- **`--quiet` on other commands returns "ok":** Verify consistent quiet output across all commands.

### Error Messages Include Valid Options

- **Invalid status lists valid statuses**
- **Invalid priority lists valid priorities**
- **Invalid urgency lists valid urgencies**
- **Invalid type lists valid types**
- **Invalid field lists updatable fields and suggests custom_fields**

---

## Priority 5: Integration Tests

### Full Workflow

- **Complete task lifecycle:** Create → assign → status changes through full pipeline → comment → link → attach → archive. Verify event log tells the complete story.
- **Multi-agent collaboration:** Two different actors both contribute events to the same task. Verify attribution is correct on each event.
- **Force transition:** Attempt invalid transition without force (should fail), then with `--force --reason` (should succeed). Verify the force flag and reason are recorded in the event.

### Actor Resolution

- **Flag overrides env var:** Set `LATTICE_ACTOR` and pass `--actor`. Verify `--actor` wins.
- **Env var overrides config default:** Set `LATTICE_ACTOR` with no `--actor`. Verify env var wins.
- **Config default used as fallback:** No `--actor`, no `LATTICE_ACTOR`. Verify config `default_actor` is used.
- **Missing actor errors clearly:** No flag, no env var, no config default. Verify clear error message.

### Dashboard

- **Dashboard serves task list:** Start dashboard, hit `/api/tasks`. Verify response matches active tasks.
- **Dashboard serves archived tasks:** Hit `/api/archived`. Verify response.
- **Dashboard serves task detail:** Hit `/api/tasks/<id>`. Verify full snapshot with notes_exists and artifacts.
- **Dashboard serves events:** Hit `/api/tasks/<id>/events`. Verify events in reverse chronological order.
- **Dashboard serves stats:** Hit `/api/stats`. Verify counts match actual files.
- **Dashboard serves activity feed:** Hit `/api/activity`. Verify recent events from multiple tasks.

---

## Notes for the Testing Agent

- Use `tmp_path` pytest fixture for all filesystem tests. Never touch the real filesystem.
- Core module tests (`test_core/`) should be pure unit tests — no filesystem.
- CLI tests (`test_cli/`) invoke Click commands via `CliRunner` and inspect `.lattice/` state.
- Storage tests (`test_storage/`) use real temp directories.
- For concurrency tests, use `threading` or `multiprocessing` to simulate parallel agents.
- Existing tests are in `tests/`. Check what's already covered before writing duplicates.
