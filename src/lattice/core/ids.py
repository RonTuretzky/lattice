"""ULID generation and validation."""

from ulid import ULID


def generate_task_id() -> str:
    """Generate a new task ID with the task_ prefix."""
    return f"task_{ULID()}"


def generate_event_id() -> str:
    """Generate a new event ID with the ev_ prefix."""
    return f"ev_{ULID()}"


def generate_artifact_id() -> str:
    """Generate a new artifact ID with the art_ prefix."""
    return f"art_{ULID()}"
