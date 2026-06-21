"""Security utilities for FreeCAD CLI.

Provides path validation, name sanitization, and input validation
to prevent path traversal attacks and injection vulnerabilities.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional


# Pattern for valid snapshot/document names: alphanumeric, hyphens, underscores
_SAFE_NAME_RE = re.compile(r'^[A-Za-z0-9_\-]+$')

# Characters that are never allowed in any file path we accept
_FORCED_ILLEGAL_CHARS = set('<>|?*')


class SecurityError(ValueError):
    """Raised when a security validation check fails."""

    def __init__(self, message: str, code: str = "SECURITY_VIOLATION",
                 suggestion: str = ""):
        super().__init__(message)
        self.code = code
        self.suggestion = suggestion


def validate_name(name: str, context: str = "name") -> str:
    """Validate a name string (snapshot name, object name, etc.).

    Only allows alphanumeric characters, hyphens, and underscores.
    Prevents path traversal via names like '../../etc/passwd'.

    Args:
        name: The name to validate.
        context: Description of what is being validated (for error messages).

    Returns:
        The validated name (unchanged).

    Raises:
        SecurityError: If the name contains invalid characters.
    """
    if not name:
        raise SecurityError(
            f"Empty {context} is not allowed",
            code="INVALID_NAME",
            suggestion=f"Provide a non-empty {context} using only "
                       "alphanumeric characters, hyphens, and underscores",
        )
    if not _SAFE_NAME_RE.match(name):
        raise SecurityError(
            f"Invalid {context}: {name}",
            code="INVALID_NAME",
            suggestion="Use only alphanumeric characters, hyphens, and underscores",
        )
    return name


def validate_path(path: str, must_exist: bool = False,
                  allow_write: bool = True,
                  allowed_extensions: Optional[list[str]] = None) -> str:
    """Validate a file path for security.

    - Resolves to absolute path
    - Checks for path traversal (..)
    - Optionally checks file existence
    - Optionally checks file extension against a whitelist

    Args:
        path: The file path to validate.
        must_exist: If True, raise FileNotFoundError when file does not exist.
        allow_write: If False, raise SecurityError if the path is read-only.
        allowed_extensions: Optional list of allowed extensions (e.g. ['.step', '.stl']).

    Returns:
        Sanitized absolute path.

    Raises:
        SecurityError: If path traversal or other security issue is detected.
        FileNotFoundError: If must_exist=True and the file does not exist.
    """
    if not path:
        raise SecurityError(
            "Empty path is not allowed",
            code="INVALID_PATH",
            suggestion="Provide a valid file path",
        )

    # Check for traversal sequences in the raw input
    if ".." in path:
        raise SecurityError(
            f"Path traversal detected: {path}",
            code="PATH_TRAVERSAL",
            suggestion="Remove '..' sequences from the path",
        )

    # Check for null bytes
    if "\x00" in path:
        raise SecurityError(
            f"Null byte detected in path: {repr(path)}",
            code="INVALID_PATH",
            suggestion="Remove null bytes from the path",
        )

    # Check for forced illegal characters
    found_illegal = _FORCED_ILLEGAL_CHARS.intersection(set(path))
    if found_illegal:
        raise SecurityError(
            f"Illegal characters in path: {found_illegal}",
            code="INVALID_PATH",
            suggestion=f"Remove these characters: {''.join(sorted(found_illegal))}",
        )

    abs_path = os.path.abspath(path)

    # Double-check: resolved path should not contain '..' components
    # (catches edge cases like 'foo/../bar' which resolves to 'foo/bar'
    # but the raw input might have been crafted)
    normalized = os.path.normpath(path)
    if ".." in normalized.split(os.sep):
        raise SecurityError(
            f"Path traversal detected after normalization: {path}",
            code="PATH_TRAVERSAL",
            suggestion="Remove '..' sequences from the path",
        )

    if must_exist and not os.path.exists(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")

    if allowed_extensions is not None:
        ext = Path(abs_path).suffix.lower()
        allowed_lower = [e.lower() for e in allowed_extensions]
        if ext not in allowed_lower:
            raise SecurityError(
                f"File extension '{ext}' is not allowed. "
                f"Allowed: {', '.join(allowed_lower)}",
                code="INVALID_EXTENSION",
                suggestion=f"Use one of these extensions: {', '.join(allowed_lower)}",
            )

    return abs_path


def validate_export_path(path: str, overwrite: bool = False,
                         allowed_extensions: Optional[list[str]] = None) -> str:
    """Validate an output path for export operations.

    Combines path validation with overwrite checking.

    Args:
        path: The output file path.
        allow_extensions: Optional list of allowed extensions.

    Returns:
        Sanitized absolute path.

    Raises:
        SecurityError: If path is invalid or file exists without overwrite.
    """
    abs_path = validate_path(path, must_exist=False,
                             allowed_extensions=allowed_extensions)

    if os.path.exists(abs_path) and not overwrite:
        raise SecurityError(
            f"File exists: {abs_path}",
            code="FILE_EXISTS",
            suggestion="Use --overwrite to replace the existing file",
        )

    # Ensure the parent directory can be created
    parent = os.path.dirname(abs_path)
    if parent and not os.path.exists(parent):
        # Check that the parent path itself is not traversing
        if ".." in parent:
            raise SecurityError(
                f"Path traversal in parent directory: {parent}",
                code="PATH_TRAVERSAL",
                suggestion="Use a valid output directory",
            )

    return abs_path


def validate_import_path(path: str,
                         allowed_extensions: Optional[list[str]] = None) -> str:
    """Validate an input path for import operations.

    Args:
        path: The input file path.
        allowed_extensions: Optional list of allowed extensions.

    Returns:
        Sanitized absolute path.

    Raises:
        SecurityError: If path is invalid.
        FileNotFoundError: If the file does not exist.
    """
    return validate_path(path, must_exist=True,
                         allowed_extensions=allowed_extensions)
