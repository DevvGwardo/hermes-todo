"""In-memory todo store for AI agent task management."""

from __future__ import annotations

import textwrap
from typing import Any, Dict, List, Optional

from .planner import build_todos_from_prompt
from .types import VALID_STATUSES


class TodoStore:
    """
    In-memory todo list. One instance per agent session.

    Items are ordered — list position is priority. Each item has:
      - id: unique string identifier (agent-chosen)
      - content: task description
      - status: pending | in_progress | completed | cancelled
    """

    def __init__(self, auto_clear: bool = True) -> None:
        self._items: List[Dict[str, str]] = []
        self.auto_clear = auto_clear

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
            # Replace mode: new list entirely
            self._items = [self._validate(t) for t in todos]
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
                    validated = self._validate(t)
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

        # Auto-clear when all tasks are completed or cancelled
        if self.auto_clear and self._items and self._all_done():
            self._items.clear()

        return self.read()

    def _all_done(self) -> bool:
        """Check if every item is completed or cancelled (no active work)."""
        return all(item["status"] in ("completed", "cancelled") for item in self._items)

    def read(self) -> List[Dict[str, str]]:
        """Return a copy of the current list."""
        return [item.copy() for item in self._items]

    def has_items(self) -> bool:
        """Check if there are any items in the list."""
        return len(self._items) > 0

    def format_for_injection(self) -> Optional[str]:
        """
        Render the todo list for context injection (e.g. after compression).

        Returns a human-readable string, or None if the list has no
        active (pending/in_progress) items.
        """
        if not self._items:
            return None

        markers = {
            "completed": "[x]",
            "in_progress": "[>]",
            "pending": "[ ]",
            "cancelled": "[~]",
        }

        # Only inject pending/in_progress items — completed/cancelled ones
        # cause the model to re-do finished work after compression.
        active_items = [
            item
            for item in self._items
            if item["status"] in ("pending", "in_progress")
        ]
        if not active_items:
            return None

        lines = ["[Your active task list was preserved across context compression]"]
        for item in active_items:
            marker = markers.get(item["status"], "[?]")
            lines.append(f"- {marker} {item['id']}. {item['content']} ({item['status']})")

        return "\n".join(lines)

    def format_for_cli(self, width: int = 72) -> str:
        """
        Render the full todo list for a terminal-friendly display.

        Unlike format_for_injection(), this includes completed and cancelled
        items because the CLI view is meant for humans, not prompt compression.
        """
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

        pending = sum(1 for item in self._items if item["status"] == "pending")
        in_progress = sum(1 for item in self._items if item["status"] == "in_progress")
        completed = sum(1 for item in self._items if item["status"] == "completed")
        cancelled = sum(1 for item in self._items if item["status"] == "cancelled")

        lines = [
            border("="),
            row("HERMES TODO"),
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
            f"{len(self._items)} tasks | active {in_progress} | pending {pending} | "
            f"done {completed} | cancelled {cancelled}"
        )
        markers = {
            "completed": "[x]",
            "in_progress": "[>]",
            "pending": "[ ]",
            "cancelled": "[~]",
        }

        lines.extend([row(summary), border()])
        for item in self._items:
            prefix = f"{markers.get(item['status'], '[?]')} {item['id']}. "
            lines.extend(wrapped_rows(prefix, item["content"]))
        lines.append(border("="))

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
        return self.write(todos, merge=not replace)

    def clear(self) -> None:
        """Remove all items."""
        self._items.clear()

    @staticmethod
    def _validate(item: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate and normalize a todo item.

        Ensures required fields exist and status is valid.
        Returns a clean dict with only {id, content, status}.
        """
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            item_id = "?"

        content = str(item.get("content", "")).strip()
        if not content:
            content = "(no description)"

        status = str(item.get("status", "pending")).strip().lower()
        if status not in VALID_STATUSES:
            status = "pending"

        return {"id": item_id, "content": content, "status": status}
