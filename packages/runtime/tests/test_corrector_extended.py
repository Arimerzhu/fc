"""Supplementary tests for Corrector — edge cases not in test_runtime.py.

Covers:
- Correction.__repr__
- correct() applying new_command
- fix_object_name when no quoted name found in error
- Combined error+stderr analysis
- _create_correction fallback paths
"""

from __future__ import annotations

import platform

import pytest

from fc_runtime.corrector import Correction, Corrector, ERROR_FIXES
from fc_runtime.planner import Task, TaskType
from fc_runtime.executor import TaskResult


class TestCorrectionRepr:
    """Test Correction.__repr__."""

    def test_repr_contains_fix_type_and_description(self):
        c = Correction(fix_type="overwrite", description="Add --overwrite flag")
        r = repr(c)
        assert "overwrite" in r
        assert "Add --overwrite flag" in r

    def test_repr_format(self):
        c = Correction(fix_type="create_document", description="No active document")
        assert repr(c) == "Correction(create_document: No active document)"


class TestCorrectionDefaults:
    """Test Correction default values."""

    def test_defaults(self):
        c = Correction(fix_type="test", description="desc")
        assert c.new_args is None
        assert c.new_command is None
        assert c.pre_tasks == []

    def test_pre_tasks_not_shared(self):
        """Verify pre_tasks list is not shared across instances."""
        c1 = Correction(fix_type="a", description="a")
        c2 = Correction(fix_type="b", description="b")
        c1.pre_tasks.append({"cmd": "test"})
        assert len(c2.pre_tasks) == 0


class TestCorrectorEdgeCases:
    """Edge cases in Corrector.analyze() and correct()."""

    def setup_method(self):
        self.corrector = Corrector()

    def _task(self, args=None, retries=0):
        t = Task(
            id="t1", type=TaskType.PART_ADD, description="Test",
            command="fc", args=args or ["part", "add", "box"],
        )
        t.retries = retries
        return t

    def _result(self, error="", stderr=""):
        return TaskResult(task_id="t1", success=False, error=error, stderr=stderr)

    # -- Combined error + stderr --

    def test_error_pattern_in_stderr_only(self):
        """Pattern matched from stderr when error field is empty."""
        task = self._task()
        result = self._result(error="", stderr="no active document")
        correction = self.corrector.analyze(task, result)
        assert correction is not None
        assert correction.fix_type == "create_document"

    def test_error_pattern_in_error_only(self):
        """Pattern matched from error when stderr is empty."""
        task = self._task()
        result = self._result(error="file exists", stderr="")
        correction = self.corrector.analyze(task, result)
        assert correction is not None
        assert correction.fix_type == "overwrite"

    # -- fix_object_name with no quoted name --

    def test_object_not_found_no_quoted_name(self):
        """When error has no quoted name, _create_correction returns None,
        and the generic retry should kick in instead."""
        task = self._task()
        # "not found in document" matches but there's no quoted name
        result = self._result(error="something not found in document", stderr="")
        correction = self.corrector.analyze(task, result)
        # The pattern matches object_not_found, but _create_correction
        # may return a generic correction as fallback
        assert correction is not None

    # -- fix_object_name with single-quoted name --

    def test_object_not_found_single_quotes(self):
        """fix_object_name extracts name from single-quoted error."""
        task = self._task(args=["part", "add", "box", "--name", "WrongName"])
        result = self._result(error="object 'WrongName' not found", stderr="")
        correction = self.corrector.analyze(task, result)
        assert correction is not None
        assert correction.fix_type == "fix_object_name"
        assert "Box" in correction.new_args

    # -- correct() applying new_command --

    def test_correct_applies_new_command(self):
        """If a correction has new_command, correct() applies it to the task."""
        task = self._task()
        # Manually patch _create_correction to return one with new_command
        original = self.corrector._create_correction

        def patched(fix_type, description, t, r):
            return Correction(
                fix_type=fix_type, description=description,
                new_command="new_fc_command",
            )

        self.corrector._create_correction = patched
        result = self._result(error="no active document", stderr="")
        applied = self.corrector.correct(task, result)
        assert applied is True
        assert task.command == "new_fc_command"

    # -- correct() does not modify task on None correction --

    def test_correct_no_modification_when_no_fix(self):
        """When no fix is available, task is unchanged."""
        task = self._task(retries=3)
        corrector = Corrector(max_retries=3)
        original_args = task.args[:]
        original_command = task.command
        result = self._result(error="totally unknown error xyz", stderr="")
        applied = corrector.correct(task, result)
        assert applied is False
        assert task.args == original_args
        assert task.command == original_command

    # -- overwrite when --overwrite already present --

    def test_file_exists_already_has_overwrite_flag(self):
        """When task already has --overwrite, _create_correction returns None,
        but the pattern still matches so a generic fallback correction is used."""
        task = self._task(args=["export", "step", "out.step", "--overwrite"])
        result = self._result(error="file exists: out.step", stderr="")
        correction = self.corrector.analyze(task, result)
        # The pattern matches file_exists, but _create_correction returns None
        # because --overwrite is already present. Generic retry kicks in.
        assert correction is not None

    # -- Pattern priority --

    def test_first_matching_pattern_wins(self):
        """When error matches multiple patterns, the first one wins."""
        task = self._task()
        # "no active document" matches no_document
        result = self._result(error="no active document", stderr="")
        correction = self.corrector.analyze(task, result)
        assert correction.fix_type == "create_document"

    # -- All 8 patterns defined --

    def test_all_8_error_fixes_defined(self):
        """Verify ERROR_FIXES has all 8 expected patterns."""
        expected = {
            "no_document", "object_not_found", "invalid_parameter",
            "file_exists", "timeout", "syntax_error", "freecad_not_found",
            "verification_failed",
        }
        assert set(ERROR_FIXES.keys()) == expected

    # -- Each pattern has required fields --

    def test_error_fixes_have_required_fields(self):
        """Each ERROR_FIXES entry must have patterns, fix_type, description."""
        for name, fix in ERROR_FIXES.items():
            assert "patterns" in fix, f"{name} missing 'patterns'"
            assert "fix_type" in fix, f"{name} missing 'fix_type'"
            assert "description" in fix, f"{name} missing 'description'"
            assert len(fix["patterns"]) > 0, f"{name} has empty patterns"

    # -- fix_parameter does not modify positive values --

    def test_fix_parameter_preserves_positive_values(self):
        """fix_parameter should not alter already-positive dimensions."""
        task = self._task(args=["part", "add", "box", "--param", "Length=20"])
        result = self._result(error="invalid parameter: must be positive", stderr="")
        correction = self.corrector.analyze(task, result)
        assert correction is not None
        assert "--param" in correction.new_args
        assert "Length=20" in correction.new_args

    # -- fix_syntax does not alter clean args --

    def test_fix_syntax_no_duplicates_keeps_args(self):
        """When there are no duplicate flags, args should be unchanged."""
        task = self._task(args=["part", "add", "box", "--name", "Box"])
        result = self._result(error="syntax error: unexpected argument", stderr="")
        correction = self.corrector.analyze(task, result)
        assert correction is not None
        assert correction.new_args == ["part", "add", "box", "--name", "Box"]

    # -- Generic retry counter increments --

    def test_generic_retry_description_includes_count(self):
        """Generic retry description includes attempt number."""
        task = self._task(retries=1)
        result = self._result(error="unknown error abc", stderr="")
        correction = self.corrector.analyze(task, result)
        assert correction is not None
        assert correction.fix_type == "generic_retry"
        assert "2/3" in correction.description
