"""Statistics and insight commands."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import click

from lattice.cli.helpers import json_envelope, load_project_config, require_root
from lattice.cli.main import cli


def _load_all_snapshots(lattice_dir: Path) -> tuple[list[dict], list[dict]]:
    """Load all active and archived task snapshots.

    Returns (active, archived) lists.
    """
    active: list[dict] = []
    archived: list[dict] = []

    tasks_dir = lattice_dir / "tasks"
    if tasks_dir.is_dir():
        for f in tasks_dir.glob("*.json"):
            try:
                active.append(json.loads(f.read_text()))
            except (json.JSONDecodeError, OSError):
                continue

    archive_dir = lattice_dir / "archive" / "tasks"
    if archive_dir.is_dir():
        for f in archive_dir.glob("*.json"):
            try:
                archived.append(json.loads(f.read_text()))
            except (json.JSONDecodeError, OSError):
                continue

    return active, archived


def _count_events(lattice_dir: Path, archived: bool = False) -> tuple[int, Counter]:
    """Count total events and events per task.

    Returns (total_events, per_task_counter).
    """
    if archived:
        events_dir = lattice_dir / "archive" / "events"
    else:
        events_dir = lattice_dir / "events"

    total = 0
    per_task: Counter = Counter()

    if not events_dir.is_dir():
        return total, per_task

    for f in events_dir.glob("*.jsonl"):
        if f.name.startswith("_"):
            continue  # skip _lifecycle.jsonl
        task_id = f.stem
        count = 0
        for line in f.read_text().splitlines():
            if line.strip():
                count += 1
        total += count
        per_task[task_id] = count

    return total, per_task


def _parse_ts(ts_str: str) -> datetime | None:
    """Parse an RFC 3339 timestamp string."""
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _days_ago(ts_str: str, now: datetime) -> float | None:
    """Return how many days ago a timestamp was."""
    dt = _parse_ts(ts_str)
    if dt is None:
        return None
    delta = now - dt
    return delta.total_seconds() / 86400


def _format_days(days: float) -> str:
    """Format a day count as a human string."""
    if days < 1:
        hours = days * 24
        if hours < 1:
            return f"{int(hours * 60)}m"
        return f"{hours:.0f}h"
    if days < 30:
        return f"{days:.0f}d"
    return f"{days / 30:.1f}mo"


def _build_stats(lattice_dir: Path, config: dict) -> dict:
    """Build the full stats data structure."""
    now = datetime.now(timezone.utc)
    active, archived = _load_all_snapshots(lattice_dir)

    # Event counts
    active_events, active_per_task = _count_events(lattice_dir, archived=False)
    archived_events, _ = _count_events(lattice_dir, archived=True)

    # --- Distributions (active tasks only) ---
    status_counts: Counter = Counter()
    priority_counts: Counter = Counter()
    type_counts: Counter = Counter()
    assignee_counts: Counter = Counter()
    tag_counts: Counter = Counter()

    for snap in active:
        status_counts[snap.get("status", "unknown")] += 1
        priority_counts[snap.get("priority", "unset")] += 1
        type_counts[snap.get("type", "unset")] += 1
        assignee_counts[snap.get("assigned_to") or "unassigned"] += 1
        for tag in snap.get("tags") or []:
            tag_counts[tag] += 1

    # --- Staleness (active tasks only) ---
    stale: list[dict] = []  # tasks not updated in 7+ days
    recently_active: list[dict] = []

    for snap in active:
        updated_at = snap.get("updated_at", "")
        days = _days_ago(updated_at, now)
        if days is not None and days >= 7:
            stale.append({
                "id": snap.get("short_id") or snap.get("id", "?"),
                "title": snap.get("title", "?"),
                "status": snap.get("status", "?"),
                "days_stale": round(days, 1),
            })

    # Sort stale by stalest first
    stale.sort(key=lambda s: s["days_stale"], reverse=True)

    # Recently active: 5 most recently updated
    active_sorted = sorted(
        active,
        key=lambda s: s.get("updated_at", ""),
        reverse=True,
    )
    for snap in active_sorted[:5]:
        days = _days_ago(snap.get("updated_at", ""), now)
        recently_active.append({
            "id": snap.get("short_id") or snap.get("id", "?"),
            "title": snap.get("title", "?"),
            "status": snap.get("status", "?"),
            "updated_ago": _format_days(days) if days is not None else "?",
        })

    # --- Busiest tasks (by event count) ---
    busiest: list[dict] = []
    for task_id, count in active_per_task.most_common(5):
        # Look up title from active snapshots
        title = "?"
        short_id = None
        for snap in active:
            if snap.get("id") == task_id:
                title = snap.get("title", "?")
                short_id = snap.get("short_id")
                break
        busiest.append({
            "id": short_id or task_id,
            "title": title,
            "event_count": count,
        })

    # --- Workflow config info ---
    workflow = config.get("workflow", {})
    wip_limits = workflow.get("wip_limits", {})
    wip_status: list[dict] = []
    for status_name, limit in wip_limits.items():
        current = status_counts.get(status_name, 0)
        wip_status.append({
            "status": status_name,
            "current": current,
            "limit": limit,
            "over": current > limit,
        })

    # Order status counts by workflow order
    defined_statuses = workflow.get("statuses", [])
    ordered_status: list[tuple[str, int]] = []
    for s in defined_statuses:
        if status_counts[s] > 0:
            ordered_status.append((s, status_counts[s]))
    # Add any statuses not in workflow (shouldn't happen, but safety)
    for s, c in status_counts.items():
        if s not in defined_statuses and c > 0:
            ordered_status.append((s, c))

    return {
        "summary": {
            "active_tasks": len(active),
            "archived_tasks": len(archived),
            "total_tasks": len(active) + len(archived),
            "total_events": active_events + archived_events,
            "active_events": active_events,
        },
        "by_status": ordered_status,
        "by_priority": priority_counts.most_common(),
        "by_type": type_counts.most_common(),
        "by_assignee": assignee_counts.most_common(),
        "by_tag": tag_counts.most_common(),
        "wip": wip_status,
        "recently_active": recently_active,
        "stale": stale,
        "busiest": busiest,
    }


# ---------------------------------------------------------------------------
# Human-readable output
# ---------------------------------------------------------------------------


def _bar(count: int, total: int, width: int = 20) -> str:
    """Render a proportional bar."""
    if total == 0:
        return ""
    filled = round(count / total * width)
    return "#" * filled + "." * (width - filled)


def _print_human_stats(stats: dict, config: dict) -> None:
    """Print stats as a human-readable dashboard."""
    s = stats["summary"]
    project_code = config.get("project_code", "")
    instance_name = config.get("instance_name", "")
    header = instance_name or project_code or "Lattice"

    click.echo(f"=== {header} Stats ===")
    click.echo("")
    click.echo(
        f"Tasks: {s['active_tasks']} active, "
        f"{s['archived_tasks']} archived "
        f"({s['total_tasks']} total)"
    )
    click.echo(f"Events: {s['total_events']} total ({s['active_events']} on active tasks)")
    click.echo("")

    # Status
    if stats["by_status"]:
        click.echo("Status:")
        total = s["active_tasks"]
        for status, count in stats["by_status"]:
            bar = _bar(count, total)
            click.echo(f"  {status:<20s} {count:>3d}  {bar}")
        click.echo("")

    # WIP limits
    wip_alerts = [w for w in stats["wip"] if w["over"]]
    if wip_alerts:
        click.echo("WIP Limit Exceeded:")
        for w in wip_alerts:
            click.echo(
                f"  {w['status']}: {w['current']}/{w['limit']}"
            )
        click.echo("")

    # Priority
    if stats["by_priority"]:
        click.echo("Priority:")
        for priority, count in stats["by_priority"]:
            click.echo(f"  {priority:<12s} {count:>3d}")
        click.echo("")

    # Type
    if stats["by_type"]:
        click.echo("Type:")
        for task_type, count in stats["by_type"]:
            click.echo(f"  {task_type:<12s} {count:>3d}")
        click.echo("")

    # Assignees
    if stats["by_assignee"]:
        click.echo("Assigned:")
        for assignee, count in stats["by_assignee"]:
            click.echo(f"  {assignee:<30s} {count:>3d}")
        click.echo("")

    # Tags
    if stats["by_tag"]:
        click.echo("Tags:")
        for tag, count in stats["by_tag"]:
            click.echo(f"  {tag:<20s} {count:>3d}")
        click.echo("")

    # Recently active
    if stats["recently_active"]:
        click.echo("Recently Active:")
        for t in stats["recently_active"]:
            click.echo(
                f"  {t['id']:<10s} {t['status']:<20s} {t['updated_ago']:>5s} ago  "
                f"\"{t['title']}\""
            )
        click.echo("")

    # Stale
    if stats["stale"]:
        click.echo(f"Stale (7+ days idle): {len(stats['stale'])} tasks")
        for t in stats["stale"][:10]:  # cap display at 10
            click.echo(
                f"  {t['id']:<10s} {t['status']:<20s} {_format_days(t['days_stale']):>5s}  "
                f"\"{t['title']}\""
            )
        if len(stats["stale"]) > 10:
            click.echo(f"  ... and {len(stats['stale']) - 10} more")
        click.echo("")

    # Busiest tasks
    if stats["busiest"]:
        click.echo("Most Active (by event count):")
        for t in stats["busiest"]:
            click.echo(
                f"  {t['id']:<10s} {t['event_count']:>4d} events  \"{t['title']}\""
            )


# ---------------------------------------------------------------------------
# lattice stats
# ---------------------------------------------------------------------------


@cli.command("stats")
@click.option("--json", "output_json", is_flag=True, help="Output structured JSON.")
def stats_cmd(output_json: bool) -> None:
    """Show project statistics and insights."""
    is_json = output_json

    lattice_dir = require_root(is_json)
    config = load_project_config(lattice_dir)

    stats = _build_stats(lattice_dir, config)

    if is_json:
        click.echo(json_envelope(True, data=stats))
    else:
        _print_human_stats(stats, config)
