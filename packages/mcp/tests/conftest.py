"""Pytest configuration and shared fixtures for fc-mcp tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class MockBackend:
    """Mock backend that simulates FreeCAD operations without requiring FreeCAD."""

    def __init__(self, backend_type: str = "headless", **kwargs):
        self.backend_type = backend_type
        self.connected = False
        self.objects: dict[str, dict] = {}

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def add_box(self, name: str, length: float, width: float, height: float, position=None):
        from fc_core.types import ToolResponse
        self.objects[name] = {
            "type": "Box",
            "name": name,
            "length": length,
            "width": width,
            "height": height,
        }
        return ToolResponse.ok("create_box", self.objects[name], f"Box '{name}' created")

    def add_cylinder(self, name: str, radius: float, height: float, position=None):
        from fc_core.types import ToolResponse
        self.objects[name] = {
            "type": "Cylinder",
            "name": name,
            "radius": radius,
            "height": height,
        }
        return ToolResponse.ok("create_cylinder", self.objects[name], f"Cylinder '{name}' created")

    def add_sphere(self, name: str, radius: float, position=None):
        from fc_core.types import ToolResponse
        self.objects[name] = {
            "type": "Sphere",
            "name": name,
            "radius": radius,
        }
        return ToolResponse.ok("create_sphere", self.objects[name], f"Sphere '{name}' created")

    def add_cone(self, name: str, radius1: float, radius2: float, height: float):
        from fc_core.types import ToolResponse
        self.objects[name] = {
            "type": "Cone",
            "name": name,
            "radius1": radius1,
            "radius2": radius2,
            "height": height,
        }
        return ToolResponse.ok("create_cone", self.objects[name], f"Cone '{name}' created")

    def add_torus(self, name: str, radius1: float, radius2: float):
        from fc_core.types import ToolResponse
        self.objects[name] = {
            "type": "Torus",
            "name": name,
            "radius1": radius1,
            "radius2": radius2,
        }
        return ToolResponse.ok("create_torus", self.objects[name], f"Torus '{name}' created")

    def boolean_union(self, base_name: str, tool_name: str, result_name: str = ""):
        from fc_core.types import ToolResponse
        if base_name not in self.objects:
            return ToolResponse.error("boolean_union", "OBJ_NOT_FOUND",
                                      f"Object '{base_name}' not found")
        if tool_name not in self.objects:
            return ToolResponse.error("boolean_union", "OBJ_NOT_FOUND",
                                      f"Object '{tool_name}' not found")
        rname = result_name or f"{base_name}_{tool_name}_union"
        self.objects[rname] = {
            "type": "BooleanUnion",
            "name": rname,
            "base": base_name,
            "tool": tool_name,
        }
        return ToolResponse.ok("boolean_union", self.objects[rname],
                               f"Union '{rname}' created")

    def boolean_cut(self, base_name: str, tool_name: str, result_name: str = ""):
        from fc_core.types import ToolResponse
        if base_name not in self.objects:
            return ToolResponse.error("boolean_cut", "OBJ_NOT_FOUND",
                                      f"Object '{base_name}' not found")
        if tool_name not in self.objects:
            return ToolResponse.error("boolean_cut", "OBJ_NOT_FOUND",
                                      f"Object '{tool_name}' not found")
        rname = result_name or f"{base_name}_{tool_name}_cut"
        self.objects[rname] = {
            "type": "BooleanCut",
            "name": rname,
            "base": base_name,
            "tool": tool_name,
        }
        return ToolResponse.ok("boolean_cut", self.objects[rname],
                               f"Cut '{rname}' created")

    def boolean_common(self, obj1_name: str, obj2_name: str, result_name: str = ""):
        from fc_core.types import ToolResponse
        if obj1_name not in self.objects:
            return ToolResponse.error("boolean_common", "OBJ_NOT_FOUND",
                                      f"Object '{obj1_name}' not found")
        if obj2_name not in self.objects:
            return ToolResponse.error("boolean_common", "OBJ_NOT_FOUND",
                                      f"Object '{obj2_name}' not found")
        rname = result_name or f"{obj1_name}_{obj2_name}_common"
        self.objects[rname] = {
            "type": "BooleanCommon",
            "name": rname,
            "obj1": obj1_name,
            "obj2": obj2_name,
        }
        return ToolResponse.ok("boolean_common", self.objects[rname],
                               f"Common '{rname}' created")

    def fillet_edges(self, obj_name: str, radius: float, edges=None, result_name: str = ""):
        from fc_core.types import ToolResponse
        if obj_name not in self.objects:
            return ToolResponse.error("fillet_edges", "OBJ_NOT_FOUND",
                                      f"Object '{obj_name}' not found")
        rname = result_name or f"{obj_name}_fillet"
        self.objects[rname] = {
            "type": "Fillet",
            "name": rname,
            "source": obj_name,
            "radius": radius,
        }
        return ToolResponse.ok("fillet_edges", self.objects[rname],
                               f"Fillet '{rname}' created")

    def chamfer_edges(self, obj_name: str, size: float, edges=None, result_name: str = ""):
        from fc_core.types import ToolResponse
        if obj_name not in self.objects:
            return ToolResponse.error("chamfer_edges", "OBJ_NOT_FOUND",
                                      f"Object '{obj_name}' not found")
        rname = result_name or f"{obj_name}_chamfer"
        self.objects[rname] = {
            "type": "Chamfer",
            "name": rname,
            "source": obj_name,
            "size": size,
        }
        return ToolResponse.ok("chamfer_edges", self.objects[rname],
                               f"Chamfer '{rname}' created")

    def mirror_object(self, obj_name: str, plane: str, result_name: str = ""):
        from fc_core.types import ToolResponse
        if obj_name not in self.objects:
            return ToolResponse.error("mirror", "OBJ_NOT_FOUND",
                                      f"Object '{obj_name}' not found")
        rname = result_name or f"{obj_name}_mirror"
        self.objects[rname] = {
            "type": "Mirror",
            "name": rname,
            "source": obj_name,
            "plane": plane,
        }
        return ToolResponse.ok("mirror", self.objects[rname],
                               f"Mirror '{rname}' created")

    def scale_object(self, obj_name: str, factor, result_name: str = ""):
        from fc_core.types import ToolResponse
        if obj_name not in self.objects:
            return ToolResponse.error("scale", "OBJ_NOT_FOUND",
                                      f"Object '{obj_name}' not found")
        rname = result_name or f"{obj_name}_scaled"
        self.objects[rname] = {
            "type": "Scale",
            "name": rname,
            "source": obj_name,
            "factor": factor,
        }
        return ToolResponse.ok("scale", self.objects[rname],
                               f"Scale '{rname}' created")

    def object_create(self, type_id: str, name: str, props: dict | None = None):
        from fc_core.types import ToolResponse
        self.objects[name] = {
            "type": type_id,
            "name": name,
            "properties": props or {},
        }
        return ToolResponse.ok("object_create", self.objects[name],
                               f"Object '{name}' of type '{type_id}' created")

    def object_delete(self, obj_name: str):
        from fc_core.types import ToolResponse
        if obj_name not in self.objects:
            return ToolResponse.error("delete", "OBJ_NOT_FOUND",
                                      f"Object '{obj_name}' not found")
        del self.objects[obj_name]
        return ToolResponse.ok("delete", {"name": obj_name},
                               f"Object '{obj_name}' deleted")

    def execute_code(self, code: str):
        from fc_core.types import ToolResponse
        return ToolResponse.ok("execute_code", {"code": code},
                               "Code executed successfully")

    # ── Document operations ------------------------------------------------
    def document_new(self, name: str = "Untitled"):
        from fc_core.types import ToolResponse
        return ToolResponse.ok("document_new",
                               {"name": name, "label": name},
                               f"Document '{name}' created")

    def document_open(self, file_path: str):
        from fc_core.types import ToolResponse
        return ToolResponse.ok("document_open",
                               {"name": "TestDoc", "label": "TestDoc",
                                "file_path": file_path},
                               f"Opened: {file_path}")

    def document_save(self, file_path: str | None = None):
        from fc_core.types import ToolResponse
        path = file_path or "untitled.FCStd"
        return ToolResponse.ok("document_save",
                               {"file_path": path},
                               f"Saved: {path}")

    def document_info(self):
        from fc_core.types import ToolResponse
        return ToolResponse.ok("document_info",
                               {"name": "TestDoc", "label": "TestDoc",
                                "objects_count": 0, "objects": []})

    def document_close(self):
        from fc_core.types import ToolResponse
        return ToolResponse.ok("document_close",
                               {"name": "TestDoc"},
                               "Closed: TestDoc")

    # ── Object / query operations ------------------------------------------
    def object_list(self):
        from fc_core.types import ToolResponse
        return ToolResponse.ok("object_list",
                               {"objects": [], "count": 0})

    def object_get(self, obj_name: str):
        from fc_core.types import ToolResponse
        return ToolResponse.ok("object_get",
                               {"name": obj_name, "label": obj_name,
                                "type_id": "Part::Box"})

    def get_version(self):
        return "0.21.2"

    # ── Sketch operations --------------------------------------------------
    def sketch_new(self, plane: str = "XY", offset: float = 0.0,
                   name: str = "Sketch"):
        from fc_core.types import ToolResponse
        return ToolResponse.ok("sketch_new",
                               {"name": name, "plane": plane, "offset": offset},
                               f"Sketch '{name}' created on {plane} plane")

    # ── Export -------------------------------------------------------------
    def export(self, file_path: str, fmt: str = ""):
        from fc_core.types import ToolResponse
        fmt = fmt or "unknown"
        return ToolResponse.ok("export",
                               {"output": file_path, "format": fmt},
                               f"Exported {fmt}: {file_path}")


@pytest.fixture
def mock_backend():
    """Provide a fresh MockBackend instance."""
    return MockBackend()


@pytest.fixture
def mock_backend_factory(mock_backend):
    """Patch _get_backend to return the mock backend (geometry module)."""
    def _factory(backend_type="headless", **kwargs):
        return mock_backend

    with patch("fc_mcp.tools.geometry._get_backend", side_effect=_factory):
        yield mock_backend


@pytest.fixture
def mock_backend_factory_document(mock_backend):
    """Patch _get_backend to return the mock backend (document module)."""
    def _factory(backend_type="headless", **kwargs):
        return mock_backend

    with patch("fc_mcp.tools.document._get_backend", side_effect=_factory):
        yield mock_backend


@pytest.fixture
def mock_backend_factory_export(mock_backend):
    """Patch _get_backend to return the mock backend (export module)."""
    def _factory(backend_type="headless", **kwargs):
        return mock_backend

    with patch("fc_mcp.tools.export._get_backend", side_effect=_factory):
        yield mock_backend


@pytest.fixture
def mock_backend_factory_execute(mock_backend):
    """Patch _get_backend to return the mock backend (execute module)."""
    def _factory(backend_type="headless", **kwargs):
        return mock_backend

    with patch("fc_mcp.tools.execute._get_backend", side_effect=_factory):
        yield mock_backend


@pytest.fixture
def mock_backend_factory_query(mock_backend):
    """Patch _get_backend to return the mock backend (query module)."""
    def _factory(backend_type="headless", **kwargs):
        return mock_backend

    with patch("fc_mcp.tools.query._get_backend", side_effect=_factory):
        yield mock_backend


@pytest.fixture
def mock_backend_factory_sketch(mock_backend):
    """Patch _get_backend to return the mock backend (sketch module)."""
    def _factory(backend_type="headless", **kwargs):
        return mock_backend

    with patch("fc_mcp.tools.sketch._get_backend", side_effect=_factory):
        yield mock_backend


@pytest.fixture
def registered_tools():
    """Return the list of registered MCP tool names."""
    from fc_mcp.server import mcp
    tools = mcp._tool_manager._tools
    return list(tools.keys())
