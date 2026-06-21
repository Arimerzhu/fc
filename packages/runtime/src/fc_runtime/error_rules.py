"""Error Rules Engine — Auto-learning forbidden rules from error patterns.

Analyzes failed task results, extracts error patterns, and automatically
generates forbidden rules when the same pattern occurs >= threshold times.
Rules are persisted to docs/ERROR_RULES.md and injected into Planner prompts.

Key components:
- ErrorPattern: A normalized error signature (error_type + context hash)
- ForbiddenRule: A rule that prevents a specific class of errors
- ErrorRulesEngine: Main engine that tracks patterns and generates rules
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Error Pattern Extraction ──

# Patterns that extract structured info from error messages
ERROR_PATTERNS = {
    "missing_flag": {
        "regex": r"missing\s+(?:required\s+)?(?:argument|option|flag)\s*[:\-]?\s*(--?\w+)",
        "extract": lambda m: {"flag": m.group(1)},
    },
    "invalid_value": {
        "regex": r"invalid\s+(?:value|choice)\s+['\"]?(\w+)['\"]?\s+for\s+(--?\w+)",
        "extract": lambda m: {"value": m.group(1), "flag": m.group(2)},
    },
    "negative_dimension": {
        "regex": r"(?:negative|must\s+be\s+(?:positive|greater\s+than\s+zero)).*?(\w+)\s*[=]\s*-?(\d+\.?\d*)",
        "extract": lambda m: {"param": m.group(1), "value": m.group(2)},
    },
    "unknown_object": {
        "regex": r"object\s+['\"](\w+)['\"].*?(?:not\s+found|does\s+not\s+exist)",
        "extract": lambda m: {"object": m.group(1)},
    },
    "missing_document": {
        "regex": r"no\s+(?:active\s+)?document",
        "extract": lambda m: {},
    },
    "file_exists": {
        "regex": r"file\s+['\"]?(\S+?)['\"]?\s+already\s+exists",
        "extract": lambda m: {"file": m.group(1)},
    },
    "wrong_type": {
        "regex": r"unknown\s+(?:type|part)\s+['\"](\w+)['\"]",
        "extract": lambda m: {"type": m.group(1)},
    },
    "missing_param": {
        "regex": r"(?:missing|required).*?--(\w+)",
        "extract": lambda m: {"param": f"--{m.group(1)}"},
    },
}


def normalize_error_message(error: str) -> str:
    """Normalize an error message for consistent pattern matching."""
    # Lowercase, collapse whitespace, strip timestamps
    text = error.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\[\d{4}-\d{2}-\d{2}.*?\]\s*", "", text)  # strip timestamps
    return text


def extract_error_pattern(error: str, stderr: str = "") -> tuple[str, dict[str, str]]:
    """Extract the error pattern type and context from an error message.

    Returns:
        (pattern_type, context_dict) — e.g., ("missing_flag", {"flag": "--name"})
        ("unknown", {}) if no pattern matches.
    """
    combined = normalize_error_message(f"{error} {stderr}")

    for pattern_name, pattern_info in ERROR_PATTERNS.items():
        match = re.search(pattern_info["regex"], combined, re.IGNORECASE)
        if match:
            try:
                context = pattern_info["extract"](match)
            except (IndexError, AttributeError):
                context = {}
            return pattern_name, context

    return "unknown", {}


def compute_pattern_hash(pattern_type: str, context: dict[str, str]) -> str:
    """Compute a stable hash for an error pattern (for deduplication)."""
    key = f"{pattern_type}:{json.dumps(context, sort_keys=True)}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


# ── Data Classes ──


@dataclass
class ErrorPattern:
    """A tracked error pattern with occurrence count."""
    pattern_type: str
    context: dict[str, str]
    hash: str
    count: int = 0
    first_seen: str = ""
    last_seen: str = ""
    sample_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_type": self.pattern_type,
            "context": self.context,
            "hash": self.hash,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "sample_errors": self.sample_errors[:3],  # Keep max 3 samples
        }


@dataclass
class ForbiddenRule:
    """A rule that prevents a specific class of errors."""
    rule_id: str
    pattern_type: str
    description: str
    forbidden_action: str
    suggested_fix: str
    context: dict[str, str]
    occurrence_count: int
    created_at: str = ""
    enabled: bool = True

    def to_markdown(self) -> str:
        """Format as a markdown rule entry."""
        ctx = f" (context: {self.context})" if self.context else ""
        return (
            f"- **[{self.rule_id}]** {self.description}{ctx}\n"
            f"  - Forbidden: `{self.forbidden_action}`\n"
            f"  - Fix: {self.suggested_fix}\n"
            f"  - Occurrences: {self.occurrence_count}\n"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "forbidden_action": self.forbidden_action,
            "suggested_fix": self.suggested_fix,
            "context": self.context,
            "occurrence_count": self.occurrence_count,
            "created_at": self.created_at,
            "enabled": self.enabled,
        }


# ── Rule Generation Logic ──

# Maps pattern types to rule generation strategies
RULE_GENERATORS = {
    "missing_flag": lambda ctx, count: ForbiddenRule(
        rule_id=f"MISSING_FLAG_{ctx.get('flag', 'unknown').lstrip('-').upper()}",
        pattern_type="missing_flag",
        description=f"Missing required flag {ctx.get('flag', '?')}",
        forbidden_action=f"Omitting {ctx.get('flag', '?')} in CLI commands",
        suggested_fix=f"Always include {ctx.get('flag', '?')} parameter",
        context=ctx,
        occurrence_count=count,
    ),
    "invalid_value": lambda ctx, count: ForbiddenRule(
        rule_id=f"INVALID_VALUE_{ctx.get('flag', 'unknown').lstrip('-').upper()}",
        pattern_type="invalid_value",
        description=f"Invalid value for {ctx.get('flag', '?')}: '{ctx.get('value', '?')}'",
        forbidden_action=f"Using invalid value '{ctx.get('value', '?')}' for {ctx.get('flag', '?')}",
        suggested_fix=f"Check valid choices for {ctx.get('flag', '?')} before using",
        context=ctx,
        occurrence_count=count,
    ),
    "negative_dimension": lambda ctx, count: ForbiddenRule(
        rule_id=f"NEGATIVE_DIM_{ctx.get('param', 'unknown').upper()}",
        pattern_type="negative_dimension",
        description=f"Negative or zero dimension for {ctx.get('param', '?')}",
        forbidden_action=f"Setting {ctx.get('param', '?')} to negative or zero value",
        suggested_fix=f"Ensure {ctx.get('param', '?')} > 0 (use abs() or clamp to minimum 0.1)",
        context=ctx,
        occurrence_count=count,
    ),
    "unknown_object": lambda ctx, count: ForbiddenRule(
        rule_id=f"UNKNOWN_OBJ_{ctx.get('object', 'unknown').upper()}",
        pattern_type="unknown_object",
        description=f"Referencing non-existent object '{ctx.get('object', '?')}'",
        forbidden_action=f"Referencing object '{ctx.get('object', '?')}' before creation",
        suggested_fix="Verify element exists before referencing; use validate_element_reference()",
        context=ctx,
        occurrence_count=count,
    ),
    "missing_document": lambda ctx, count: ForbiddenRule(
        rule_id="MISSING_DOCUMENT",
        pattern_type="missing_document",
        description="Operation requires an active document",
        forbidden_action="Running part/operation commands without creating a document first",
        suggested_fix="Always create document (fc document new) before any part operations",
        context=ctx,
        occurrence_count=count,
    ),
    "file_exists": lambda ctx, count: ForbiddenRule(
        rule_id="FILE_EXISTS_NO_OVERWRITE",
        pattern_type="file_exists",
        description="Export failed because file already exists",
        forbidden_action="Exporting without --overwrite flag when file exists",
        suggested_fix="Add --overwrite flag to export commands, or check file existence first",
        context=ctx,
        occurrence_count=count,
    ),
    "wrong_type": lambda ctx, count: ForbiddenRule(
        rule_id=f"WRONG_TYPE_{ctx.get('type', 'unknown').upper()}",
        pattern_type="wrong_type",
        description=f"Unknown part/primitive type '{ctx.get('type', '?')}'",
        forbidden_action=f"Using unsupported type '{ctx.get('type', '?')}'",
        suggestion_fix="Use valid FreeCAD types: box, cylinder, sphere, cone, torus, wedge, helix, ellipsoid, spiral",
        context=ctx,
        occurrence_count=count,
    ),
    "missing_param": lambda ctx, count: ForbiddenRule(
        rule_id=f"MISSING_PARAM_{ctx.get('param', 'unknown').lstrip('-').upper()}",
        pattern_type="missing_param",
        description=f"Missing required parameter {ctx.get('param', '?')}",
        forbidden_action=f"Omitting required parameter {ctx.get('param', '?')}",
        suggested_fix=f"Always include {ctx.get('param', '?')} in commands that require it",
        context=ctx,
        occurrence_count=count,
    ),
}


def generate_rule(pattern_type: str, context: dict[str, str], count: int) -> ForbiddenRule | None:
    """Generate a forbidden rule from an error pattern."""
    generator = RULE_GENERATORS.get(pattern_type)
    if generator is None:
        return None
    rule = generator(context, count)
    rule.created_at = datetime.now().isoformat()
    return rule


# ── Error Rules Engine ──


class ErrorRulesEngine:
    """Main engine that tracks error patterns and auto-generates forbidden rules.

    Workflow:
    1. record_error() — called by Corrector when an error occurs
    2. Patterns are counted; when count >= threshold, a rule is generated
    3. Rules are persisted to docs/ERROR_RULES.md
    4. get_active_rules() — called by Planner to inject forbidden rules
    5. export_rules() / import_rules() — cross-session persistence
    """

    DEFAULT_THRESHOLD = 3  # Occurrences before a rule is auto-generated

    def __init__(self, rules_path: str | Path | None = None,
                 threshold: int = DEFAULT_THRESHOLD):
        self._threshold = threshold
        self._rules_path = Path(rules_path) if rules_path else None
        self._patterns: dict[str, ErrorPattern] = {}  # hash -> ErrorPattern
        self._rules: dict[str, ForbiddenRule] = {}  # rule_id -> ForbiddenRule
        self._rule_counter = 0

        # Load existing rules if path exists
        if self._rules_path and self._rules_path.exists():
            self._load_rules()

    @property
    def threshold(self) -> int:
        return self._threshold

    @property
    def patterns(self) -> dict[str, ErrorPattern]:
        return dict(self._patterns)

    @property
    def rules(self) -> dict[str, ForbiddenRule]:
        return dict(self._rules)

    @property
    def active_rules(self) -> list[ForbiddenRule]:
        """Get all enabled rules."""
        return [r for r in self._rules.values() if r.enabled]

    @property
    def pattern_count(self) -> int:
        return len(self._patterns)

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def record_error(self, error: str, stderr: str = "") -> ForbiddenRule | None:
        """Record an error occurrence. Returns a new rule if threshold reached.

        Args:
            error: The error message from TaskResult.error
            stderr: The stderr from TaskResult.stderr

        Returns:
            A new ForbiddenRule if this error pushed the count to threshold,
            None otherwise.
        """
        pattern_type, context = extract_error_pattern(error, stderr)
        pattern_hash = compute_pattern_hash(pattern_type, context)

        now = datetime.now().isoformat()

        # Update or create pattern
        if pattern_hash in self._patterns:
            p = self._patterns[pattern_hash]
            p.count += 1
            p.last_seen = now
            if len(p.sample_errors) < 3:
                p.sample_errors.append(error[:200])
        else:
            self._patterns[pattern_hash] = ErrorPattern(
                pattern_type=pattern_type,
                context=context,
                hash=pattern_hash,
                count=1,
                first_seen=now,
                last_seen=now,
                sample_errors=[error[:200]],
            )

        # Check if threshold reached → generate rule
        p = self._patterns[pattern_hash]
        if p.count >= self._threshold:
            existing_rule = self._find_rule_by_pattern(pattern_type, context)
            if existing_rule:
                # Update occurrence count on existing rule
                existing_rule.occurrence_count = p.count
                return None
            else:
                rule = generate_rule(pattern_type, context, p.count)
                if rule:
                    self._rules[rule.rule_id] = rule
                    self._rule_counter += 1
                    logger.info(
                        f"Auto-generated forbidden rule: {rule.rule_id} "
                        f"(pattern={pattern_type}, count={p.count})"
                    )
                    return rule

        return None

    def get_active_rules_text(self) -> str:
        """Get formatted text of all active rules for injection into prompts."""
        rules = self.active_rules
        if not rules:
            return ""

        lines = ["## Active Forbidden Rules (Auto-Learned)\n"]
        lines.append(f"Total: {len(rules)} rules from {self.pattern_count} error patterns\n")
        for rule in sorted(rules, key=lambda r: r.occurrence_count, reverse=True):
            lines.append(rule.to_markdown())
        return "\n".join(lines)

    def get_rules_summary(self) -> dict[str, Any]:
        """Get a JSON-serializable summary of rules and patterns."""
        return {
            "total_patterns": len(self._patterns),
            "total_rules": len(self._rules),
            "active_rules": len(self.active_rules),
            "patterns": {h: p.to_dict() for h, p in self._patterns.items()},
            "rules": {rid: r.to_dict() for rid, r in self._rules.items()},
        }

    def export_rules(self, path: str | Path | None = None) -> Path:
        """Export rules to a JSON file for cross-session persistence."""
        export_path = Path(path) if path else self._rules_path
        if not export_path:
            raise ValueError("No path specified for rule export")

        export_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.get_rules_summary()
        data["exported_at"] = datetime.now().isoformat()

        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported {self.rule_count} rules to {export_path}")
        return export_path

    def import_rules(self, path: str | Path) -> int:
        """Import rules from a JSON file.

        Returns:
            Number of rules imported.
        """
        import_path = Path(path)
        if not import_path.exists():
            logger.warning(f"Rules file not found: {import_path}")
            return 0

        with open(import_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for rid, rdata in data.get("rules", {}).items():
            if rid not in self._rules:
                self._rules[rid] = ForbiddenRule(
                    rule_id=rdata["rule_id"],
                    pattern_type=rdata["pattern_type"],
                    description=rdata["description"],
                    forbidden_action=rdata["forbidden_action"],
                    suggested_fix=rdata["suggested_fix"],
                    context=rdata.get("context", {}),
                    occurrence_count=rdata.get("occurrence_count", 0),
                    created_at=rdata.get("created_at", ""),
                    enabled=rdata.get("enabled", True),
                )
                count += 1

        # Also import patterns
        for h, pdata in data.get("patterns", {}).items():
            if h not in self._patterns:
                self._patterns[h] = ErrorPattern(
                    pattern_type=pdata["pattern_type"],
                    context=pdata.get("context", {}),
                    hash=pdata.get("hash", h),
                    count=pdata.get("count", 0),
                    first_seen=pdata.get("first_seen", ""),
                    last_seen=pdata.get("last_seen", ""),
                    sample_errors=pdata.get("sample_errors", []),
                )

        logger.info(f"Imported {count} rules from {import_path}")
        return count

    def save_as_markdown(self, path: str | Path | None = None) -> Path:
        """Save active rules as a human-readable markdown file."""
        md_path = Path(path) if path else (
            self._rules_path.with_suffix(".md") if self._rules_path else None
        )
        if not md_path:
            raise ValueError("No path specified for markdown export")

        md_path.parent.mkdir(parents=True, exist_ok=True)

        rules = self.active_rules
        lines = [
            "# ERROR_RULES — Auto-Learned Forbidden Rules",
            "",
            f"> Auto-maintained by ErrorRulesEngine.",
            f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> Total rules: {len(rules)} from {len(self._patterns)} error patterns",
            "",
            "---",
            "",
        ]

        if not rules:
            lines.append("No forbidden rules yet. Rules are auto-generated when")
            lines.append("the same error pattern occurs >= 3 times.")
        else:
            # Group by pattern type
            by_type: dict[str, list[ForbiddenRule]] = {}
            for rule in rules:
                by_type.setdefault(rule.pattern_type, []).append(rule)

            for ptype, type_rules in sorted(by_type.items()):
                lines.append(f"## {ptype.replace('_', ' ').title()}\n")
                for rule in sorted(type_rules, key=lambda r: r.occurrence_count, reverse=True):
                    lines.append(rule.to_markdown())
                lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## How Rules Work")
        lines.append("")
        lines.append("1. Each time a CLI command fails, the error pattern is extracted")
        lines.append("2. When the same pattern occurs >= 3 times, a forbidden rule is auto-generated")
        lines.append("3. Active rules are injected into Planner prompts to prevent recurrence")
        lines.append("4. Rules can be exported/imported for cross-session persistence")
        lines.append("")
        lines.append("## Valid Part Types")
        lines.append("")
        lines.append("`box`, `cylinder`, `sphere`, `cone`, `torus`, `wedge`, `helix`, `ellipsoid`, `spiral`")
        lines.append("")
        lines.append("## Valid Planes")
        lines.append("")
        lines.append("`XY`, `XZ`, `YZ`")
        lines.append("")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Saved {len(rules)} rules to {md_path}")
        return md_path

    def reset_pattern(self, pattern_hash: str) -> bool:
        """Reset a specific error pattern's count (e.g., after fixing the root cause)."""
        if pattern_hash in self._patterns:
            self._patterns[pattern_hash].count = 0
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a specific rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Re-enable a specific rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            return True
        return False

    # ── Private Methods ──

    def _find_rule_by_pattern(self, pattern_type: str,
                              context: dict[str, str]) -> ForbiddenRule | None:
        """Find an existing rule matching the same pattern type and context."""
        for rule in self._rules.values():
            if (rule.pattern_type == pattern_type
                    and rule.context == context
                    and rule.enabled):
                return rule
        return None

    def _load_rules(self) -> None:
        """Load rules from the JSON file."""
        try:
            self.import_rules(self._rules_path)
        except Exception as e:
            logger.warning(f"Failed to load rules from {self._rules_path}: {e}")
