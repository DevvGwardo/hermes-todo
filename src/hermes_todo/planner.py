"""Prompt analysis helpers for auto-launching todo lists."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

ACTION_VERBS = {
    "add",
    "audit",
    "build",
    "check",
    "clean",
    "compare",
    "create",
    "debug",
    "deploy",
    "design",
    "document",
    "draft",
    "edit",
    "explain",
    "extract",
    "fetch",
    "finalize",
    "find",
    "fix",
    "format",
    "generate",
    "implement",
    "improve",
    "inspect",
    "investigate",
    "launch",
    "list",
    "migrate",
    "move",
    "optimize",
    "organize",
    "plan",
    "polish",
    "prepare",
    "refactor",
    "release",
    "rename",
    "repair",
    "replace",
    "research",
    "review",
    "run",
    "scan",
    "ship",
    "show",
    "sort",
    "summarize",
    "test",
    "track",
    "triage",
    "update",
    "upgrade",
    "verify",
    "write",
}

LEADING_PREFIXES = (
    "please help me ",
    "please ",
    "can you ",
    "could you ",
    "would you ",
    "will you ",
    "help me ",
    "i need you to ",
    "i want you to ",
    "i need to ",
    "need to ",
    "lets ",
    "let's ",
)

LEADING_FILLERS = (
    "and ",
    "then ",
    "also ",
    "next ",
    "finally ",
)

LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]|[0-9]+[.)])\s*")
WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]*")


def extract_tasks(prompt: str) -> List[str]:
    """Extract likely task clauses from a raw user prompt."""
    text = _normalize_prompt(prompt)
    if not text:
        return []

    line_tasks = _extract_line_tasks(text)
    if len(line_tasks) >= 2:
        return line_tasks

    comma_tasks = _extract_comma_tasks(text)
    if len(comma_tasks) >= 2:
        return comma_tasks

    clauses: List[str] = []
    for segment in _split_segments(text):
        clauses.extend(_split_coordinated_clause(segment))

    return _dedupe([task for task in (_polish_task(c) for c in clauses) if _looks_like_task(task)])


def should_track_prompt(prompt: str, min_tasks: int = 2) -> bool:
    """Return True when the prompt appears to contain multiple tasks."""
    return len(extract_tasks(prompt)) >= max(1, min_tasks)


def build_todos_from_tasks(
    tasks: List[str],
    activate_first: bool = True,
) -> List[Dict[str, str]]:
    """Convert task strings into normalized todo items."""
    todos: List[Dict[str, str]] = []
    for index, task in enumerate(tasks, start=1):
        todos.append(
            {
                "id": str(index),
                "content": task,
                "status": "in_progress" if activate_first and index == 1 else "pending",
            }
        )
    return todos


def build_todos_from_prompt(
    prompt: str,
    min_tasks: int = 2,
    activate_first: bool = True,
) -> List[Dict[str, str]]:
    """Extract tasks from a prompt and return todo items when threshold is met."""
    tasks = extract_tasks(prompt)
    if len(tasks) < max(1, min_tasks):
        return []
    return build_todos_from_tasks(tasks, activate_first=activate_first)


def _extract_line_tasks(text: str) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return []

    marked_lines = [line for line in lines if LIST_MARKER_RE.match(line)]
    source_lines = marked_lines if len(marked_lines) >= 2 else lines

    tasks = []
    for line in source_lines:
        cleaned = _normalize_task(LIST_MARKER_RE.sub("", line))
        if cleaned:
            tasks.append(cleaned)

    return _dedupe([task for task in (_polish_task(task) for task in tasks) if _looks_like_task(task)])


def _extract_comma_tasks(text: str) -> List[str]:
    if "," not in text:
        return []

    raw_parts = text.split(",")
    if len(raw_parts) < 2:
        return []

    tasks = [_normalize_task(part) for part in raw_parts]
    task_like = [task for task in tasks if _lead_verb(task)]
    if len(task_like) < 2:
        return []

    expanded: List[str] = []
    for task in tasks:
        expanded.extend(_split_coordinated_clause(task))

    return _dedupe([task for task in (_polish_task(task) for task in expanded) if _looks_like_task(task)])


def _split_segments(text: str) -> List[str]:
    segments = [text]
    patterns = (
        r"\n+",
        r";+\s*",
        r"(?<=[.!?])\s+",
        r"(?:,\s*)?(?:and then|then|after that|next|also|plus)\s+",
    )

    for pattern in patterns:
        next_segments: List[str] = []
        for segment in segments:
            next_segments.extend(re.split(pattern, segment, flags=re.IGNORECASE))
        segments = next_segments

    return [segment for segment in (_normalize_task(s) for s in segments) if segment]


def _split_coordinated_clause(clause: str) -> List[str]:
    clause = _normalize_task(clause)
    if not clause:
        return []

    parts = re.split(r"\s+(?:and|&)\s+", clause)
    if len(parts) < 2:
        return [clause]

    lead_verb = _lead_verb(parts[0])
    lead_verb_text = _lead_verb_text(parts[0])
    if not lead_verb or not lead_verb_text:
        return [clause]

    tasks = []
    for index, part in enumerate(parts):
        cleaned = _normalize_task(part)
        if not cleaned:
            continue
        if index == 0:
            tasks.append(cleaned)
            continue
        if _lead_verb(cleaned):
            tasks.append(cleaned)
            continue
        if _is_short_phrase(cleaned):
            tasks.append(f"{lead_verb_text} {cleaned}")
            continue
        tasks.append(cleaned)

    return tasks


def _normalize_prompt(prompt: str) -> str:
    prompt = prompt.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", prompt).strip()


def _normalize_task(task: str) -> str:
    task = re.sub(r"\s+", " ", task).strip(" \t\n\r,;:.")
    lowered = task.lower()

    changed = True
    while changed and task:
        changed = False
        for prefix in LEADING_PREFIXES:
            if lowered.startswith(prefix):
                task = task[len(prefix):].strip()
                lowered = task.lower()
                changed = True
        for filler in LEADING_FILLERS:
            if lowered.startswith(filler):
                task = task[len(filler):].strip()
                lowered = task.lower()
                changed = True

    return task.strip(" \t\n\r,;:.")


def _looks_like_task(task: str) -> bool:
    if not task or not WORD_RE.search(task):
        return False

    words = WORD_RE.findall(task.lower())
    if not words:
        return False

    if _lead_verb(task):
        return True

    return len(words) >= 2


def _polish_task(task: str) -> str:
    task = _normalize_task(task)
    words = WORD_RE.findall(task)
    if not words:
        return task

    first = words[0]
    if first.lower() in ACTION_VERBS and first[:1].islower():
        return f"{first.capitalize()}{task[len(first):]}"

    return task


def _lead_verb(task: str) -> Optional[str]:
    words = WORD_RE.findall(_normalize_task(task).lower())
    for word in words[:3]:
        if word in ACTION_VERBS:
            return word
    return None


def _lead_verb_text(task: str) -> Optional[str]:
    words = WORD_RE.findall(_normalize_task(task))
    for word in words[:3]:
        if word.lower() in ACTION_VERBS:
            return word
    return None


def _is_short_phrase(task: str) -> bool:
    return len(WORD_RE.findall(task)) <= 6


def _dedupe(tasks: List[str]) -> List[str]:
    seen = set()
    deduped = []
    for task in tasks:
        key = task.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(task)
    return deduped
