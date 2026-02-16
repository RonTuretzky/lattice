"""Tests for lattice branch-link and branch-unlink CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from lattice.storage.fs import LATTICE_DIR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_task(invoke) -> str:
    """Create a task and return its ID."""
    r = invoke("create", "Test task", "--actor", "human:test", "--json")
    assert r.exit_code == 0, f"create failed: {r.output}"
    return json.loads(r.output)["data"]["id"]


def _read_snapshot(initialized_root: Path, task_id: str) -> dict:
    """Read a task snapshot directly from disk."""
    path = initialized_root / LATTICE_DIR / "tasks" / f"{task_id}.json"
    return json.loads(path.read_text())


def _read_events(initialized_root: Path, task_id: str) -> list[dict]:
    """Read all events for a task from its JSONL file."""
    path = initialized_root / LATTICE_DIR / "events" / f"{task_id}.jsonl"
    lines = path.read_text().strip().split("\n")
    return [json.loads(line) for line in lines if line]


# ---------------------------------------------------------------------------
# lattice branch-link
# ---------------------------------------------------------------------------


class TestBranchLinkValid:
    """Happy-path tests for lattice branch-link."""

    def test_branch_link_creates_link(self, invoke, initialized_root: Path) -> None:
        task_id = _create_task(invoke)
        result = invoke("branch-link", task_id, "feat/LAT-42", "--actor", "human:test")
        assert result.exit_code == 0
        assert "Linked branch" in result.output
        assert "feat/LAT-42" in result.output

        # Verify snapshot
        snap = _read_snapshot(initialized_root, task_id)
        assert len(snap["branch_links"]) == 1
        bl = snap["branch_links"][0]
        assert bl["branch"] == "feat/LAT-42"
        assert bl["repo"] is None
        assert bl["linked_by"] == "human:test"

    def test_branch_link_with_repo(self, invoke, initialized_root: Path) -> None:
        task_id = _create_task(invoke)
        result = invoke(
            "branch-link", task_id, "feat/login", "--repo", "lattice", "--actor", "human:test"
        )
        assert result.exit_code == 0

        snap = _read_snapshot(initialized_root, task_id)
        assert snap["branch_links"][0]["branch"] == "feat/login"
        assert snap["branch_links"][0]["repo"] == "lattice"

    def test_branch_link_appends_event(self, invoke, initialized_root: Path) -> None:
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "feat/test", "--actor", "human:test")

        events = _read_events(initialized_root, task_id)
        bl_events = [e for e in events if e["type"] == "branch_linked"]
        assert len(bl_events) == 1
        assert bl_events[0]["data"]["branch"] == "feat/test"

    def test_branch_link_updates_bookkeeping(self, invoke, initialized_root: Path) -> None:
        task_id = _create_task(invoke)
        snap_before = _read_snapshot(initialized_root, task_id)

        invoke("branch-link", task_id, "feat/test", "--actor", "human:test")

        snap_after = _read_snapshot(initialized_root, task_id)
        assert snap_after["last_event_id"] != snap_before["last_event_id"]
        assert snap_after["updated_at"] >= snap_before["updated_at"]

    def test_multiple_branches_allowed(self, invoke, initialized_root: Path) -> None:
        task_id = _create_task(invoke)
        r1 = invoke("branch-link", task_id, "feat/a", "--actor", "human:test")
        assert r1.exit_code == 0
        r2 = invoke("branch-link", task_id, "feat/b", "--actor", "human:test")
        assert r2.exit_code == 0

        snap = _read_snapshot(initialized_root, task_id)
        assert len(snap["branch_links"]) == 2

    def test_same_branch_different_repo_allowed(self, invoke, initialized_root: Path) -> None:
        task_id = _create_task(invoke)
        r1 = invoke("branch-link", task_id, "main", "--repo", "frontend", "--actor", "human:test")
        assert r1.exit_code == 0
        r2 = invoke("branch-link", task_id, "main", "--repo", "backend", "--actor", "human:test")
        assert r2.exit_code == 0

        snap = _read_snapshot(initialized_root, task_id)
        assert len(snap["branch_links"]) == 2


class TestBranchLinkJsonOutput:
    """--json flag produces structured output."""

    def test_json_success(self, invoke) -> None:
        task_id = _create_task(invoke)
        result = invoke("branch-link", task_id, "feat/test", "--actor", "human:test", "--json")
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["ok"] is True
        assert len(parsed["data"]["branch_links"]) == 1

    def test_json_error_duplicate(self, invoke) -> None:
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "feat/test", "--actor", "human:test")
        result = invoke("branch-link", task_id, "feat/test", "--actor", "human:test", "--json")
        assert result.exit_code == 1
        parsed = json.loads(result.output)
        assert parsed["ok"] is False
        assert parsed["error"]["code"] == "CONFLICT"


class TestBranchLinkQuietOutput:
    """--quiet flag prints only the task ID."""

    def test_quiet_success(self, invoke) -> None:
        task_id = _create_task(invoke)
        result = invoke("branch-link", task_id, "feat/test", "--actor", "human:test", "--quiet")
        assert result.exit_code == 0
        assert result.output.strip() == task_id


class TestBranchLinkErrors:
    """Error cases for lattice branch-link."""

    def test_duplicate_rejected(self, invoke) -> None:
        task_id = _create_task(invoke)
        r1 = invoke("branch-link", task_id, "feat/test", "--actor", "human:test")
        assert r1.exit_code == 0

        r2 = invoke("branch-link", task_id, "feat/test", "--actor", "human:test")
        assert r2.exit_code == 1
        assert "Duplicate" in r2.stderr

    def test_duplicate_with_repo_rejected(self, invoke) -> None:
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "main", "--repo", "lattice", "--actor", "human:test")
        result = invoke(
            "branch-link", task_id, "main", "--repo", "lattice", "--actor", "human:test"
        )
        assert result.exit_code == 1
        assert "Duplicate" in result.stderr

    def test_task_not_found(self, invoke) -> None:
        fake_id = "task_01ZZZZZZZZZZZZZZZZZZZZZZZZ"
        result = invoke("branch-link", fake_id, "feat/test", "--actor", "human:test")
        assert result.exit_code == 1
        assert "not found" in result.stderr.lower()

    def test_invalid_actor(self, invoke) -> None:
        task_id = _create_task(invoke)
        result = invoke("branch-link", task_id, "feat/test", "--actor", "bad-format")
        assert result.exit_code == 1
        assert "Invalid actor" in result.stderr


# ---------------------------------------------------------------------------
# lattice branch-unlink
# ---------------------------------------------------------------------------


class TestBranchUnlinkValid:
    """Happy-path tests for lattice branch-unlink."""

    def test_branch_unlink_removes_link(self, invoke, initialized_root: Path) -> None:
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "feat/test", "--actor", "human:test")

        result = invoke("branch-unlink", task_id, "feat/test", "--actor", "human:test")
        assert result.exit_code == 0
        assert "Unlinked branch" in result.output

        snap = _read_snapshot(initialized_root, task_id)
        assert len(snap["branch_links"]) == 0

    def test_branch_unlink_with_repo(self, invoke, initialized_root: Path) -> None:
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "main", "--repo", "lattice", "--actor", "human:test")

        result = invoke(
            "branch-unlink", task_id, "main", "--repo", "lattice", "--actor", "human:test"
        )
        assert result.exit_code == 0

        snap = _read_snapshot(initialized_root, task_id)
        assert len(snap["branch_links"]) == 0

    def test_branch_unlink_appends_event(self, invoke, initialized_root: Path) -> None:
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "feat/test", "--actor", "human:test")
        invoke("branch-unlink", task_id, "feat/test", "--actor", "human:test")

        events = _read_events(initialized_root, task_id)
        bl_events = [e for e in events if e["type"] == "branch_unlinked"]
        assert len(bl_events) == 1
        assert bl_events[0]["data"]["branch"] == "feat/test"

    def test_branch_unlink_preserves_other_links(self, invoke, initialized_root: Path) -> None:
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "feat/a", "--actor", "human:test")
        invoke("branch-link", task_id, "feat/b", "--actor", "human:test")

        invoke("branch-unlink", task_id, "feat/a", "--actor", "human:test")

        snap = _read_snapshot(initialized_root, task_id)
        assert len(snap["branch_links"]) == 1
        assert snap["branch_links"][0]["branch"] == "feat/b"


class TestBranchUnlinkJsonOutput:
    """--json flag produces structured output for branch-unlink."""

    def test_json_success(self, invoke) -> None:
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "feat/test", "--actor", "human:test")

        result = invoke("branch-unlink", task_id, "feat/test", "--actor", "human:test", "--json")
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["ok"] is True
        assert len(parsed["data"]["branch_links"]) == 0

    def test_json_error_not_found(self, invoke) -> None:
        task_id = _create_task(invoke)
        result = invoke("branch-unlink", task_id, "feat/test", "--actor", "human:test", "--json")
        assert result.exit_code == 1
        parsed = json.loads(result.output)
        assert parsed["ok"] is False
        assert parsed["error"]["code"] == "NOT_FOUND"


class TestBranchUnlinkQuietOutput:
    """--quiet flag prints only the task ID for branch-unlink."""

    def test_quiet_success(self, invoke) -> None:
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "feat/test", "--actor", "human:test")

        result = invoke("branch-unlink", task_id, "feat/test", "--actor", "human:test", "--quiet")
        assert result.exit_code == 0
        assert result.output.strip() == task_id


class TestBranchUnlinkErrors:
    """Error cases for lattice branch-unlink."""

    def test_nonexistent_branch_link(self, invoke) -> None:
        task_id = _create_task(invoke)
        result = invoke("branch-unlink", task_id, "feat/test", "--actor", "human:test")
        assert result.exit_code == 1
        assert "No branch link" in result.stderr

    def test_task_not_found(self, invoke) -> None:
        fake_id = "task_01ZZZZZZZZZZZZZZZZZZZZZZZZ"
        result = invoke("branch-unlink", fake_id, "feat/test", "--actor", "human:test")
        assert result.exit_code == 1
        assert "not found" in result.stderr.lower()

    def test_wrong_repo_not_found(self, invoke) -> None:
        """Unlinking with wrong repo should fail."""
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "main", "--repo", "frontend", "--actor", "human:test")
        result = invoke(
            "branch-unlink", task_id, "main", "--repo", "backend", "--actor", "human:test"
        )
        assert result.exit_code == 1
        assert "No branch link" in result.stderr


# ---------------------------------------------------------------------------
# Event log integrity
# ---------------------------------------------------------------------------


class TestBranchEventLogIntegrity:
    """Verify events are written correctly for branch-link/branch-unlink operations."""

    def test_branch_link_event_not_in_lifecycle_log(self, invoke, initialized_root: Path) -> None:
        """branch_linked events should NOT go to _lifecycle.jsonl."""
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "feat/test", "--actor", "human:test")

        lifecycle_path = initialized_root / LATTICE_DIR / "events" / "_lifecycle.jsonl"
        lifecycle_events = [
            json.loads(line) for line in lifecycle_path.read_text().strip().split("\n") if line
        ]
        for ev in lifecycle_events:
            assert ev["type"] == "task_created"

    def test_event_order_preserved(self, invoke, initialized_root: Path) -> None:
        """Events should appear in the order they were created."""
        task_id = _create_task(invoke)
        invoke("branch-link", task_id, "feat/test", "--actor", "human:test")
        invoke("branch-unlink", task_id, "feat/test", "--actor", "human:test")

        events = _read_events(initialized_root, task_id)
        types = [e["type"] for e in events]
        assert types == ["task_created", "branch_linked", "branch_unlinked"]
