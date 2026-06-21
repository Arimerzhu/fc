"""Tests for fc_core security module.

Covers:
- validate_name: snapshot/object name validation
- validate_path: general file path validation
- validate_export_path: export output path validation
- validate_import_path: import input path validation
- Path traversal attack prevention
- Edge cases: null bytes, illegal chars, empty inputs
"""

import os
import re
import tempfile

import pytest

from fc_core.security import (
    SecurityError,
    validate_export_path,
    validate_import_path,
    validate_name,
    validate_path,
)


# ---------------------------------------------------------------------------
# validate_name tests
# ---------------------------------------------------------------------------

class TestValidateName:
    """Tests for name validation (snapshots, objects, etc.)."""

    def test_simple_name(self):
        assert validate_name("mysnapshot") == "mysnapshot"

    def test_name_with_hyphens(self):
        assert validate_name("my-snapshot-01") == "my-snapshot-01"

    def test_name_with_underscores(self):
        assert validate_name("my_snapshot_01") == "my_snapshot_01"

    def test_name_all_uppercase(self):
        assert validate_name("UPPERCASE") == "UPPERCASE"

    def test_name_mixed(self):
        assert validate_name("My_Snapshot-123") == "My_Snapshot-123"

    def test_empty_name_raises(self):
        with pytest.raises(SecurityError, match="Empty"):
            validate_name("")

    def test_path_traversal_in_name(self):
        with pytest.raises(SecurityError, match="Invalid name"):
            validate_name("../../etc/passwd")

    def test_dot_in_name(self):
        with pytest.raises(SecurityError, match="Invalid name"):
            validate_name("file.txt")

    def test_space_in_name(self):
        with pytest.raises(SecurityError, match="Invalid name"):
            validate_name("my snapshot")

    def test_special_chars_in_name(self):
        for ch in ["/", "\\", ":", "*", "?", '"', "<", ">", "|", "@", "#"]:
            with pytest.raises(SecurityError, match="Invalid name"):
                validate_name(f"bad{ch}name")

    def test_name_with_context(self):
        """Context parameter should appear in error message."""
        with pytest.raises(SecurityError, match="snapshot"):
            validate_name("bad/name", context="snapshot")

    def test_security_error_has_code(self):
        """SecurityError should have code and suggestion attributes."""
        with pytest.raises(SecurityError) as exc_info:
            validate_name("bad/name")
        assert exc_info.value.code == "INVALID_NAME"
        assert "alphanumeric" in exc_info.value.suggestion

    def test_security_error_is_value_error(self):
        """SecurityError is a subclass of ValueError."""
        with pytest.raises(ValueError):
            validate_name("..")

    def test_unicode_rejected(self):
        """Unicode characters should be rejected."""
        with pytest.raises(SecurityError):
            validate_name("snapshot_é")

    def test_newline_in_name(self):
        """Newline character should be rejected."""
        with pytest.raises(SecurityError):
            validate_name("name\nwith\nnewlines")

    def test_single_char_name(self):
        """Single valid character should be allowed."""
        assert validate_name("a") == "a"

    def test_numeric_name(self):
        """Purely numeric names should be allowed."""
        assert validate_name("12345") == "12345"


# ---------------------------------------------------------------------------
# validate_path tests
# ---------------------------------------------------------------------------

class TestValidatePath:
    """Tests for general file path validation."""

    def test_simple_relative_path(self):
        result = validate_path("test.step")
        assert os.path.isabs(result)
        assert result.endswith(os.path.join("", "test.step"))

    def test_absolute_path(self, tmp_path):
        p = tmp_path / "output.step"
        result = validate_path(str(p))
        assert os.path.isabs(result)

    def test_path_traversal_rejected(self):
        with pytest.raises(SecurityError, match="traversal"):
            validate_path("../../etc/passwd")

    def test_path_traversal_in_middle(self):
        with pytest.raises(SecurityError, match="traversal"):
            validate_path("output/../../etc/passwd")

    def test_path_traversal_with_backslashes(self):
        """Backslash traversal should also be caught."""
        with pytest.raises(SecurityError):
            validate_path("..\\..\\etc\\passwd")

    def test_null_byte_rejected(self):
        with pytest.raises(SecurityError, match="Null byte"):
            validate_path("test\x00.step")

    def test_empty_path_rejected(self):
        with pytest.raises(SecurityError, match="Empty path"):
            validate_path("")

    def test_illegal_chars_rejected(self):
        for ch in ['<', '>', '|', '?', '*']:
            with pytest.raises(SecurityError, match="Illegal characters"):
                validate_path(f"test{ch}file.step")

    def test_must_exist_with_missing_file(self):
        with pytest.raises(FileNotFoundError):
            validate_path("/nonexistent/path/to/file.step", must_exist=True)

    def test_must_exist_with_existing_file(self, tmp_path):
        p = tmp_path / "test.step"
        p.write_text("test")
        result = validate_path(str(p), must_exist=True)
        assert os.path.isabs(result)

    def test_allowed_extensions_valid(self, tmp_path):
        p = tmp_path / "test.step"
        result = validate_path(str(p), allowed_extensions=[".step", ".stl"])
        assert os.path.isabs(result)

    def test_allowed_extensions_invalid(self, tmp_path):
        p = tmp_path / "test.exe"
        with pytest.raises(SecurityError, match="extension"):
            validate_path(str(p), allowed_extensions=[".step", ".stl"])

    def test_allowed_extensions_case_insensitive(self, tmp_path):
        p = tmp_path / "test.STEP"
        result = validate_path(str(p), allowed_extensions=[".step"])
        assert os.path.isabs(result)

    def test_allowed_extensions_none_means_any(self):
        result = validate_path("test.anything")
        assert os.path.isabs(result)

    def test_dot_dot_encoded(self):
        """Even tricky traversal attempts should be caught."""
        with pytest.raises(SecurityError):
            validate_path("foo/../bar")

    def test_traversal_at_end(self):
        with pytest.raises(SecurityError):
            validate_path("output/..")

    def test_security_error_is_value_error(self):
        """SecurityError is a subclass of ValueError."""
        with pytest.raises(ValueError):
            validate_path("..")

    def test_normal_path_without_extension(self):
        """Paths without extensions should be fine."""
        result = validate_path("output/noext")
        assert os.path.isabs(result)


# ---------------------------------------------------------------------------
# validate_export_path tests
# ---------------------------------------------------------------------------

class TestValidateExportPath:
    """Tests for export output path validation."""

    def test_valid_export_path(self, tmp_path):
        p = tmp_path / "output.step"
        result = validate_export_path(str(p), overwrite=False)
        assert os.path.isabs(result)

    def test_existing_file_without_overwrite(self, tmp_path):
        p = tmp_path / "exists.step"
        p.write_text("already here")
        with pytest.raises(SecurityError, match="exists"):
            validate_export_path(str(p), overwrite=False)

    def test_existing_file_with_overwrite(self, tmp_path):
        p = tmp_path / "exists.step"
        p.write_text("already here")
        result = validate_export_path(str(p), overwrite=True)
        assert os.path.isabs(result)

    def test_traversal_rejected(self):
        with pytest.raises(SecurityError, match="traversal"):
            validate_export_path("../../etc/passwd", overwrite=True)

    def test_allowed_extensions_filter(self, tmp_path):
        p = tmp_path / "output.step"
        result = validate_export_path(str(p), allowed_extensions=[".step", ".stl"])
        assert os.path.isabs(result)

    def test_disallowed_extension(self, tmp_path):
        p = tmp_path / "output.exe"
        with pytest.raises(SecurityError, match="extension"):
            validate_export_path(str(p), allowed_extensions=[".step", ".stl"])

    def test_nonexistent_parent_directory(self, tmp_path):
        """Export to a path where parent doesn't exist yet should be fine."""
        p = tmp_path / "newdir" / "output.step"
        result = validate_export_path(str(p), overwrite=False)
        assert os.path.isabs(result)


# ---------------------------------------------------------------------------
# validate_import_path tests
# ---------------------------------------------------------------------------

class TestValidateImportPath:
    """Tests for import input path validation."""

    def test_existing_file(self, tmp_path):
        p = tmp_path / "model.step"
        p.write_text("test content")
        result = validate_import_path(str(p))
        assert os.path.isabs(result)

    def test_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            validate_import_path(str(tmp_path / "nonexistent.step"))

    def test_traversal_rejected(self):
        with pytest.raises(SecurityError, match="traversal"):
            validate_import_path("../../etc/passwd")

    def test_allowed_extensions(self, tmp_path):
        p = tmp_path / "model.step"
        p.write_text("test")
        result = validate_import_path(str(p), allowed_extensions=[".step", ".stl"])
        assert os.path.isabs(result)

    def test_disallowed_extension(self, tmp_path):
        p = tmp_path / "model.exe"
        p.write_text("test")
        with pytest.raises(SecurityError, match="extension"):
            validate_import_path(str(p), allowed_extensions=[".step"])


# ---------------------------------------------------------------------------
# Path traversal attack vector tests
# ---------------------------------------------------------------------------

class TestPathTraversalAttacks:
    """Systematic tests for path traversal attack vectors."""

    @pytest.mark.parametrize("malicious_path", [
        "../../etc/passwd",
        "../../../etc/passwd",
        "output/../../etc/passwd",
        "foo/bar/../../../etc/passwd",
        "..\\..\\etc\\passwd",
        "output\\..\\..\\etc\\passwd",
        "../../../../../../../../etc/passwd",
        "....//....//etc/passwd",
        "foo/..",
        "..",
        "a/../..",
        "a/b/../../..",
    ])
    def test_traversal_attacks_rejected(self, malicious_path):
        """All known path traversal patterns should be rejected."""
        with pytest.raises((SecurityError, FileNotFoundError)):
            validate_path(malicious_path)

    @pytest.mark.parametrize("malicious_path", [
        "../../etc/passwd",
        "../../../etc/passwd",
        "output/../../etc/passwd",
        "foo/bar/../../../etc/passwd",
    ])
    def test_traversal_in_export_rejected(self, malicious_path):
        """Traversal attacks should be rejected for export paths."""
        with pytest.raises(SecurityError):
            validate_export_path(malicious_path, overwrite=True)

    @pytest.mark.parametrize("malicious_path", [
        "../../etc/passwd",
        "../../../etc/passwd",
        "output/../../etc/passwd",
    ])
    def test_traversal_in_import_rejected(self, malicious_path):
        """Traversal attacks should be rejected for import paths."""
        with pytest.raises((SecurityError, FileNotFoundError)):
            validate_import_path(malicious_path)

    @pytest.mark.parametrize("malicious_name", [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\config\\sam",
        "normal/../../../etc/shadow",
        ".hidden",
        "name with spaces",
        "name/with/slashes",
        "name\\with\\backslashes",
        "name:with:colons",
        "name*with*stars",
        "name?with?questions",
        'name"with"quotes',
        "name<with>angles",
        "name|with|pipes",
    ])
    def test_snapshot_name_attacks_rejected(self, malicious_name):
        """All known name-based attacks should be rejected for snapshot names."""
        with pytest.raises(SecurityError):
            validate_name(malicious_name)


# ---------------------------------------------------------------------------
# SecurityError tests
# ---------------------------------------------------------------------------

class TestSecurityError:
    """Tests for the SecurityError exception class."""

    def test_default_code(self):
        e = SecurityError("test error")
        assert e.code == "SECURITY_VIOLATION"
        assert e.suggestion == ""

    def test_custom_code(self):
        e = SecurityError("test", code="CUSTOM_CODE")
        assert e.code == "CUSTOM_CODE"

    def test_with_suggestion(self):
        e = SecurityError("test", suggestion="Try this fix")
        assert e.suggestion == "Try this fix"

    def test_is_value_error(self):
        e = SecurityError("test")
        assert isinstance(e, ValueError)

    def test_str_message(self):
        e = SecurityError("test message")
        assert str(e) == "test message"
