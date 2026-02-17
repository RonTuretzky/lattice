"""``lattice dashboard`` command — launch the read-only web UI."""

from __future__ import annotations

import errno
import socket
import sys

import click

from lattice.cli.helpers import json_envelope, json_error_obj, require_root
from lattice.cli.main import cli

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _find_free_port(host: str, near: int) -> int | None:
    """Return an available port close to *near*, or ``None`` on failure."""
    for candidate in range(near + 1, near + 20):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, candidate))
                return candidate
        except OSError:
            continue
    return None


@cli.command("dashboard")
@click.option("--host", default="127.0.0.1", help="Host to bind to.")
@click.option("--port", default=8799, type=int, help="Port to bind to.")
@click.option("--json", "output_json", is_flag=True, help="Output structured JSON.")
def dashboard_cmd(host: str, port: int, output_json: bool) -> None:
    """Launch a read-only local web dashboard."""
    lattice_dir = require_root(output_json)

    # Non-loopback binds are forced into read-only mode
    readonly = host not in _LOOPBACK_HOSTS
    if readonly:
        click.echo(
            "Warning: dashboard is exposed on the network — writes are disabled. "
            "Bind to 127.0.0.1 for local-only access with full write support.",
            err=True,
        )

    from lattice.dashboard.server import create_server

    try:
        server = create_server(lattice_dir, host, port, readonly=readonly)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            alt = _find_free_port(host, port)
            hint = (
                f"  lattice dashboard --port {alt}"
                if alt
                else "  lattice dashboard --port <PORT>"
            )
            msg = (
                f"Port {port} is already in use — is another dashboard running?\n"
                f"You can stop the other process, or start on a free port:\n\n"
                f"{hint}"
            )
            code = "PORT_IN_USE"
        else:
            msg = str(exc)
            code = "BIND_ERROR"
        if output_json:
            click.echo(json_envelope(False, error=json_error_obj(code, msg)))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    url = f"http://{host}:{port}/"

    if output_json:
        click.echo(json_envelope(True, data={"host": host, "port": port, "url": url}))
    else:
        click.echo(f"Lattice dashboard: {url}")
        click.echo("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        server.server_close()
