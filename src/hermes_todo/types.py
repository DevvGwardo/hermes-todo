"""Types and constants for the todo tool."""

from typing import Literal

# Valid status values for todo items
VALID_STATUSES = {"pending", "in_progress", "completed", "cancelled"}

TodoStatus = Literal["pending", "in_progress", "completed", "cancelled"]
