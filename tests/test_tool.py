"""Tests for the todo_tool function and schema."""

import json

import pytest

from hermes_todo import TodoStore, todo_tool, TODO_SCHEMA


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


class TestSchema:
    def test_schema_is_valid_dict(self):
        assert isinstance(TODO_SCHEMA, dict)
        assert TODO_SCHEMA["name"] == "todo"
        assert "parameters" in TODO_SCHEMA
        assert "properties" in TODO_SCHEMA["parameters"]

    def test_schema_has_required_fields(self):
        props = TODO_SCHEMA["parameters"]["properties"]
        assert "todos" in props
        assert "merge" in props
