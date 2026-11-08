"""In-memory todo store for AI agent task management."""

from __future__ import annotations

import textwrap
import warnings
from typing import Any, Dict, List, Optional

from .planner import build_todos_from_prompt
from .types import STATUS_MARKERS, VALID_STATUSES, count_by_status

# Terminal statuses — items in these states are considered done
DONE_STATUSES = {"completed", "cancelled"}
# Active statuses — items still needing work
ACTIVE_STATUSES = {"pending", "in_progress"}

HEADER_TITLE = "HERMES TODO"


def validate_todo_item(item: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate and normalize a todo item.

    Ensures required fields exist and status is valid.
    Returns a clean dict with only {id, content, status}.
    """
    item_id = str(item.get("id", "")).strip()
    if not item_id:
        item_id = "?"

    content = item.get("content")
    if content is None:
        content = ""
    else:
        content = str(content).strip()
    if not content:
        content = "(no description)"

    status = str(item.get("status", "pending")).strip().lower()
    if status not in VALID_STATUSES:
        status = "pending"

    return {"id": item_id, "content": content, "status": status}


class TodoStore:
    """
    In-memory todo list. One instance per agent session.

    Items are ordered — list position is priority. Each item has:
      - id: unique string identifier (agent-chosen)
      - content: task description
      - status: pending | in_progress | completed | cancelled
    """

    def __init__(self, auto_clear: bool = True, max_items: Optional[int] = None) -> None:
        self._items: List[Dict[str, str]] = []
        self.auto_clear = auto_clear
        self.max_items = max_items
        self._warned_exceeded = False

    def write(
        self, todos: List[Dict[str, Any]], merge: bool = False
    ) -> List[Dict[str, str]]:
        """
        Write todos. Returns the full current list after writing.

        Args:
            todos: list of {id, content, status} dicts
            merge: if False, replace the entire list. If True, update
                   existing items by id and append new ones.
        """
        if not merge:
            # Replace mode: new list entirely (dedup keeps last occurrence of each id)
            self._items = [validate_todo_item(t) for t in self._dedupe_by_id(todos)]
        else:
            # Merge mode: update existing items by id, append new ones
            existing = {item["id"]: item for item in self._items}
            for t in todos:
                item_id = str(t.get("id", "")).strip()
                if not item_id:
                    continue  # Can't merge without an id

                if item_id in existing:
                    # Update only the fields the LLM actually provided
                    if "content" in t and t["content"]:
                        existing[item_id]["content"] = str(t["content"]).strip()
                    if "status" in t and t["status"]:
                        status = str(t["status"]).strip().lower()
                        if status in VALID_STATUSES:
                            existing[item_id]["status"] = status
                else:
                    # New item — validate fully and append to end
                    validated = validate_todo_item(t)
                    existing[validated["id"]] = validated
                    self._items.append(validated)
            # Rebuild _items preserving order for existing items
            seen: set[str] = set()
            rebuilt: List[Dict[str, str]] = []
            for item in self._items:
                current = existing.get(item["id"], item)
                if current["id"] not in seen:
                    rebuilt.append(current)
                    seen.add(current["id"])
            self._items = rebuilt

        # Warn when write would exceed max_items (one-time per instance)
        if self.max_items is not None and len(self._items) > self.max_items and not self._warned_exceeded:
            warnings.warn(
                f"TodoStore has {len(self._items)} items, "
                f"which exceeds max_items={self.max_items}"
            )
            self._warned_exceeded = True

        # Auto-clear when all tasks are completed or cancelled
        if self.auto_clear and self._items and self._all_done():
            self._items.clear()

        return self.read()

    def _all_done(self) -> bool:
        """Check if every item is completed or cancelled (no active work)."""
        return all(item["status"] in DONE_STATUSES for item in self._items)

    def read(self) -> List[Dict[str, str]]:
        """Return a copy of the current list."""
        return [item.copy() for item in self._items]

    def has_items(self) -> bool:
        """Check if there are any items in the list."""
        return len(self._items) > 0

    def get_by_id(self, id: str) -> Optional[Dict[str, str]]:
        """Return a single item by id, or None if not found."""
        for item in self._items:
            if item["id"] == id:
                return item.copy()
        return None

    def filter_by_status(self, status: str) -> List[Dict[str, str]]:
        """Return a copy of items matching the given status."""
        return [item.copy() for item in self._items if item["status"] == status]

    def format_for_injection(self) -> Optional[str]:
        """
        Render the todo list for context injection (e.g. after compression).

        Returns a human-readable string, or None if the list has no
        active (pending/in_progress) items.
        """
        if not self._items:
            return None

        # Only inject pending/in_progress items — completed/cancelled ones
        # cause the model to re-do finished work after compression.
        active_items = [
            item
            for item in self._items
            if item["status"] in ACTIVE_STATUSES
        ]
        if not active_items:
            return None

        lines = ["[Your active task list was preserved across context compression]"]
        for item in active_items:
            marker = STATUS_MARKERS.get(item["status"], "[?]")
            lines.append(f"- {marker} {item['id']}. {item['content']} ({item['status']})")

        return "\n".join(lines)

    def format_for_cli(self, width: int = 72, compact: bool = False) -> str:
        """
        Render the full todo list for a terminal-friendly display.

        Unlike format_for_injection(), this includes completed and cancelled
        items because the CLI view is meant for humans, not prompt compression.

        When compact=True, renders a simpler unicode-glyph format instead of
        the boxed ASCII-art format.
        """
        if compact:
            return self._format_compact()
        return self._format_boxed(width)

    def _format_boxed(self, width: int = 72) -> str:
        width = max(48, min(width, 120))
        inner_width = width - 4

        def border(char: str = "-") -> str:
            return f"+{char * (width - 2)}+"

        def row(text: str = "") -> str:
            return f"| {text.ljust(inner_width)} |"

        def wrapped_rows(prefix: str, content: str) -> List[str]:
            wrap_width = max(12, inner_width - len(prefix))
            chunks = textwrap.wrap(
                content,
                width=wrap_width,
                break_long_words=False,
                break_on_hyphens=False,
            ) or [""]
            rows = [row(f"{prefix}{chunks[0]}")]
            indent = " " * len(prefix)
            for chunk in chunks[1:]:
                rows.append(row(f"{indent}{chunk}"))
            return rows

        counts = count_by_status(self._items)

        lines = [
            border("="),
            row(HEADER_TITLE),
        ]

        if not self._items:
            lines.extend(
                [
                    border(),
                    row("No tasks yet."),
                    row("Call todo_tool(prompt=...) or seed_from_prompt(...) to launch one."),
                    border("="),
                ]
            )
            return "\n".join(lines)

        summary = (
            f"{len(self._items)} tasks | active {counts['in_progress']} | "
            f"pending {counts['pending']} | done {counts['completed']} | "
            f"cancelled {counts['cancelled']}"
        )

        lines.extend([row(summary), border()])
        for item in self._items:
            prefix = f"{STATUS_MARKERS.get(item['status'], '[?]')} {item['id']}. "
            lines.extend(wrapped_rows(prefix, item["content"]))
        lines.append(border("="))

        return "\n".join(lines)

    def _format_compact(self) -> str:
        """Render the task list in a compact unicode-glyph format."""
        counts = count_by_status(self._items)
        total = len(self._items)
        done = counts["completed"] + counts["cancelled"]
        header = f"\U0001f4cb Todo ({done}/{total} done)"
        if counts["cancelled"]:
            header += f", {counts['cancelled']} cancelled"
        lines = [header]
        for item in self._items:
            marker = STATUS_MARKERS.get(item["status"], "[?]")
            lines.append(f"  {marker} {item['id']}. {item['content']}")
        return "\n".join(lines)

    def seed_from_prompt(
        self,
        prompt: str,
        min_tasks: int = 2,
        activate_first: bool = True,
        replace: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Build a todo list from a raw user prompt and write it to the store.

        Returns the current list unchanged when the prompt does not contain
        enough distinct tasks to meet the threshold.
        """
        todos = build_todos_from_prompt(
            prompt,
            min_tasks=min_tasks,
            activate_first=activate_first,
        )
        if not todos:
            return self.read()

        if not replace:
            # Avoid ID collisions with existing items when merging
            existing_ids = {item["id"] for item in self._items}
            offset = len(self._items)
            for i, todo in enumerate(todos):
                new_id = str(offset + i + 1)
                # If the new ID still collides (existing IDs were non-numeric),
                # keep incrementing until we find a free one.
                while new_id in existing_ids:
                    offset += 1
                    new_id = str(offset + i + 1)
                todo["id"] = new_id
                existing_ids.add(new_id)

        return self.write(todos, merge=not replace)

    def clear(self) -> None:
        """Remove all items."""
        self._items.clear()

    @staticmethod
    def _dedupe_by_id(todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collapse duplicate ids, keeping the last occurrence in its position."""
        last_index: Dict[str, int] = {}
        for i, item in enumerate(todos):
            item_id = str(item.get("id", "")).strip() or "?"
            last_index[item_id] = i
        return [todos[i] for i in sorted(last_index.values())]
