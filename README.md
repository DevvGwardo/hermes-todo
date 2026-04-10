<div align="center">

# hermes-todo

**In-memory task list for AI agents. Zero dependencies.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](./tests)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-blueviolet)](./pyproject.toml)

[Quick Start](#quick-start) · [Usage](#usage) · [API Reference](#api-reference) · [How It Works](#how-it-works)

</div>

---

## Features

| | |
|---|---|
| 🚀 **Zero Dependencies** | Pure Python stdlib — no installs beyond `hermes-todo` itself |
| 🤖 **Agent-Ready** | OpenAI function-calling schema included out of the box |
| 🔄 **Smart Merging** | Update individual tasks by ID without losing the rest |
| 🧹 **Auto-Clear** | List wipes itself when everything is done — clean state, always |
| 💉 **Context Injection** | Render active tasks as compact text for LLM context windows |
| ✅ **Validation** | Missing fields get sane defaults — never crashes your agent loop |

---

## Architecture

```mermaid
flowchart TB
    %% ── Styling ──
    classDef agent fill:#4A6FA5,stroke:#2D4A7A,color:#fff,stroke-width:2px
    classDef core fill:#2D8659,stroke:#1B5E3A,color:#fff,stroke-width:2px
    classDef state fill:#7B4F9E,stroke:#5A3478,color:#fff,stroke-width:2px
    classDef output fill:#D4880F,stroke:#A66A00,color:#fff,stroke-width:2px
    classDef autoclear fill:#C0392B,stroke:#922B21,color:#fff,stroke-width:2px
    classDef io fill:#5B7B8A,stroke:#3D5A66,color:#fff,stroke-width:2px

    %% ── Agent Layer ──
    LLM["🧠 LLM Agent Loop<br/><i>Function-calling enabled</i>"]:::agent
    SCHEMA["📋 TODO_SCHEMA<br/><i>OpenAI tool definition</i>"]:::agent

    %% ── Entry Point ──
    TOOL["⚡ todo_tool<br/><i>Single entry point</i>"]:::core

    %% ── Routing ──
    ROUTE{"todos provided?"}:::core

    %% ── Read Path ──
    READ["📖 store.read()<br/><i>Return current list</i>"]:::output

    %% ── Write Path ──
    WRITE{"merge mode?"}:::core
    REPLACE["♻️ Replace<br/><i>Full list swap</i>"]:::core
    MERGE["🔗 Merge<br/><i>Update by ID, append new</i>"]:::core

    %% ── Store ──
    STORE["🗄️ TodoStore<br/><i>In-memory ordered list</i>"]:::core

    %% ── State Transitions ──
    PENDING["⏳ pending"]:::state
    INPROGRESS["🔥 in_progress"]:::state
    COMPLETED["✅ completed"]:::state
    CANCELLED["🚫 cancelled"]:::state

    %% ── Auto-Clear ──
    CHECK{"all tasks done?"}:::autoclear
    AUTOCLEAR["🧹 Auto-Clear<br/><i>List wiped automatically</i>"]:::autoclear

    %% ── Output ──
    JSON_OUT["📦 JSON Response<br/><i>todos + summary + done flag</i>"]:::output
    INJECT["💉 format_for_injection<br/><i>Active tasks → context string</i>"]:::output
    CONTEXT["📝 LLM Context Window"]:::io

    %% ── Connections ──
    LLM -->|"registers"| SCHEMA
    LLM -->|"calls"| TOOL
    SCHEMA -.->|"defines"| TOOL

    TOOL --> ROUTE
    ROUTE -->|"no todos"| READ
    ROUTE -->|"todos given"| WRITE

    WRITE -->|"merge=False"| REPLACE
    WRITE -->|"merge=True"| MERGE
    REPLACE --> STORE
    MERGE --> STORE

    STORE --> PENDING
    PENDING -->|"agent starts"| INPROGRESS
    INPROGRESS -->|"agent finishes"| COMPLETED
    INPROGRESS -->|"agent skips"| CANCELLED

    STORE --> CHECK
    CHECK -->|"yes"| AUTOCLEAR
    CHECK -->|"no, active items exist"| INJECT
    AUTOCLEAR --> JSON_OUT

    STORE --> JSON_OUT
    READ --> JSON_OUT
    INJECT -->|"injected into"| CONTEXT
    JSON_OUT --> LLM
    CONTEXT --> LLM
```

---

## Quick Start

```bash
pip install hermes-todo
```

```python
from hermes_todo import TodoStore

store = TodoStore()
store.write([
    {"id": "1", "content": "Ship v1", "status": "pending"},
    {"id": "2", "content": "Write docs", "status": "in_progress"},
])

print(store.format_for_injection())
# → [Your active task list was preserved across context compression]
#   - [ ] 1. Ship v1 (pending)
#   - [>] 2. Write docs (in_progress)
```

---

## Usage

### Standalone Store

```python
from hermes_todo import TodoStore

store = TodoStore()

# Write tasks (replace mode)
store.write([
    {"id": "1", "content": "Implement auth", "status": "in_progress"},
    {"id": "2", "content": "Write tests", "status": "pending"},
])

# Read tasks
items = store.read()

# Merge updates by id
store.write([{"id": "2", "status": "completed"}], merge=True)

# Format for context injection
text = store.format_for_injection()

# Clear everything
store.clear()
```

### As an Agent Tool (OpenAI Function-Calling)

```python
from hermes_todo import TodoStore, todo_tool, TODO_SCHEMA

store = TodoStore()

# Register the schema with your LLM client
# tools = [TODO_SCHEMA]

# When the LLM calls the todo tool:
result = todo_tool(
    todos=[{"id": "1", "content": "Plan architecture", "status": "pending"}],
    merge=False,
    store=store,
)
# result → JSON string: {"todos": [...], "summary": {...}}
```

### Integrating with hermes-agent

```python
from hermes_todo import TodoStore, todo_tool, TODO_SCHEMA
from tools.registry import registry

registry.register(
    name="todo",
    toolset="todo",
    schema=TODO_SCHEMA,
    handler=lambda args, **kw: todo_tool(
        todos=args.get("todos"),
        merge=args.get("merge", False),
        store=kw.get("store"),
    ),
    check_fn=lambda: True,
    emoji="📋",
)
```

---

## API Reference

### `TodoStore`

| Method | Description |
|--------|-------------|
| `write(todos, merge=False)` | Write items. `merge=True` updates by ID, `merge=False` replaces all. Returns full list. |
| `read()` | Returns a copy of the current list. |
| `has_items()` | Returns `True` if the list has any items. |
| `format_for_injection()` | Renders active items for context injection. Returns `None` if empty. |
| `clear()` | Removes all items. |

### `todo_tool(todos=None, merge=False, store=None)`

Single entry point — reads when `todos` is `None`, writes otherwise. Returns JSON string with full list, summary counts, and a `done` flag.

### `TODO_SCHEMA`

OpenAI function-calling schema dict. Includes behavioral guidance in the description.

### `VALID_STATUSES`

`{"pending", "in_progress", "completed", "cancelled"}`

---

## How It Works

1. **Agent registers** `TODO_SCHEMA` with its LLM client as an available tool
2. **LLM decides** to track tasks and calls the `todo` tool with a list of items
3. **`todo_tool`** routes to read or write based on whether `todos` was provided
4. **`TodoStore`** validates, merges or replaces, and manages state transitions
5. **Auto-clear** kicks in when all tasks reach a terminal state (`completed`/`cancelled`)
6. **Context injection** via `format_for_injection()` keeps the agent's context window lean with only active tasks

---

## License

MIT — see [LICENSE](./LICENSE) for details.
