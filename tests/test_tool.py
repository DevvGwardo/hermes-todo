"""Tests for the todo_tool function and schema."""

import json

from hermes_todo import TODO_SCHEMA, TodoStore, todo_cli_from_result, todo_tool


class TestTodoToolFunction:
    def test_read_mode(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "Task", "status": "pending"}])
        result = json.loads(todo_tool(store=store))
        assert result["summary"]["total"] == 1
        assert result["summary"]["pending"] == 1

    def test_write_mode(self):
        store = TodoStore()
        result = json.loads(
            todo_tool(
                todos=[{"id": "1", "content": "New", "status": "in_progress"}],
                store=store,
            )
        )
        assert result["summary"]["in_progress"] == 1
        assert result["todos"][0]["content"] == "New"

    def test_no_store_returns_error(self):
        result = json.loads(todo_tool())
        assert "error" in result

    def test_summary_counts(self):
        store = TodoStore()
        store.write([
            {"id": "1", "content": "A", "status": "pending"},
            {"id": "2", "content": "B", "status": "in_progress"},
            {"id": "3", "content": "C", "status": "completed"},
            {"id": "4", "content": "D", "status": "cancelled"},
        ])
        result = json.loads(todo_tool(store=store))
        assert result["summary"]["total"] == 4
        assert result["summary"]["pending"] == 1
        assert result["summary"]["in_progress"] == 1
        assert result["summary"]["completed"] == 1
        assert result["summary"]["cancelled"] == 1

    def test_prompt_auto_launches_when_two_tasks_are_detected(self):
        store = TodoStore()
        result = json.loads(
            todo_tool(
                prompt="Update the README and tests",
                store=store,
            )
        )
        assert result["prompt_analysis"]["launched"] is True
        assert result["prompt_analysis"]["task_count"] == 2
        assert result["summary"]["total"] == 2
        assert result["todos"][0]["status"] == "in_progress"
        assert "HERMES TODO" in result["cli"]

    def test_prompt_does_not_launch_for_single_task(self):
        store = TodoStore()
        result = json.loads(
            todo_tool(
                prompt="Review the diff",
                store=store,
            )
        )
        assert result["prompt_analysis"]["launched"] is False
        assert result["prompt_analysis"]["task_count"] == 1
        assert result["summary"]["total"] == 0

    def test_cli_text_can_be_extracted_from_tool_result(self):
        store = TodoStore()
        result = todo_tool(
            prompt="Update the README and tests",
            store=store,
        )
        cli = todo_cli_from_result(result)
        assert cli is not None
        assert "HERMES TODO" in cli
        assert "[>]" in cli

    def test_cli_text_extraction_returns_none_for_invalid_json(self):
        assert todo_cli_from_result("not json") is None

    def test_cli_text_extraction_returns_none_when_cli_missing(self):
        assert todo_cli_from_result(json.dumps({"todos": []})) is None


class TestAutoClearDone:
    def test_done_flag_when_all_completed(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "Task", "status": "pending"}])
        result = json.loads(todo_tool(
            todos=[{"id": "1", "status": "completed"}],
            merge=True,
            store=store,
        ))
        assert result["done"] is True
        assert result["todos"] == []
        assert result["summary"]["total"] == 0

    def test_no_done_flag_when_still_active(self):
        store = TodoStore()
        store.write([
            {"id": "1", "content": "A", "status": "pending"},
            {"id": "2", "content": "B", "status": "pending"},
        ])
        result = json.loads(todo_tool(
            todos=[{"id": "1", "status": "completed"}],
            merge=True,
            store=store,
        ))
        assert "done" not in result
        assert len(result["todos"]) == 2

    def test_no_done_flag_on_read(self):
        """Reading an empty list shouldn't show done flag."""
        store = TodoStore()
        result = json.loads(todo_tool(store=store))
        assert "done" not in result
        assert result["todos"] == []

    def test_no_done_flag_when_auto_clear_disabled(self):
        store = TodoStore(auto_clear=False)
        store.write([{"id": "1", "content": "Task", "status": "pending"}])
        result = json.loads(todo_tool(
            todos=[{"id": "1", "status": "completed"}],
            merge=True,
            store=store,
        ))
        assert "done" not in result
        assert len(result["todos"]) == 1


class TestSchema:
    def test_schema_is_valid_dict(self):
        assert isinstance(TODO_SCHEMA, dict)
        assert TODO_SCHEMA["name"] == "todo"
        assert "parameters" in TODO_SCHEMA
        assert "properties" in TODO_SCHEMA["parameters"]

    def test_schema_has_required_fields(self):
        props = TODO_SCHEMA["parameters"]["properties"]
        assert "prompt" in props
        assert "todos" in props
        assert "min_tasks" in props
        assert "merge" in props
