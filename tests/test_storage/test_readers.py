"""Tests for lattice.storage.readers — shared event reading helpers."""

from __future__ import annotations

import json
from pathlib import Path

from lattice.storage.readers import read_task_events


class TestReadTaskEvents:
    def test_reads_valid_events(self, tmp_path: Path) -> None:
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        event = {"id": "ev_1", "type": "task_created", "ts": "2026-01-01T00:00:00Z"}
        (events_dir / "task_X.jsonl").write_text(json.dumps(event) + "\n")

        result = read_task_events(tmp_path, "task_X")
        assert len(result) == 1
        assert result[0]["id"] == "ev_1"

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        result = read_task_events(tmp_path, "task_MISSING")
        assert result == []

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        (events_dir / "task_X.jsonl").write_text("")
        result = read_task_events(tmp_path, "task_X")
        assert result == []

    def test_malformed_line_skipped(self, tmp_path: Path) -> None:
        """A JSONL file with one valid and one corrupt line should return only the valid event."""
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        valid = json.dumps({"id": "ev_1", "type": "task_created"})
        (events_dir / "task_X.jsonl").write_text(f"{valid}\n{{CORRUPT\n")

        result = read_task_events(tmp_path, "task_X")
        assert len(result) == 1
        assert result[0]["id"] == "ev_1"

    def test_blank_lines_skipped(self, tmp_path: Path) -> None:
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        valid = json.dumps({"id": "ev_1", "type": "task_created"})
        (events_dir / "task_X.jsonl").write_text(f"\n{valid}\n\n\n")

        result = read_task_events(tmp_path, "task_X")
        assert len(result) == 1

    def test_archived_events(self, tmp_path: Path) -> None:
        archive_dir = tmp_path / "archive" / "events"
        archive_dir.mkdir(parents=True)
        event = {"id": "ev_arch", "type": "task_created"}
        (archive_dir / "task_X.jsonl").write_text(json.dumps(event) + "\n")

        result = read_task_events(tmp_path, "task_X", is_archived=True)
        assert len(result) == 1
        assert result[0]["id"] == "ev_arch"

    def test_multiple_events_in_order(self, tmp_path: Path) -> None:
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        lines = []
        for i in range(5):
            lines.append(json.dumps({"id": f"ev_{i}", "type": "task_created"}))
        (events_dir / "task_X.jsonl").write_text("\n".join(lines) + "\n")

        result = read_task_events(tmp_path, "task_X")
        assert len(result) == 5
        assert [e["id"] for e in result] == [f"ev_{i}" for i in range(5)]
