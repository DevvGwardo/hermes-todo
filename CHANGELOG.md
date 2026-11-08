# Changelog

## v0.2.1 — 2026-05-25

### Bugs Fixed

- **`_split_coordinated_clause`**: Now handles the Oxford comma pattern (`implement, test, and deploy` → three tasks) by stripping leading coordinating conjunctions. The split regex also matches uppercase "AND".
- **Markdown in task text**: Bold (`**`), italic (`*`/`_`), and inline code (`` ` ``) tokens are stripped in `_normalize_task` before processing (e.g. `**fix** the login` → `Fix the login`).
- **`content=None` crash**: `validate_todo_item` now checks for `None` before `str()` conversion, preventing the literal string `"None"`.
- **Uppercase verbs**: `_polish_task` now title-cases uppercase verbs (`FIX BUG` → `Fix BUG`).
- **`_looks_like_task` too loose**: Now requires a lead verb **or** a minimum of 3 words (was 2), reducing false positives from short phrases.
- **Numbered list extraction**: Lines extracted via `LIST_MARKER_RE` are always treated as task-like, so `1. first\n2. second` now correctly produces two tasks.

### Planner Improvements

- **30+ new dev verbs** added to `ACTION_VERBS`: `remove`, `delete`, `install`, `configure`, `setup`, `analyze`, `benchmark`, `profile`, `lint`, `commit`, `push`, `merge`, `rebase`, `cherry-pick`, `bisect`, `monitor`, `alert`, `rollback`, `handle`, `support`, `validate`, `sanitize`, `encrypt`, `sign`, `backup`, `restore`, `schedule`, `seed`, `archive`, `purge`, `initialize`, `scaffold`, `provision`, `notify`, `pull`.
- **New leading prefixes**: `"i would like you to "`, `"do you mind "`, `"would you mind "`.
- **`step N:` prefix stripping**: `_normalize_task` strips `"step 1:"`, `"step 2:"`, etc. (case-insensitive).
- **`!!!`/`---` middle stripping**: These sequences are now replaced with a space when they appear in the middle of task text.

### New Features & Methods

- **`TodoStore.__init__(max_items=...)`**: Optional `max_items` parameter; when exceeded, a `warnings.warn` is issued (write still proceeds).
- **`TodoStore.get_by_id(id)`**: Returns a single item dict (copy) or `None`.
- **`TodoStore.filter_by_status(status)`**: Returns a list of items matching the given status.
- **`format_for_cli(compact=True)`**: New compact unicode-glyph format (`📋 Todo (0/1 done)` with `[>]`, `[ ]`, `[x]`, `[~]` markers).

### Lint / Type Fixes

- **Ruff**: Fixed unused variables and ambiguous `l` variable name in `test_store.py`.
- **Mypy**: Added explicit `Dict[str, Any]` type annotation to prevent bool-assignment error in `tool.py`.

### Code Quality

- **`VALID_STATUSES` usage**: Hardcoded status strings replaced with `VALID_STATUSES`, `DONE_STATUSES`, and `ACTIVE_STATUSES` constants.
- **`HEADER_TITLE` constant**: `"HERMES TODO"` extracted to a module-level constant.
- **Self type annotations**: Added proper type annotations to all `TodoStore` methods.
- **Deleted `__pycache__/`** directories from source tree.

### Documentation

- **README**: Documented `compact=True` parameter for `format_for_cli()` and `prompt_analysis` output key for `todo_tool()`.
- **This changelog** added.
