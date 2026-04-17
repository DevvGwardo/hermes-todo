"""Tests for prompt-to-todo planning helpers."""

from hermes_todo import build_todos_from_prompt, extract_tasks, should_track_prompt


class TestExtractTasks:
    def test_extracts_bulleted_tasks(self):
        tasks = extract_tasks(
            "Please do the following:\n- Audit the repo\n- Fix the tests\n- Update the docs"
        )
        assert tasks == ["Audit the repo", "Fix the tests", "Update the docs"]

    def test_extracts_shared_verb_tasks(self):
        tasks = extract_tasks("Update the README and tests")
        assert tasks == ["Update the README", "Update tests"]

    def test_extracts_comma_separated_tasks(self):
        tasks = extract_tasks("Update docs, add examples, and run tests")
        assert tasks == ["Update docs", "Add examples", "Run tests"]


class TestShouldTrackPrompt:
    def test_true_for_multi_task_prompt(self):
        assert should_track_prompt("Fix lint and run tests") is True

    def test_false_for_single_task_prompt(self):
        assert should_track_prompt("Review the diff") is False


class TestBuildTodosFromPrompt:
    def test_returns_empty_when_threshold_not_met(self):
        assert build_todos_from_prompt("Review the diff") == []

    def test_marks_first_item_in_progress(self):
        todos = build_todos_from_prompt("Fix lint and run tests")
        assert len(todos) == 2
        assert todos[0]["status"] == "in_progress"
        assert todos[1]["status"] == "pending"
