"""Tests for atomic write operations."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lattice.storage.fs import atomic_write


class TestAtomicWrite:
    """atomic_write() writes content safely via temp + fsync + rename."""

    def test_writes_expected_content(self, tmp_path: Path) -> None:
        target = tmp_path / "output.json"
        atomic_write(target, '{"key": "value"}\n')

        assert target.read_text() == '{"key": "value"}\n'

    def test_writes_bytes_content(self, tmp_path: Path) -> None:
        target = tmp_path / "output.bin"
        data = b"\x00\x01\x02\x03"
        atomic_write(target, data)

        assert target.read_bytes() == data

    def test_no_temp_file_left_after_success(self, tmp_path: Path) -> None:
        target = tmp_path / "output.json"
        atomic_write(target, "content\n")

        # Only the target file should exist
        files = list(tmp_path.iterdir())
        assert files == [target]

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "output.json"
        target.write_text("old content\n")

        atomic_write(target, "new content\n")
        assert target.read_text() == "new content\n"

    def test_parent_directory_must_exist(self, tmp_path: Path) -> None:
        target = tmp_path / "nonexistent" / "output.json"

        with pytest.raises(FileNotFoundError, match="Parent directory does not exist"):
            atomic_write(target, "content\n")

    def test_file_permissions_are_readable(self, tmp_path: Path) -> None:
        target = tmp_path / "output.json"
        atomic_write(target, "content\n")

        # File should be readable
        assert os.access(target, os.R_OK)
