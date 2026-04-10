"""Tests for the TodoStore class."""

import pytest

from hermes_todo import TodoStore


class TestWriteAndRead:
    def test_write_replaces_list(self):
        store = TodoStore()
        items = [
            {"id": "1", "content": "First task", "status": "pending"},
            {"id": "2", "content": "Second task", "status": "in_progress"},
        ]
        result = store.write(items)
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["status"] == "in_progress"

    def test_read_returns_copy(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "Task", "status": "pending"}])
        items = store.read()
        items[0]["content"] = "MUTATED"
        assert store.read()[0]["content"] == "Task"

    def test_empty_read(self):
        store = TodoStore()
        assert store.read() == []


class TestHasItems:
    def test_empty_store(self):
        store = TodoStore()
        assert store.has_items() is False

    def test_non_empty_store(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "x", "status": "pending"}])
        assert store.has_items() is True


class TestFormatForInjection:
    def test_empty_returns_none(self):
        store = TodoStore()
        assert store.format_for_injection() is None

    def test_all_completed_returns_none(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "Done", "status": "completed"}])
        assert store.format_for_injection() is None

    def test_non_empty_has_markers(self):
        store = TodoStore()
        store.write(
            [
                {"id": "1", "content": "Do thing", "status": "completed"},
                {"id": "2", "content": "Next", "status": "pending"},
                {"id": "3", "content": "Working", "status": "in_progress"},
            ]
        )
        text = store.format_for_injection()
        # Completed items are filtered out
        assert "[x]" not in text
        assert "Do thing" not in text
        # Active items are included
        assert "[ ]" in text
        assert "[>]" in text
        assert "Next" in text
        assert "Working" in text
        assert "context compression" in text.lower()


class TestMergeMode:
    def test_update_existing_by_id(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "Original", "status": "pending"}])
        store.write([{"id": "1", "status": "completed"}], merge=True)
        items = store.read()
        assert len(items) == 1
        assert items[0]["status"] == "completed"
        assert items[0]["content"] == "Original"

    def test_merge_appends_new(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "First", "status": "pending"}])
        store.write([{"id": "2", "content": "Second", "status": "pending"}], merge=True)
        items = store.read()
        assert len(items) == 2

    def test_merge_skips_items_without_id(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "First", "status": "pending"}])
        store.write(
            [{"content": "No ID", "status": "pending"}, {"id": "2", "content": "Has ID", "status": "pending"}],
            merge=True,
        )
        items = store.read()
        assert len(items) == 2
        assert items[1]["id"] == "2"


class TestValidation:
    def test_missing_id_gets_placeholder(self):
        store = TodoStore()
        store.write([{"content": "No ID", "status": "pending"}])
        items = store.read()
        assert items[0]["id"] == "?"

    def test_missing_content_gets_placeholder(self):
        store = TodoStore()
        store.write([{"id": "1", "status": "pending"}])
        items = store.read()
        assert items[0]["content"] == "(no description)"

    def test_invalid_status_defaults_to_pending(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "Test", "status": "invalid"}])
        items = store.read()
        assert items[0]["status"] == "pending"

    def test_missing_status_defaults_to_pending(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "Test"}])
        items = store.read()
        assert items[0]["status"] == "pending"


class TestClear:
    def test_clear_removes_all(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "Task", "status": "pending"}])
        store.clear()
        assert not store.has_items()
        assert store.read() == []


class TestOrderPreservation:
    def test_merge_preserves_order(self):
        store = TodoStore()
        store.write([
            {"id": "a", "content": "First", "status": "pending"},
            {"id": "b", "content": "Second", "status": "pending"},
            {"id": "c", "content": "Third", "status": "pending"},
        ])
        store.write([
            {"id": "b", "status": "completed"},
            {"id": "d", "content": "Fourth", "status": "pending"},
        ], merge=True)
        items = store.read()
        assert [i["id"] for i in items] == ["a", "b", "c", "d"]
