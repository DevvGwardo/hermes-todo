# hermes-todo

In-memory task list for AI agents. Zero dependencies. OpenAI function-calling schema included.

## Install

```bash
pip install hermes-todo
```

Or for development:

```bash
git clone https://github.com/jayminwest/hermes-todo.git
cd hermes-todo
pip install -e ".[dev]"
```

## Usage

### As a standalone store

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

# Format for context injection (after compression)
text = store.format_for_injection()
```

### As an agent tool (with OpenAI function-calling)

```python
from hermes_todo import TodoStore, todo_tool, TODO_SCHEMA

# In your agent loop:
store = TodoStore()

# Register the schema with your LLM client
# tools = [TODO_SCHEMA]

# When the LLM calls the todo tool:
result = todo_tool(
    todos=[{"id": "1", "content": "Plan architecture", "status": "pending"}],
    merge=False,
    store=store,
)
# result is a JSON string with {"todos": [...], "summary": {...}}
```

### Integrating with hermes-agent

In `tools/todo_tool.py`, replace the local implementation with:

```python
from hermes_todo import TodoStore, todo_tool, TODO_SCHEMA

# Register with hermes registry (hermes-specific)
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

## API

### `TodoStore`

| Method | Description |
|--------|-------------|
| `write(todos, merge=False)` | Write items. `merge=True` updates by id, `merge=False` replaces all. Returns full list. |
| `read()` | Returns a copy of the current list. |
| `has_items()` | Returns `True` if the list has any items. |
| `format_for_injection()` | Renders active items for context injection. Returns `None` if empty. |
| `clear()` | Removes all items. |

### `todo_tool(todos=None, merge=False, store=None)`

Single entry point — reads when `todos` is `None`, writes otherwise. Returns JSON string.

### `TODO_SCHEMA`

OpenAI function-calling schema dict. Includes behavioral guidance in the description.

### `VALID_STATUSES`

`{"pending", "in_progress", "completed", "cancelled"}`

## License

MIT
