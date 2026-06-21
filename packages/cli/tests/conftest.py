"""Test fixtures for fc-cli commands.

Provides MockBackend (simulates HeadlessBackend without FreeCAD),
CliRunner fixture, and helpers to patch backend creation in commands.
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import patch

import pytest

from fc_core.types import ToolResponse


class MockBackend:
    """Simulates HeadlessBackend without FreeCAD.

    Tracks call history so tests can assert what the backend was asked to do.
    Each method returns a sensible ToolResponse; callers can also pre stage
    custom responses via ``stage_response(method_name, response)``.
    """

    def __init__(self) -> None:
        self.connected: bool = False
        self.disconnected: bool = False
        self._staged: dict[str, ToolResponse] = {}
        self._calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    # ── staging -----------------------------------------------------------
    def stage_response(self, method_name: str, response: ToolResponse) -> None:
        """Pre-stage a response for a given method."""
        self._staged[method_name] = response

    # ── connection --------------------------------------------------------
    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.disconnected = True

    def is_connected(self) -> bool:
        return self.connected

    # ── helpers -----------------------------------------------------------
    def _record(self, method: str, *args: Any, **kwargs: Any) -> None:
        self._calls.append((method, args, kwargs))

    def _respond(self, method: str, default_data: dict[str, Any] | None = None,
                 default_message: str = "") -> ToolResponse:
        if method in self._staged:
            return self._staged.pop(method)
        return ToolResponse.ok(method, default_data or {}, default_message)

    @property
    def calls(self) -> list[tuple[str, tuple[Any, ...], dict[str, Any]]]:
        return list(self._calls)

    def was_called(self, method: str) -> bool:
        return any(c[0] == method for c in self._calls)

    # ── Document operations ------------------------------------------------
    def document_new(self, name: str = "Untitled") -> ToolResponse:
        self._record("document_new", name)
        return self._respond("document_new",
                             {"name": name, "label": name},
                             f"Document '{name}' created")

    def document_open(self, file_path: str) -> ToolResponse:
        self._record("document_open", file_path)
        return self._respond("document_open",
                             {"name": "TestDoc", "label": "TestDoc",
                              "file_path": file_path},
                             f"Opened: {file_path}")

    def document_save(self, file_path: str | None = None) -> ToolResponse:
        self._record("document_save", file_path)
        path = file_path or "untitled.FCStd"
        return self._respond("document_save",
                             {"saved_to": path},
                             f"Saved: {path}")

    def document_info(self) -> ToolResponse:
        self._record("document_info")
        return self._respond("document_info",
                             {"name": "TestDoc", "label": "TestDoc",
                              "objects_count": 0, "objects": []})

    def document_close(self) -> ToolResponse:
        self._record("document_close")
        return self._respond("document_close",
                             {"name": "TestDoc"},
                             "Closed: TestDoc")

    # ── Object operations --------------------------------------------------
    def object_list(self) -> ToolResponse:
        self._record("object_list")
        return self._respond("object_list",
                             {"objects": [], "count": 0})

    def object_get(self, name: str) -> ToolResponse:
        self._record("object_get", name)
        return self._respond("object_get",
                             {"name": name, "label": name, "type_id": "Part::Box"})

    def object_create(self, fc_type: str, name: str, props: dict | None = None) -> ToolResponse:
        self._record("object_create", fc_type, name, props)
        return self._respond("object_create",
                             {"name": name, "type_id": fc_type, "properties": props or {}},
                             f"Created {fc_type}: {name}")

    def object_delete(self, name: str) -> ToolResponse:
        self._record("object_delete", name)
        return self._respond("object_delete",
                             {"name": name},
                             f"Deleted: {name}")

    # ── Execute code -------------------------------------------------------
    def execute_code(self, code: str) -> ToolResponse:
        self._record("execute_code", code[:80])
        return self._respond("execute_code",
                             {"executed": True},
                             "Code executed successfully")

    # ── Boolean operations -------------------------------------------------
    def boolean_cut(self, base: str, tool: str, result_name: str) -> ToolResponse:
        self._record("boolean_cut", base, tool, result_name)
        return self._respond("boolean_cut",
                             {"result": result_name, "base": base, "tool": tool},
                             f"Cut: {base} - {tool} = {result_name}")

    def boolean_union(self, base: str, tool: str, result_name: str) -> ToolResponse:
        self._record("boolean_union", base, tool, result_name)
        return self._respond("boolean_union",
                             {"result": result_name, "base": base, "tool": tool},
                             f"Fuse: {base} + {tool} = {result_name}")

    def boolean_common(self, base: str, tool: str, result_name: str) -> ToolResponse:
        self._record("boolean_common", base, tool, result_name)
        return self._respond("boolean_common",
                             {"result": result_name, "base": base, "tool": tool},
                             f"Common: {base} & {tool} = {result_name}")

    # ── Transform / mirror / scale -----------------------------------------
    def mirror_object(self, name: str, plane: str, result_name: str) -> ToolResponse:
        self._record("mirror_object", name, plane, result_name)
        return self._respond("mirror_object",
                             {"result": result_name, "source": name, "plane": plane},
                             f"Mirrored: {name} -> {result_name} (plane={plane})")

    def scale_object(self, name: str, factor, result_name: str) -> ToolResponse:
        self._record("scale_object", name, factor, result_name)
        return self._respond("scale_object",
                             {"result": result_name, "source": name, "factor": str(factor)},
                             f"Scaled: {name} -> {result_name} (factor={factor})")

    def fillet_edges(self, name: str, radius: float, edge_list, result_name: str) -> ToolResponse:
        self._record("fillet_edges", name, radius, edge_list, result_name)
        return self._respond("fillet_edges",
                             {"result": result_name, "source": name, "radius": radius},
                             f"Fillet: {result_name} (r={radius})")

    def chamfer_edges(self, name: str, size: float, edge_list, result_name: str) -> ToolResponse:
        self._record("chamfer_edges", name, size, edge_list, result_name)
        return self._respond("chamfer_edges",
                             {"result": result_name, "source": name, "size": size},
                             f"Chamfer: {result_name} (s={size})")

    # ── Sketch operations --------------------------------------------------
    def sketch_new(self, plane: str, offset: float, name: str) -> ToolResponse:
        self._record("sketch_new", plane, offset, name)
        return self._respond("sketch_new",
                             {"name": name, "plane": plane, "offset": offset},
                             f"Sketch '{name}' created on {plane} plane")

    # ── Body operations ----------------------------------------------------
    def body_new(self, name: str) -> ToolResponse:
        self._record("body_new", name)
        return self._respond("body_new",
                             {"name": name, "label": name},
                             f"Body '{name}' created")

    def body_pad(self, body_name: str, sketch_name: str, length: float,
                 symmetric: bool = False, reversed: bool = False) -> ToolResponse:
        self._record("body_pad", body_name, sketch_name, length, symmetric, reversed)
        return self._respond("body_pad",
                             {"body": body_name, "sketch": sketch_name, "length": length},
                             f"Pad: {body_name} + {sketch_name} (L={length})")

    # ── Export -------------------------------------------------------------
    def export(self, output: str, fmt: str, verify: bool = True) -> ToolResponse:
        self._record("export", output, fmt, verify=verify)
        return self._respond("export",
                             {"output": output, "format": fmt},
                             f"Exported {fmt}: {output}")


@pytest.fixture
def mock_backend() -> MockBackend:
    """Return a fresh MockBackend instance."""
    return MockBackend()


@pytest.fixture
def runner():
    """Return a Click CliRunner with isolated filesystem."""
    from click.testing import CliRunner
    return CliRunner()


def _patch_get_backend(mock: MockBackend):
    """Patch ``_get_backend()`` inside fc_cli.commands.document so it returns *mock*.

    Returns the patch object (already started).  Caller must stop it in teardown
    or use it as a context manager.
    """
    target = "fc_cli.commands.document._get_backend"
    return patch(target, return_value=mock)
