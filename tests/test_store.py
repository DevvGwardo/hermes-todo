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


class TestFormatForCli:
    def test_empty_cli_view_has_empty_state(self):
        store = TodoStore()
        text = store.format_for_cli()
        assert "HERMES TODO" in text
        assert "No tasks yet." in text

    def test_cli_view_includes_all_statuses(self):
        store = TodoStore(auto_clear=False)
        store.write(
            [
                {"id": "1", "content": "Inspect repo", "status": "in_progress"},
                {"id": "2", "content": "Write tests", "status": "pending"},
                {"id": "3", "content": "Ship docs", "status": "completed"},
                {"id": "4", "content": "Skip legacy task", "status": "cancelled"},
            ]
        )
        text = store.format_for_cli(width=64)
        assert "[>]" in text
        assert "[ ]" in text
        assert "[x]" in text
        assert "[~]" in text
        assert "active 1" in text


class TestSeedFromPrompt:
    def test_seed_from_prompt_builds_list(self):
        store = TodoStore()
        items = store.seed_from_prompt("Update the docs and run tests")
        assert len(items) == 2
        assert items[0]["status"] == "in_progress"

    def test_seed_from_prompt_ignores_single_task(self):
        store = TodoStore()
        items = store.seed_from_prompt("Review the diff")
        assert items == []


class TestMergeMode:
    def test_update_existing_by_id(self):
        store = TodoStore(auto_clear=False)
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


class TestAutoClear:
    def test_auto_clears_when_all_completed(self):
        store = TodoStore()  # auto_clear=True by default
        store.write([
            {"id": "1", "content": "A", "status": "pending"},
            {"id": "2", "content": "B", "status": "pending"},
        ])
        assert store.has_items()
        # Mark all as completed
        result = store.write([
            {"id": "1", "status": "completed"},
            {"id": "2", "status": "completed"},
        ], merge=True)
        assert not store.has_items()
        assert result == []

    def test_auto_clears_when_all_cancelled(self):
        store = TodoStore()
        store.write([{"id": "1", "content": "A", "status": "pending"}])
        result = store.write([{"id": "1", "status": "cancelled"}], merge=True)
        assert not store.has_items()

    def test_auto_clears_when_mixed_completed_cancelled(self):
        store = TodoStore()
        store.write([
            {"id": "1", "content": "A", "status": "pending"},
            {"id": "2", "content": "B", "status": "pending"},
        ])
        result = store.write([
            {"id": "1", "status": "completed"},
            {"id": "2", "status": "cancelled"},
        ], merge=True)
        assert not store.has_items()

    def test_no_clear_when_one_still_active(self):
        store = TodoStore()
        store.write([
            {"id": "1", "content": "A", "status": "pending"},
            {"id": "2", "content": "B", "status": "pending"},
        ])
        store.write([{"id": "1", "status": "completed"}], merge=True)
        assert store.has_items()
        assert len(store.read()) == 2

    def test_no_clear_when_disabled(self):
        store = TodoStore(auto_clear=False)
        store.write([{"id": "1", "content": "A", "status": "pending"}])
        store.write([{"id": "1", "status": "completed"}], merge=True)
        assert store.has_items()
        assert len(store.read()) == 1

    def test_no_clear_on_replace_mode(self):
        """Replace mode with completed items should auto-clear."""
        store = TodoStore()
        store.write([{"id": "1", "content": "A", "status": "completed"}])
        assert not store.has_items()

    def test_does_not_clear_empty_list(self):
        """Writing to an empty store should not trigger auto-clear logic."""
        store = TodoStore()
        result = store.write([], merge=False)
        assert result == []


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
