"""Types and constants for the todo tool."""

from __future__ import annotations

from typing import Dict, List, Literal, TypedDict


# Valid status values for todo items
VALID_STATUSES = {"pending", "in_progress", "completed", "cancelled"}

TodoStatus = Literal["pending", "in_progress", "completed", "cancelled"]


class TodoItem(TypedDict):
    """A single todo item with id, content, and status."""

    id: str
    content: str
    status: TodoStatus


# Shared marker mapping for rendering (CLI and injection)
STATUS_MARKERS: Dict[str, str] = {
    "completed": "[x]",
    "in_progress": "[>]",
    "pending": "[ ]",
    "cancelled": "[~]",
}


def count_by_status(items: List[Dict[str, str]]) -> Dict[str, int]:
    """Count items by status, returning a dict with all four status keys."""
    counts: Dict[str, int] = {s: 0 for s in VALID_STATUSES}
    for item in items:
        status = item.get("status", "pending")
        if status in counts:
            counts[status] += 1
    return counts
