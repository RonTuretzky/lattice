"""CLI entry point and commands."""

from __future__ import annotations

from pathlib import Path

import click

from lattice.core.config import default_config, serialize_config
from lattice.storage.fs import LATTICE_DIR, atomic_write, ensure_lattice_dirs


@click.group()
def cli() -> None:
    """Lattice: file-based, agent-native task tracker."""


@cli.command()
@click.option(
    "--path",
    "target_path",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    default=".",
    help="Directory to initialize Lattice in (defaults to current directory).",
)
def init(target_path: str) -> None:
    """Initialize a new Lattice project."""
    root = Path(target_path)
    lattice_dir = root / LATTICE_DIR

    # Idempotency: if .lattice/ already exists, exit without touching anything
    if lattice_dir.is_dir():
        click.echo(f"Lattice already initialized in {LATTICE_DIR}/")
        return

    # Create directory structure
    ensure_lattice_dirs(root)

    # Write default config atomically
    config = default_config()
    config_content = serialize_config(config)
    atomic_write(lattice_dir / "config.json", config_content)

    click.echo(f"Initialized empty Lattice in {LATTICE_DIR}/")


if __name__ == "__main__":
    cli()
