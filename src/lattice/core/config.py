"""Default config generation and validation."""


def default_config() -> dict:
    """Return the default Lattice configuration.

    The returned dict, when serialized with
    ``json.dumps(data, sort_keys=True, indent=2) + "\\n"``,
    produces the canonical default config.json.
    """
    return {
        "schema_version": 1,
        "default_status": "backlog",
        "default_priority": "medium",
        "task_types": [
            "task",
            "epic",
            "bug",
            "spike",
            "chore",
        ],
        "workflow": {
            "statuses": [
                "backlog",
                "ready",
                "in_progress",
                "review",
                "done",
                "blocked",
                "cancelled",
            ],
            "transitions": {
                "backlog": ["ready", "cancelled"],
                "ready": ["in_progress", "blocked", "cancelled"],
                "in_progress": ["review", "blocked", "cancelled"],
                "review": ["done", "in_progress", "cancelled"],
                "done": [],
                "cancelled": [],
                "blocked": ["ready", "in_progress", "cancelled"],
            },
            "wip_limits": {
                "in_progress": 10,
                "review": 5,
            },
        },
    }


def serialize_config(config: dict) -> str:
    """Serialize a config dict to the canonical JSON format."""
    import json

    return json.dumps(config, sort_keys=True, indent=2) + "\n"
