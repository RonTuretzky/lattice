"""Tests for core config module."""

from __future__ import annotations

import json

from lattice.core.config import default_config, serialize_config


class TestDefaultConfig:
    """default_config() returns a well-formed configuration dict."""

    def test_has_schema_version(self) -> None:
        config = default_config()
        assert config["schema_version"] == 1

    def test_has_default_status(self) -> None:
        config = default_config()
        assert config["default_status"] == "backlog"

    def test_has_default_priority(self) -> None:
        config = default_config()
        assert config["default_priority"] == "medium"

    def test_has_task_types(self) -> None:
        config = default_config()
        assert config["task_types"] == ["task", "epic", "bug", "spike", "chore"]

    def test_workflow_statuses(self) -> None:
        config = default_config()
        expected = ["backlog", "ready", "in_progress", "review", "done", "blocked", "cancelled"]
        assert config["workflow"]["statuses"] == expected

    def test_workflow_transitions_keys(self) -> None:
        config = default_config()
        transitions = config["workflow"]["transitions"]
        expected_keys = {
            "backlog",
            "ready",
            "in_progress",
            "review",
            "done",
            "cancelled",
            "blocked",
        }
        assert set(transitions.keys()) == expected_keys

    def test_terminal_statuses_have_no_transitions(self) -> None:
        config = default_config()
        transitions = config["workflow"]["transitions"]
        assert transitions["done"] == []
        assert transitions["cancelled"] == []

    def test_wip_limits(self) -> None:
        config = default_config()
        wip = config["workflow"]["wip_limits"]
        assert wip == {"in_progress": 10, "review": 5}


class TestSerializeConfig:
    """serialize_config() produces deterministic canonical JSON."""

    def test_sorted_keys(self) -> None:
        config = default_config()
        serialized = serialize_config(config)
        parsed = json.loads(serialized)
        # Re-serialize with sort_keys to verify roundtrip
        reserialized = json.dumps(parsed, sort_keys=True, indent=2) + "\n"
        assert serialized == reserialized

    def test_trailing_newline(self) -> None:
        config = default_config()
        serialized = serialize_config(config)
        assert serialized.endswith("\n")
        assert not serialized.endswith("\n\n")

    def test_two_space_indent(self) -> None:
        config = default_config()
        serialized = serialize_config(config)
        # Second line should start with exactly 2 spaces (first key)
        lines = serialized.split("\n")
        assert lines[1].startswith("  ")
        assert not lines[1].startswith("    ")

    def test_roundtrip(self) -> None:
        config = default_config()
        serialized = serialize_config(config)
        parsed = json.loads(serialized)
        assert parsed == config
