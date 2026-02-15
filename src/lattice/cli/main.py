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

    # Idempotency: if .lattice/ already exists as a directory, skip
    if lattice_dir.is_dir():
        click.echo(f"Lattice already initialized in {LATTICE_DIR}/")
        return

    # Fail clearly if .lattice exists as a file (not a directory)
    if lattice_dir.exists():
        raise click.ClickException(
            f"Cannot initialize: '{LATTICE_DIR}' exists but is not a directory. "
            "Remove it and try again."
        )

    try:
        # Create directory structure
        ensure_lattice_dirs(root)

        # Write default config atomically
        config = default_config()
        config_content = serialize_config(config)
        atomic_write(lattice_dir / "config.json", config_content)
    except PermissionError:
        raise click.ClickException(
            f"Permission denied: cannot create {LATTICE_DIR}/ in {root}"
        )
    except OSError as e:
        raise click.ClickException(f"Failed to initialize Lattice: {e}")

    click.echo(f"Initialized empty Lattice in {LATTICE_DIR}/")


if __name__ == "__main__":
    cli()
