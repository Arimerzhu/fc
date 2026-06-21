"""Tests for ErrorRulesEngine (TASK-036).

Covers:
- Error pattern extraction from various error formats
- Pattern counting and threshold-based rule generation
- Rule persistence (export/import JSON, markdown generation)
- Rule management (enable/disable/reset)
- Corrector integration with auto-learning rules engine
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from fc_runtime.error_rules import (
    ErrorPattern, ForbiddenRule, ErrorRulesEngine,
    normalize_error_message, extract_error_pattern,
    compute_pattern_hash, generate_rule,
)
from fc_runtime.corrector import Corrector
from fc_runtime.planner import Task, TaskType
from fc_runtime.executor import TaskResult


# ── Error Pattern Extraction Tests ──

class TestNormalizeErrorMessage:
    def test_lowercase_and_collapse_whitespace(self):
        text = "  NO   active   Document  "
        assert normalize_error_message(text) == "no active document"

    def test_strip_timestamps(self):
        text = "[2026-06-11 10:30:00] no active document"
        assert normalize_error_message(text) == "no active document"


class TestExtractErrorPattern:
    def test_missing_flag(self):
        ptype, ctx = extract_error_pattern("missing required argument: --name")
        assert ptype == "missing_flag"
        assert ctx["flag"] == "--name"

    def test_invalid_value(self):
        ptype, ctx = extract_error_pattern("invalid value 'XYZ' for --plane")
        assert ptype == "invalid_value"
        assert ctx["value"].upper() == "XYZ"
        assert ctx["flag"] == "--plane"

    def test_negative_dimension(self):
        ptype, ctx = extract_error_pattern("negative value: Length=-5")
        assert ptype == "negative_dimension"
        assert ctx["param"].lower() == "length"

    def test_unknown_object(self):
        ptype, ctx = extract_error_pattern("object 'Box_999' not found in document")
        assert ptype == "unknown_object"
        assert ctx["object"].lower() == "box_999"

    def test_missing_document(self):
        ptype, ctx = extract_error_pattern("no active document")
        assert ptype == "missing_document"

    def test_file_exists(self):
        ptype, ctx = extract_error_pattern("file 'output.step' already exists")
        assert ptype == "file_exists"
        assert ctx["file"] == "output.step"

    def test_wrong_type(self):
        ptype, ctx = extract_error_pattern("unknown type 'hexagon'")
        assert ptype == "wrong_type"
        assert ctx["type"] == "hexagon"

    def test_missing_param(self):
        ptype, ctx = extract_error_pattern("missing --name parameter")
        assert ptype == "missing_param"

    def test_unknown_pattern(self):
        ptype, ctx = extract_error_pattern("something completely unrelated")
        assert ptype == "unknown"
        assert ctx == {}

    def test_stderr_also_checked(self):
        ptype, ctx = extract_error_pattern("", "no active document")
        assert ptype == "missing_document"


class TestComputePatternHash:
    def test_same_input_same_hash(self):
        h1 = compute_pattern_hash("missing_flag", {"flag": "--name"})
        h2 = compute_pattern_hash("missing_flag", {"flag": "--name"})
        assert h1 == h2

    def test_different_input_different_hash(self):
        h1 = compute_pattern_hash("missing_flag", {"flag": "--name"})
        h2 = compute_pattern_hash("missing_flag", {"flag": "--json"})
        assert h1 != h2


# ── ErrorRulesEngine Tests ──

class TestErrorRulesEngine:
    def setup_method(self):
        self.engine = ErrorRulesEngine(threshold=3)

    def test_initial_state(self):
        assert self.engine.pattern_count == 0
        assert self.engine.rule_count == 0
        assert self.engine.active_rules == []

    def test_record_single_error_no_rule(self):
        rule = self.engine.record_error("missing required argument: --name")
        assert rule is None
        assert self.engine.pattern_count == 1
        assert self.engine.rule_count == 0

    def test_record_errors_below_threshold(self):
        for _ in range(2):
            self.engine.record_error("missing required argument: --name")
        assert self.engine.rule_count == 0
        p = list(self.engine.patterns.values())[0]
        assert p.count == 2

    def test_record_errors_at_threshold_generates_rule(self):
        for i in range(3):
            rule = self.engine.record_error("missing required argument: --name")
            if i < 2:
                assert rule is None
            else:
                assert rule is not None
                assert rule.pattern_type == "missing_flag"
                assert rule.occurrence_count == 3
        assert self.engine.rule_count == 1

    def test_threshold_not_retriggered(self):
        """After rule generated, same error shouldn't create duplicate rules."""
        for _ in range(6):
            self.engine.record_error("missing required argument: --name")
        assert self.engine.rule_count == 1
        assert len(self.engine.active_rules) == 1

    def test_different_errors_different_rules(self):
        for _ in range(3):
            self.engine.record_error("missing required argument: --name")
        for _ in range(3):
            self.engine.record_error("no active document")
        assert self.engine.rule_count == 2

    def test_get_active_rules_text_empty(self):
        text = self.engine.get_active_rules_text()
        assert text == ""

    def test_get_active_rules_text_with_rules(self):
        for _ in range(3):
            self.engine.record_error("no active document")
        text = self.engine.get_active_rules_text()
        assert "Active Forbidden Rules" in text
        assert "MISSING_DOCUMENT" in text

    def test_disable_rule(self):
        for _ in range(3):
            self.engine.record_error("no active document")
        rule = self.engine.active_rules[0]
        assert self.engine.disable_rule(rule.rule_id) is True
        assert len(self.engine.active_rules) == 0

    def test_enable_rule(self):
        for _ in range(3):
            self.engine.record_error("no active document")
        rule = self.engine.active_rules[0]
        self.engine.disable_rule(rule.rule_id)
        assert self.engine.enable_rule(rule.rule_id) is True
        assert len(self.engine.active_rules) == 1

    def test_reset_pattern(self):
        for _ in range(3):
            self.engine.record_error("no active document")
        p = list(self.engine.patterns.values())[0]
        assert self.engine.reset_pattern(p.hash) is True
        assert p.count == 0

    def test_export_import_json(self, tmp_path):
        """Test cross-session persistence via JSON export/import."""
        for _ in range(3):
            self.engine.record_error("missing required argument: --name")
        for _ in range(3):
            self.engine.record_error("no active document")

        json_path = tmp_path / "rules.json"
        self.engine.export_rules(json_path)

        # Verify file exists and is valid JSON
        assert json_path.exists()
        with open(json_path) as f:
            data = json.load(f)
        assert data["total_rules"] == 2

        # Import into new engine
        new_engine = ErrorRulesEngine()
        count = new_engine.import_rules(json_path)
        assert count == 2
        assert new_engine.rule_count == 2

    def test_save_as_markdown(self, tmp_path):
        for _ in range(3):
            self.engine.record_error("no active document")
        md_path = tmp_path / "ERROR_RULES.md"
        self.engine.save_as_markdown(md_path)
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "ERROR_RULES" in content
        assert "MISSING_DOCUMENT" in content

    def test_get_rules_summary(self):
        for _ in range(3):
            self.engine.record_error("no active document")
        summary = self.engine.get_rules_summary()
        assert summary["total_patterns"] == 1
        assert summary["total_rules"] == 1
        assert summary["active_rules"] == 1

    def test_custom_threshold(self):
        engine = ErrorRulesEngine(threshold=2)
        engine.record_error("no active document")
        assert engine.rule_count == 0
        engine.record_error("no active document")
        assert engine.rule_count == 1


# ── Generate Rule Tests ──

class TestGenerateRule:
    def test_missing_flag_rule(self):
        rule = generate_rule("missing_flag", {"flag": "--name"}, 3)
        assert rule is not None
        assert rule.pattern_type == "missing_flag"
        assert "--name" in rule.forbidden_action

    def test_negative_dimension_rule(self):
        rule = generate_rule("negative_dimension", {"param": "Length"}, 3)
        assert rule is not None
        assert "Length" in rule.description

    def test_unknown_pattern_returns_none(self):
        rule = generate_rule("unknown", {}, 3)
        assert rule is None


# ── Corrector Integration Tests ──

class TestCorrectorAutoLearning:
    def test_corrector_has_rules_engine(self):
        c = Corrector()
        assert c.rules_engine is not None
        assert c.auto_rules_enabled is True

    def test_corrector_rules_disabled(self):
        c = Corrector(enable_auto_rules=False)
        assert c.rules_engine is None
        assert c.auto_rules_enabled is False

    def test_analyze_records_error_to_engine(self):
        c = Corrector()
        task = Task(
            id="t1", type=TaskType.PART_ADD,
            description="Test", command="fc",
            args=["part", "add", "box"],
        )
        result = TaskResult(
            task_id="t1", success=False,
            error="missing required argument: --name",
        )
        c.analyze(task, result)
        assert c.rules_engine.pattern_count == 1

    def test_analyze_generates_rule_at_threshold(self):
        c = Corrector()
        task = Task(
            id="t1", type=TaskType.PART_ADD,
            description="Test", command="fc",
            args=["part", "add", "box"],
        )
        for i in range(3):
            result = TaskResult(
                task_id="t1", success=False,
                error="missing required argument: --name",
            )
            c.analyze(task, result)
        assert c.rules_engine.rule_count == 1

    def test_get_rules_text_empty(self):
        c = Corrector()
        text = c.get_rules_text()
        assert text == ""

    def test_get_rules_text_after_learning(self):
        c = Corrector()
        task = Task(
            id="t1", type=TaskType.PART_ADD,
            description="Test", command="fc",
            args=["part", "add", "box"],
        )
        for _ in range(3):
            result = TaskResult(
                task_id="t1", success=False,
                error="no active document",
            )
            c.analyze(task, result)
        text = c.get_rules_text()
        assert "Active Forbidden Rules" in text

    def test_export_rules(self, tmp_path):
        c = Corrector(rules_path=tmp_path / "ERROR_RULES.json")
        task = Task(
            id="t1", type=TaskType.PART_ADD,
            description="Test", command="fc",
            args=["part", "add", "box"],
        )
        for _ in range(3):
            result = TaskResult(
                task_id="t1", success=False,
                error="no active document",
            )
            c.analyze(task, result)
        md_path = c.export_rules()
        assert md_path is not None
        assert md_path.exists()

    def test_get_rules_summary(self):
        c = Corrector()
        summary = c.get_rules_summary()
        # Corrector.get_rules_summary returns the engine's summary dict
        assert summary["total_rules"] == 0
        assert summary["total_patterns"] == 0

    def test_get_rules_summary_disabled(self):
        c = Corrector(enable_auto_rules=False)
        summary = c.get_rules_summary()
        assert summary["enabled"] is False
