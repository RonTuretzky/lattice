"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def lattice_root(tmp_path: Path) -> Path:
    """Return a temporary directory suitable for initializing .lattice/ in."""
    return tmp_path


@pytest.fixture()
def initialized_root(lattice_root: Path) -> Path:
    """Return a temporary directory with .lattice/ already initialized."""
    from lattice.storage.fs import ensure_lattice_dirs, atomic_write, LATTICE_DIR
    from lattice.core.config import default_config, serialize_config

    ensure_lattice_dirs(lattice_root)
    lattice_dir = lattice_root / LATTICE_DIR
    atomic_write(lattice_dir / "config.json", serialize_config(default_config()))
    (lattice_dir / "events" / "_global.jsonl").touch()
    return lattice_root
