"""Corrector — Error detection and self-correction.

Analyzes failed task results and attempts to fix common issues:
- Missing document (create one first)
- Object not found (use correct name)
- Invalid parameters (clamp to valid range)
- Command syntax errors (fix arguments)

Integrates with ErrorRulesEngine for auto-learning:
- Records every error to the rules engine
- When patterns reach threshold (default 3), forbidden rules are auto-generated
- Rules are exported to docs/ERROR_RULES.md for cross-session persistence
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from fc_runtime.error_rules import ErrorRulesEngine

logger = logging.getLogger(__name__)


# Common error patterns and their fixes
ERROR_FIXES = {
    "no_document": {
        "patterns": [
            r"no\s+active\s+document",
            r"no\s+document",
            r"active\s+document",
            r"document.*not\s+found",
            r"没有.*文档",
            r"文档.*不存在",
        ],
        "fix_type": "create_document",
        "description": "No active document — create one first",
    },
    "object_not_found": {
        "patterns": [
            r"object.*not\s+found",
            r"not\s+found\s+in\s+document",
            r"找不到.*对象",
            r"对象.*不存在",
        ],
        "fix_type": "fix_object_name",
        "description": "Object not found — use existing object name",
    },
    "invalid_parameter": {
        "patterns": [
            r"invalid\s+(?:parameter|value|argument)",
            r"out\s+of\s+range",
            r"must\s+be\s+(?:positive|greater|less)",
            r"参数.*无效",
            r"值.*超出.*范围",
        ],
        "fix_type": "fix_parameter",
        "description": "Invalid parameter — clamp to valid range",
    },
    "file_exists": {
        "patterns": [
            r"file\s+exists",
            r"already\s+exists",
            r"文件.*已存在",
        ],
        "fix_type": "overwrite",
        "description": "File exists — add --overwrite flag",
    },
    "timeout": {
        "patterns": [
            r"timed?\s+out",
            r"timeout",
            r"超时",
        ],
        "fix_type": "retry_with_timeout",
        "description": "Operation timed out — retry with longer timeout",
    },
    "syntax_error": {
        "patterns": [
            r"syntax\s+error",
            r"unexpected\s+(?:argument|option)",
            r"invalid\s+(?:command|option|choice)",
            r"语法错误",
        ],
        "fix_type": "fix_syntax",
        "description": "Command syntax error — fix arguments",
    },
    "freecad_not_found": {
        "patterns": [
            r"freecad.*not\s+found",
            r"freecad.*not\s+installed",
            r"freecad.*not\s+available",
            r"cannot\s+(?:find|locate)\s+freecad",
            r"freecad.*未安装",
            r"找不到\s*freecad",
        ],
        "fix_type": "install_freecad",
        "description": "FreeCAD not found — installation required",
    },
    "verification_failed": {
        "patterns": [
            r"VERIFICATION_FAILED",
            r"验证失败",
            r"几何为空",
            r"实体数.*<.*期望",
            r"对象数.*<.*期望",
            r"体积.*<.*期望",
        ],
        "fix_type": "fix_geometry",
        "description": "CAD 验证失败 — 检查模型参数和几何正确性",
    },
}


class Correction:
    """A proposed correction for a failed task."""
    def __init__(self, fix_type: str, description: str,
                 new_args: list[str] | None = None,
                 new_command: str | None = None,
                 pre_tasks: list[dict[str, Any]] | None = None):
        self.fix_type = fix_type
        self.description = description
        self.new_args = new_args
        self.new_command = new_command
        self.pre_tasks = pre_tasks or []

    def __repr__(self):
        return f"Correction({self.fix_type}: {self.description})"


class Corrector:
    """Analyzes failures and proposes corrections."""

    def __init__(self, max_retries: int = 3, enable_auto_rules: bool = True,
                 rules_path: str | Path | None = None,
                 rules_threshold: int = 3):
        self._max_retries = max_retries
        self._corrections: list[Correction] = []
        # Error rules engine for auto-learning
        self._enable_auto_rules = enable_auto_rules
        if enable_auto_rules:
            default_path = Path(__file__).parent.parent.parent / "docs" / "ERROR_RULES.json"
            self._rules_engine = ErrorRulesEngine(
                rules_path=rules_path or default_path,
                threshold=rules_threshold,
            )
        else:
            self._rules_engine = None

    @property
    def corrections(self) -> list[Correction]:
        return list(self._corrections)

    @property
    def rules_engine(self) -> ErrorRulesEngine | None:
        """Access the error rules engine for inspection or manual rule management."""
        return self._rules_engine

    @property
    def auto_rules_enabled(self) -> bool:
        return self._enable_auto_rules

    def analyze(self, task, task_result) -> Correction | None:
        """Analyze a failed task and propose a correction.

        Args:
            task: The failed Task object
            task_result: The TaskResult with error details

        Returns:
            A Correction if one can be determined, None otherwise
        """
        error_text = (task_result.error + " " + task_result.stderr).lower()
        logger.info(f"Analyzing error: {error_text[:200]}")

        # Auto-learn: record error pattern to rules engine
        if self._rules_engine:
            new_rule = self._rules_engine.record_error(
                task_result.error, task_result.stderr
            )
            if new_rule:
                logger.info(f"New forbidden rule auto-generated: {new_rule.rule_id}")
                print(f"    [RULE LEARNED] {new_rule.description}")

        for error_name, fix_info in ERROR_FIXES.items():
            for pattern in fix_info["patterns"]:
                if re.search(pattern, error_text, re.IGNORECASE):
                    correction = self._create_correction(
                        fix_info["fix_type"], fix_info["description"],
                        task, task_result
                    )
                    if correction:
                        self._corrections.append(correction)
                        return correction

        # Generic retry for unknown errors
        if task.retries < self._max_retries:
            return Correction(
                fix_type="generic_retry",
                description=f"Generic retry (attempt {task.retries + 1}/{self._max_retries})",
            )

        return None

    def correct(self, task, task_result) -> bool:
        """Attempt to correct a failed task.

        Args:
            task: The failed Task object
            task_result: The TaskResult with error details

        Returns:
            True if a correction was applied, False if no fix available
        """
        correction = self.analyze(task, task_result)
        if correction is None:
            logger.warning(f"No correction available for: {task.description}")
            return False

        logger.info(f"Applying correction: {correction.description}")
        print(f"    [CORRECT] {correction.description}")

        # Apply the correction
        if correction.new_args is not None:
            task.args = correction.new_args

        if correction.new_command is not None:
            task.command = correction.new_command

        return True

    def _create_correction(self, fix_type: str, description: str,
                           task, task_result) -> Correction | None:
        """Create a specific correction based on the fix type."""

        if fix_type == "create_document":
            # Insert a document creation task before this one
            return Correction(
                fix_type=fix_type,
                description=description,
                new_args=["document", "new", "--name", "AutoDesign", "--json"] + task.args,
            )

        elif fix_type == "fix_object_name":
            # Try to extract the object name from the error and suggest alternatives
            error = task_result.error
            match = re.search(r"['\"](\w+)['\"]", error)
            if match:
                bad_name = match.group(1)
                return Correction(
                    fix_type=fix_type,
                    description=f"Object '{bad_name}' not found — will use last created object",
                    new_args=[a if a != bad_name else "Box" for a in task.args],
                )

        elif fix_type == "fix_parameter":
            # Clamp numeric parameters to valid ranges
            new_args = []
            for arg in task.args:
                # Fix negative dimensions
                dim_match = re.match(r'(--param\s+\w+=)-(\d+\.?\d*)', arg)
                if dim_match:
                    val = float(dim_match.group(2))
                    if val <= 0:
                        arg = f"{dim_match.group(1)}1.0"
                new_args.append(arg)
            return Correction(
                fix_type=fix_type,
                description=description,
                new_args=new_args,
            )

        elif fix_type == "overwrite":
            if "--overwrite" not in task.args:
                return Correction(
                    fix_type=fix_type,
                    description=description,
                    new_args=task.args + ["--overwrite"],
                )

        elif fix_type == "retry_with_timeout":
            return Correction(
                fix_type=fix_type,
                description=description,
                # Timeout is handled by the executor
            )

        elif fix_type == "fix_syntax":
            # Try common syntax fixes
            new_args = task.args[:]
            # Remove duplicate flags
            seen = set()
            cleaned = []
            for arg in new_args:
                if arg.startswith("--") and arg in seen:
                    continue
                seen.add(arg)
                cleaned.append(arg)
            return Correction(
                fix_type=fix_type,
                description=description,
                new_args=cleaned,
            )

        elif fix_type == "install_freecad":
            # Provide platform-specific installation guidance
            import platform
            system = platform.system().lower()
            if system == "windows":
                install_help = (
                    "FreeCAD not found on Windows. Install options:\n"
                    "  1. Download from https://www.freecad.org/downloads.php\n"
                    "  2. winget install FreeCAD.FreeCAD\n"
                    "  3. choco install freecad"
                )
            elif system == "darwin":
                install_help = (
                    "FreeCAD not found on macOS. Install options:\n"
                    "  1. brew install --cask freecad\n"
                    "  2. Download from https://www.freecad.org/downloads.php"
                )
            else:
                install_help = (
                    "FreeCAD not found on Linux. Install options:\n"
                    "  1. sudo apt install freecad  (Debian/Ubuntu)\n"
                    "  2. sudo dnf install freecad  (Fedora)\n"
                    "  3. flatpak install flathub org.freecadweb.FreeCAD"
                )
            return Correction(
                fix_type=fix_type,
                description=install_help,
            )

        return Correction(fix_type=fix_type, description=description)

    # ── Auto-Learning Rule Management ──

    def get_rules_text(self) -> str:
        """Get formatted text of all active auto-learned rules for prompt injection."""
        if not self._rules_engine:
            return ""
        return self._rules_engine.get_active_rules_text()

    def export_rules(self) -> Path | None:
        """Export rules to JSON + markdown. Returns markdown path."""
        if not self._rules_engine:
            return None
        json_path = self._rules_engine.export_rules()
        md_path = self._rules_engine.save_as_markdown()
        return md_path

    def get_rules_summary(self) -> dict[str, Any]:
        """Get JSON-serializable rules summary."""
        if not self._rules_engine:
            return {"enabled": False}
        return self._rules_engine.get_rules_summary()
