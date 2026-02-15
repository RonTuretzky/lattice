"""Tests for root discovery logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from lattice.storage.fs import LATTICE_DIR, LatticeRootError, find_root


class TestFindRootWalkUp:
    """find_root() walks up from a starting path to find .lattice/."""

    def test_finds_lattice_in_current_dir(self, tmp_path: Path) -> None:
        (tmp_path / LATTICE_DIR).mkdir()
        result = find_root(start=tmp_path)
        assert result == tmp_path

    def test_finds_lattice_in_parent_dir(self, tmp_path: Path) -> None:
        (tmp_path / LATTICE_DIR).mkdir()
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)

        result = find_root(start=nested)
        assert result == tmp_path

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        # tmp_path has no .lattice/ — walk up should eventually hit root and return None
        # Use a nested dir to avoid accidentally finding a real .lattice/ on the system
        isolated = tmp_path / "isolated"
        isolated.mkdir()
        result = find_root(start=isolated)
        assert result is None


class TestFindRootEnvVar:
    """LATTICE_ROOT env var overrides walk-up discovery."""

    def test_env_var_overrides_walk_up(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Create .lattice/ in the env var target
        env_target = tmp_path / "env_root"
        env_target.mkdir()
        (env_target / LATTICE_DIR).mkdir()

        monkeypatch.setenv("LATTICE_ROOT", str(env_target))

        # Even when starting from a different path, env var wins
        other = tmp_path / "other"
        other.mkdir()
        result = find_root(start=other)
        assert result == env_target

    def test_env_var_nonexistent_path_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LATTICE_ROOT", str(tmp_path / "does_not_exist"))

        with pytest.raises(LatticeRootError, match="does not exist"):
            find_root(start=tmp_path)

    def test_env_var_no_lattice_dir_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Directory exists but has no .lattice/ inside
        env_target = tmp_path / "empty_root"
        env_target.mkdir()

        monkeypatch.setenv("LATTICE_ROOT", str(env_target))

        with pytest.raises(LatticeRootError, match="no .lattice/"):
            find_root(start=tmp_path)

    def test_env_var_invalid_does_not_fall_back(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When LATTICE_ROOT is set but invalid, do NOT fall back to walk-up."""
        # Create .lattice/ that walk-up would find
        (tmp_path / LATTICE_DIR).mkdir()

        # But set env var to a bad path
        monkeypatch.setenv("LATTICE_ROOT", str(tmp_path / "bad"))

        with pytest.raises(LatticeRootError):
            find_root(start=tmp_path)

    def test_env_var_empty_string_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty LATTICE_ROOT is an error, not a silent cwd fallback."""
        monkeypatch.setenv("LATTICE_ROOT", "")

        with pytest.raises(LatticeRootError, match="empty"):
            find_root(start=tmp_path)
