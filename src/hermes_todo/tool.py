"""todo_tool function and OpenAI function-calling schema."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .planner import build_todos_from_tasks, extract_tasks
from .store import TodoStore


def todo_cli_from_result(result: str) -> Optional[str]:
    """
    Extract the terminal-ready task list from a ``todo_tool`` JSON result.

    This is the integration point a host CLI should use if it wants to
    render the full task list after the tool runs. Returns ``None`` when the
    payload is invalid JSON or does not include a CLI block.
    """
    try:
        payload = json.loads(result)
    except (TypeError, json.JSONDecodeError):
        return None

    cli = payload.get("cli")
    return cli if isinstance(cli, str) and cli else None


def todo_tool(
    todos: Optional[List[Dict[str, Any]]] = None,
    prompt: Optional[str] = None,
    min_tasks: int = 2,
    merge: bool = False,
    store: Optional[TodoStore] = None,
) -> str:
    """
    Single entry point for the todo tool. Reads or writes depending on params.

    Args:
        todos: if provided, write these items. If None, read current list.
        prompt: optional raw user prompt. When supplied without todos, the
            tool extracts tasks and auto-launches a list if it finds
            at least ``min_tasks`` distinct tasks.
        min_tasks: threshold for prompt-triggered auto-launch.
        merge: if True, update by id. If False (default), replace entire list.
        store: the TodoStore instance (required).

    Returns:
        JSON string with the full current list and summary metadata.
        When all tasks are completed/cancelled and auto_clear is enabled,
        returns an empty list with a "done" flag.
    """
    if store is None:
        return json.dumps({"error": "TodoStore not initialized"}, ensure_ascii=False)

    had_items_before = store.has_items()
    prompt_tasks: List[str] = []
    launched_from_prompt = False

    if todos is not None:
        items = store.write(todos, merge)
    elif prompt is not None:
        prompt_tasks = extract_tasks(prompt)
        if len(prompt_tasks) >= max(1, min_tasks):
            items = store.write(build_todos_from_tasks(prompt_tasks), merge=False)
            launched_from_prompt = True
        else:
            items = store.read()
    else:
        items = store.read()

    # Detect auto-clear: had items before, now empty after a write
    auto_cleared = had_items_before and not items and todos is not None

    pending = sum(1 for i in items if i["status"] == "pending")
    in_progress = sum(1 for i in items if i["status"] == "in_progress")
    completed = sum(1 for i in items if i["status"] == "completed")
    cancelled = sum(1 for i in items if i["status"] == "cancelled")

    result = {
        "todos": items,
        "summary": {
            "total": len(items),
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "cancelled": cancelled,
        },
        "cli": store.format_for_cli(),
        "injection": store.format_for_injection(),
    }

    if prompt is not None:
        result["prompt_analysis"] = {
            "task_count": len(prompt_tasks),
            "launch_threshold": max(1, min_tasks),
            "launched": launched_from_prompt,
        }

    if auto_cleared:
        result["done"] = True

    return json.dumps(result, ensure_ascii=False)


# =============================================================================
# OpenAI Function-Calling Schema
# =============================================================================
# Behavioral guidance is baked into the description so it's part of the
# static tool schema (cached, never changes mid-conversation).

TODO_SCHEMA: Dict[str, Any] = {
    "name": "todo",
    "description": (
        "Manage your task list for the current session. Use for complex tasks "
        "with 2+ distinct tasks or steps. Call with no parameters to read the "
        "current list. Fastest path: pass the raw user request as 'prompt' and "
        "this tool will auto-launch a todo list whenever it detects at least "
        "two tasks.\n\n"
        "Writing:\n"
        "- Provide 'prompt' to auto-create a fresh list from the user request\n"
        "- Provide 'todos' array to create/update items\n"
        "- merge=false (default): replace the entire list with a fresh plan\n"
        "- merge=true: update existing items by id, add any new ones\n"
        "- 'min_tasks' controls how many detected tasks are required before "
        "prompt auto-launch triggers (default 2)\n\n"
        "Each item: {id: string, content: string, "
        "status: pending|in_progress|completed|cancelled}\n"
        "List order is priority. Only ONE item in_progress at a time.\n"
        "Mark items completed immediately when done. If something fails, "
        "cancel it and add a revised item.\n\n"
        "Always returns the full current list plus CLI-ready rendering."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": (
                    "Raw user request. Use this to auto-create a todo list from "
                    "the prompt when it contains multiple tasks."
                ),
            },
            "todos": {
                "type": "array",
                "description": "Task items to write. Omit to read current list.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique item identifier",
                        },
                        "content": {
                            "type": "string",
                            "description": "Task description",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"],
                            "description": "Current status",
                        },
                    },
                    "required": ["id", "content", "status"],
                },
            },
            "min_tasks": {
                "type": "integer",
                "description": (
                    "Minimum number of detected tasks required before a raw "
                    "prompt auto-launches a list."
                ),
                "default": 2,
                "minimum": 1,
            },
            "merge": {
                "type": "boolean",
                "description": (
                    "true: update existing items by id, add new ones. "
                    "false (default): replace the entire list. Ignored when "
                    "a raw prompt is used to auto-create a list."
                ),
                "default": False,
            },
        },
        "required": [],
    },
}
