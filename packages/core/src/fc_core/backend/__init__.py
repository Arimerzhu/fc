"""Backend abstraction layer for FreeCAD CLI.

Provides two backends:
- HeadlessBackend: Uses FreeCADCmd subprocess for headless operation
- RPCBackend: Connects to running FreeCAD GUI via XML-RPC

Both backends implement the same BackendInterface, making all commands
backend-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import tempfile
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from fc_core.geometry.operations import GeometryOpsMixin
from fc_core.types import DocumentInfo, ObjectInfo, ToolResponse, Vec3

logger = logging.getLogger(__name__)

_FREECAD_CMD_NAMES = ["freecadcmd", "FreeCADCmd", "freecadcmd.exe", "FreeCADCmd.exe"]
_FREECAD_GUI_NAMES = ["freecad", "FreeCAD", "freecad.exe", "FreeCAD.exe"]


def _install_instructions() -> str:
    return textwrap.dedent("""\
        FreeCAD console executable (FreeCADCmd) not found.

        Install FreeCAD and make sure FreeCADCmd is on your PATH:

          Windows:
            Download from https://www.freecad.org/downloads.php
            Default: C:\\Program Files\\FreeCAD*\\bin\\FreeCADCmd.exe

          macOS:
            brew install --cask freecad

          Linux:
            sudo apt install freecad
            # or: conda install -c conda-forge freecad

        You can also set FREECAD_PATH environment variable to the full path.
    """)


def find_freecad(gui_required: bool = False) -> str:
    """Locate the FreeCAD executable on the system.

    Search order:
      1. FREECAD_PATH environment variable
      2. Known executable names on PATH
      3. Common platform-specific install locations

    Returns:
        Absolute path to the FreeCAD executable.

    Raises:
        FileNotFoundError: If FreeCAD cannot be found.
    """
    env_path = os.environ.get("FREECAD_PATH")
    if env_path and os.path.isfile(env_path):
        return os.path.abspath(env_path)

    names = _FREECAD_GUI_NAMES if gui_required else _FREECAD_CMD_NAMES
    for name in names:
        which = shutil.which(name)
        if which:
            return os.path.abspath(which)

    # Platform-specific discovery
    if platform.system() == "Windows":
        import glob
        if gui_required:
            patterns = [
                "C:/Program Files/FreeCAD*/bin/freecad.exe",
                "C:/Program Files/FreeCAD*/bin/FreeCAD.exe",
                "C:/Program Files (x86)/FreeCAD*/bin/freecad.exe",
                "C:/Program Files (x86)/FreeCAD*/bin/FreeCAD.exe",
            ]
        else:
            patterns = [
                "C:/Program Files/FreeCAD*/bin/FreeCADCmd.exe",
                "C:/Program Files/FreeCAD*/bin/freecadcmd.exe",
                "C:/Program Files (x86)/FreeCAD*/bin/FreeCADCmd.exe",
            ]
        for pattern in patterns:
            matches = sorted(glob.glob(pattern), reverse=True)
            if matches:
                return os.path.abspath(matches[0])

    raise FileNotFoundError(_install_instructions())


class BackendInterface(ABC):
    """Abstract interface for FreeCAD backends.

    All backend implementations must provide these methods.
    Commands and tools use this interface, not concrete backends.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to FreeCAD."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from FreeCAD."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if backend is connected and responsive."""
        ...

    @abstractmethod
    def get_version(self) -> str:
        """Get FreeCAD version string."""
        ...

    # Document operations
    @abstractmethod
    def document_new(self, name: str = "Untitled") -> ToolResponse:
        ...

    @abstractmethod
    def document_open(self, file_path: str) -> ToolResponse:
        ...

    @abstractmethod
    def document_save(self, file_path: str | None = None) -> ToolResponse:
        ...

    @abstractmethod
    def inject_gui_data(
        self,
        file_path: str | None = None,
        view: str = "isometric",
        fit_all: bool = True,
    ) -> ToolResponse:
        """注入 GUI 视图数据并重新保存文档（仅 GUI 模式有效）。

        解决 FreeCADCmd 模式保存的 FCStd 文件缺少 GuiDocument.xml、
        相机位置、ViewProvider 设置的问题。
        """
        ...

    @abstractmethod
    def document_info(self) -> ToolResponse:
        ...

    @abstractmethod
    def document_close(self) -> ToolResponse:
        ...

    # Object operations
    @abstractmethod
    def object_list(self) -> ToolResponse:
        ...

    @abstractmethod
    def object_get(self, obj_name: str) -> ToolResponse:
        ...

    @abstractmethod
    def object_create(self, obj_type: str, obj_name: str,
                      properties: dict[str, Any] | None = None) -> ToolResponse:
        ...

    @abstractmethod
    def object_edit(self, obj_name: str,
                    properties: dict[str, Any]) -> ToolResponse:
        ...

    @abstractmethod
    def object_delete(self, obj_name: str) -> ToolResponse:
        ...

    # Sketch operations
    @abstractmethod
    def sketch_new(self, plane: str = "XY", offset: float = 0.0,
                   name: str = "") -> ToolResponse:
        ...

    # PartDesign operations
    @abstractmethod
    def body_new(self, name: str = "") -> ToolResponse:
        ...

    @abstractmethod
    def body_pad(self, body_name: str, sketch_name: str,
                 length: float = 10.0, **kwargs: Any) -> ToolResponse:
        ...

    # Boolean operations
    @abstractmethod
    def boolean_union(self, base_name: str, tool_name: str,
                      result_name: str = "") -> ToolResponse:
        ...

    @abstractmethod
    def boolean_cut(self, base_name: str, tool_name: str,
                    result_name: str = "") -> ToolResponse:
        ...

    @abstractmethod
    def boolean_common(self, obj1_name: str, obj2_name: str,
                       result_name: str = "") -> ToolResponse:
        ...

    # Feature operations
    @abstractmethod
    def fillet_edges(self, obj_name: str, radius: float = 1.0,
                     edges: list[int] | None = None,
                     result_name: str = "") -> ToolResponse:
        ...

    @abstractmethod
    def chamfer_edges(self, obj_name: str, size: float = 1.0,
                      edges: list[int] | None = None,
                      result_name: str = "") -> ToolResponse:
        ...

    @abstractmethod
    def mirror_object(self, obj_name: str, plane: str = "XY",
                      result_name: str = "") -> ToolResponse:
        ...

    @abstractmethod
    def scale_object(self, obj_name: str, factor: float | list[float],
                     result_name: str = "") -> ToolResponse:
        ...

    # Export
    @abstractmethod
    def export(self, file_path: str, fmt: str | None = None, verify: bool = True) -> ToolResponse:
        ...

    # Convenience export methods
    def export_step(self, file_path: str) -> ToolResponse:
        """Export to STEP format."""
        return self.export(file_path, "step")

    def export_stl(self, file_path: str) -> ToolResponse:
        """Export to STL format."""
        return self.export(file_path, "stl")

    def export_obj(self, file_path: str) -> ToolResponse:
        """Export to OBJ format."""
        return self.export(file_path, "obj")

    def export_brep(self, file_path: str) -> ToolResponse:
        """Export to BREP format."""
        return self.export(file_path, "brep")

    def export_dxf(self, file_path: str) -> ToolResponse:
        """Export to DXF format."""
        return self.export(file_path, "dxf")

    def export_svg(self, file_path: str) -> ToolResponse:
        """Export to SVG format."""
        return self.export(file_path, "svg")

    def export_dwg(self, file_path: str, version: str | None = None) -> ToolResponse:
        """Export to DWG format (DXF->DWG conversion via ODA File Converter).

        Note: This first exports to DXF via FreeCAD, then converts to DWG
        using the ODA File Converter. Requires ODA File Converter to be installed.

        Args:
            file_path: Output DWG file path.
            version: Target DWG version (R2000-R2018). Defaults to R2018.

        Returns:
            ToolResponse with conversion result.
        """
        from fc_core.io.dwg_converter import convert_dwg
        dxf_path = file_path.rsplit(".", 1)[0] + ".dxf"
        r = self.export(dxf_path, "dxf")
        if r.status != "ok":
            return r
        return convert_dwg(dxf_path, file_path, version=version, replace=True)

    def export_pdf(self, file_path: str) -> ToolResponse:
        """Export to SVG then convert (placeholder)."""
        return self.export(file_path, "svg")

    def export_gltf(self, file_path: str) -> ToolResponse:
        """Export to glTF format."""
        return self.export(file_path, "gltf")

    def export_3mf(self, file_path: str) -> ToolResponse:
        """Export to 3MF format."""
        return self.export(file_path, "3mf")

    def export_fcstd(self, file_path: str) -> ToolResponse:
        """Export/save as FreeCAD native format."""
        return self.export(file_path, "fcstd")

    # Convenience import methods
    def import_step(self, file_path: str) -> ToolResponse:
        """Import a STEP file."""
        return self._import_file(file_path, "step")

    def import_stl(self, file_path: str) -> ToolResponse:
        """Import an STL file."""
        return self._import_file(file_path, "stl")

    def import_obj(self, file_path: str) -> ToolResponse:
        """Import an OBJ file."""
        return self._import_file(file_path, "obj")

    def import_dxf(self, file_path: str) -> ToolResponse:
        """Import a DXF file."""
        return self._import_file(file_path, "dxf")

    def import_brep(self, file_path: str) -> ToolResponse:
        """Import a BREP file."""
        return self._import_file(file_path, "brep")

    def _import_file(self, file_path: str, fmt: str) -> ToolResponse:
        """Internal import helper — subclasses may override."""
        return ToolResponse.error(
            "import", "NOT_IMPLEMENTED",
            f"Import not implemented for format: {fmt}",
        )

    # Query aliases
    def list_objects(self) -> ToolResponse:
        """Alias for object_list()."""
        return self.object_list()

    def get_object_info(self, obj_name: str) -> ToolResponse:
        """Alias for object_get()."""
        return self.object_get(obj_name)

    def get_objects_info(self) -> ToolResponse:
        """Alias for object_list() returning full info."""
        return self.object_list()

    # Transform
    @abstractmethod
    def transform_placement(self, obj_name: str,
                            position: tuple[float, float, float] | None = None,
                            rotation: tuple[float, float, float] | None = None) -> ToolResponse:
        ...

    # Batch operations
    @abstractmethod
    def batch_start(self) -> None:
        """Start batching operations into a single script."""
        ...

    @abstractmethod
    def batch_add(self, body: str) -> None:
        """Add a Python code snippet to the batch script."""
        ...

    @abstractmethod
    def batch_execute(self, timeout: int | None = None) -> list[dict[str, Any]]:
        """Execute all batched operations in a single FreeCAD process."""
        ...

    # Raw code execution
    @abstractmethod
    def execute_code(self, code: str) -> ToolResponse:
        ...


class HeadlessBackend(GeometryOpsMixin, BackendInterface):
    """Headless backend using FreeCADCmd subprocess.

    Executes Python scripts via FreeCADCmd for all operations.
    No GUI, no screenshots, but works without FreeCAD running.
    Ideal for CI/CD, batch processing, and automated pipelines.
    """

    def __init__(self, freecad_path: str | None = None, timeout: int = 120):
        self._freecad_path = freecad_path
        self._timeout = timeout
        self._connected = False
        self._current_doc_path: str | None = None
        self._macro_counter = 0
        self._backend = self

    @property
    def freecad_path(self) -> str:
        if self._freecad_path is None:
            self._freecad_path = find_freecad()
        return self._freecad_path

    # ── Batch execution mode ──
    def batch_start(self) -> None:
        """Start batching operations into a single script.

        Call batch_start(), then use batch_add() to queue operations,
        then batch_execute() to run them all in a single FreeCAD process.
        """
        self._batch_parts: list[str] = []
        self._batch_doc_path: str | None = None

    def batch_add(self, body: str) -> None:
        """Add a Python code snippet to the batch script.

        Args:
            body: Python code to execute in FreeCAD context.
        """
        if not hasattr(self, "_batch_parts"):
            self.batch_start()
        self._batch_parts.append(body)

    def batch_execute(self, timeout: int | None = None) -> list[dict[str, Any]]:
        """Execute all batched operations in a single FreeCAD process.

        All operations share the same FreeCAD context (document, objects, variables).
        Each operation's result is captured via a separate _fc_result_N variable.

        Args:
            timeout: Timeout in seconds (default: self._timeout).

        Returns:
            List of result dicts with status/data/message keys.
        """
        if not hasattr(self, "_batch_parts") or not self._batch_parts:
            return []

        n = len(self._batch_parts)

        # Build a single shared-context script.
        # All operations run in the same scope so variables/documents persist.
        # Each operation is wrapped in try/except to capture per-op results.
        script_lines: list[str] = [
            "import FreeCAD",
            "import Part",
            "import Sketcher",
            "import PartDesign",
            "import json",
            "import sys",
            "import os",
            "import Mesh",
        ]
        for i, body in enumerate(self._batch_parts):
            script_lines.append("")
            script_lines.append(f"# --- operation_{i} ---")
            script_lines.append(f"_fc_result_{i} = {{'status': 'ok', 'data': {{}}, 'message': ''}}")
            script_lines.append(f"try:")
            for line in body.splitlines():
                script_lines.append(f"    {line}")
            script_lines.append(f"except Exception as _e_{i}:")
            script_lines.append(f"    _fc_result_{i} = {{'status': 'error', 'data': {{}}, 'message': str(_e_{i})}}")
            script_lines.append(f"print('___FC_RESULT_{i}___' + json.dumps(_fc_result_{i}, default=str))")

        script = "\n".join(script_lines)
        macro_path = self._write_macro(script)
        try:
            result = self._run([self.freecad_path, macro_path], timeout=timeout)
            # Parse all results from stdout
            results: list[dict[str, Any]] = []
            for line in result.stdout.splitlines():
                for i in range(n):
                    marker = f"___FC_RESULT_{i}___"
                    if line.startswith(marker):
                        results.append(json.loads(line[len(marker):]))
            # Pad with error results if some markers were missing
            while len(results) < n:
                results.append({"status": "error", "data": {}, "message": "No result output"})
            return results
        finally:
            try:
                os.unlink(macro_path)
            except OSError:
                pass
            self._batch_parts = []

    def connect(self) -> None:
        """Verify FreeCAD is accessible by checking version."""
        try:
            version = self.get_version()
            self._connected = True
            logger.info(f"Connected to FreeCAD {version} (headless)")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to FreeCAD: {e}") from e

    def disconnect(self) -> None:
        self._connected = False
        logger.info("Disconnected from FreeCAD (headless)")

    def is_connected(self) -> bool:
        return self._connected

    def get_version(self) -> str:
        result = self._run([self.freecad_path, "--version"])
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if any(c.isdigit() for c in line) and "." in line:
                    for part in line.split():
                        if any(c.isdigit() for c in part) and "." in part:
                            return part.strip(",").strip()
            return line.split()[-1] if line else "unknown"
        raise RuntimeError(f"Failed to get FreeCAD version: {result.stderr}")

    def _run(self, args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        """Run a subprocess command."""
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                timeout=timeout or self._timeout,
            )
            return proc
        except FileNotFoundError:
            raise FileNotFoundError(_install_instructions())
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"FreeCAD process timed out after {timeout or self._timeout}s")

    def _write_macro(self, content: str) -> str:
        """Write Python code to a temporary macro file."""
        self._macro_counter += 1
        fd, path = tempfile.mkstemp(
            suffix=".py",
            prefix=f"fc_macro_{self._macro_counter:04d}_",
        )
        try:
            os.write(fd, content.encode("utf-8"))
        finally:
            os.close(fd)
        return path

    def _build_wrapper_script(self, body: str) -> str:
        """Build a complete FreeCAD Python script with proper imports.

        The body is indented 4 spaces to sit inside the try: block.
        We avoid textwrap.dedent because it would strip the body's indentation.
        """
        indented_body = "\n".join("    " + line for line in body.splitlines())
        return (
            "import FreeCAD\n"
            "import Part\n"
            "import Sketcher\n"
            "import PartDesign\n"
            "import json\n"
            "import sys\n"
            "import os\n"
            "\n"
            '_fc_result = {"status": "ok", "data": {}, "message": ""}\n'
            "\n"
            "try:\n"
            f"{indented_body}\n"
            "except Exception as e:\n"
            '    _fc_result = {"status": "error", "data": {}, "message": str(e)}\n'
            "\n"
            'print("___FC_RESULT___:" + json.dumps(_fc_result, default=str))\n'
        )

    def _execute_macro(self, body: str, timeout: int | None = None) -> dict[str, Any]:
        """Execute a Python script body in FreeCAD and return parsed result."""
        script = self._build_wrapper_script(body)
        macro_path = self._write_macro(script)
        try:
            result = self._run([self.freecad_path, macro_path], timeout=timeout)
            # Parse result from stdout
            for line in result.stdout.splitlines():
                if line.startswith("___FC_RESULT___:"):
                    return json.loads(line[len("___FC_RESULT___:"):])
            # If no result marker found, check for errors
            if result.returncode != 0:
                return {"status": "error", "data": {}, "message": result.stderr or result.stdout}
            return {"status": "ok", "data": {}, "message": "No result output"}
        finally:
            try:
                os.unlink(macro_path)
            except OSError:
                pass

    # Document operations
    def document_new(self, name: str = "Untitled") -> ToolResponse:
        r = self._execute_macro(textwrap.dedent(f"""\
            doc = FreeCAD.newDocument("{name}")
            _fc_result["data"] = {{"name": doc.Name, "label": doc.Label}}
        """))
        if r["status"] == "ok":
            return ToolResponse.ok("document_new", r["data"], f"Document '{name}' created")
        return ToolResponse.error("document_new", "CREATE_FAILED", r["message"])

    def document_open(self, file_path: str) -> ToolResponse:
        r = self._execute_macro(textwrap.dedent(f"""\
            doc = FreeCAD.open(r"{os.path.abspath(file_path)}")
            _fc_result["data"] = {{"name": doc.Name, "label": doc.Label, "objects_count": len(doc.Objects)}}
        """))
        if r["status"] == "ok":
            self._current_doc_path = file_path
            return ToolResponse.ok("document_open", r["data"], f"Opened: {file_path}")
        return ToolResponse.error("document_open", "OPEN_FAILED", r["message"])

    def document_save(self, file_path: str | None = None) -> ToolResponse:
        path = self._current_doc_path if file_path is None else file_path
        if path is None:
            return ToolResponse.error("document_save", "NO_PATH", "No file path specified")
        r = self._execute_macro(textwrap.dedent(f"""\
            doc = FreeCAD.ActiveDocument
            doc.saveAs(r"{os.path.abspath(path)}")
            _fc_result["data"] = {{"saved_to": r"{os.path.abspath(path)}"}}
        """))
        if r["status"] == "ok":
            self._current_doc_path = path
            return ToolResponse.ok("document_save", r["data"], f"Saved: {path}")
        return ToolResponse.error("document_save", "SAVE_FAILED", r["message"])

    def inject_gui_data(
        self,
        file_path: str | None = None,
        view: str = "isometric",
        fit_all: bool = True,
    ) -> ToolResponse:
        """HeadlessBackend 不支持 GUI 注入。

        提示用户切换到 RPC 模式启动 FreeCAD GUI 会话。
        """
        return ToolResponse.error(
            "inject_gui_data",
            "GUI_REQUIRED",
            "GUI 注入需要 FreeCAD GUI 模式。请使用 `fc session start --mode gui` "
            "启动 GUI 会话，然后通过 `fc --session <name> document inject-gui` 调用。",
        )

    def document_info(self) -> ToolResponse:
        r = self._execute_macro(textwrap.dedent("""\
            doc = FreeCAD.ActiveDocument
            _fc_result["data"] = {
                "name": doc.Name,
                "label": doc.Label,
                "objects_count": len(doc.Objects),
                "objects": [{"name": obj.Name, "label": obj.Label, "type_id": obj.TypeId} for obj in doc.Objects]
            }
        """))
        if r["status"] == "ok":
            return ToolResponse.ok("document_info", r["data"])
        return ToolResponse.error("document_info", "INFO_FAILED", r["message"])

    def document_close(self) -> ToolResponse:
        r = self._execute_macro(textwrap.dedent("""\
            doc = FreeCAD.ActiveDocument
            name = doc.Name
            FreeCAD.closeDocument(name)
            _fc_result["data"] = {"name": name}
        """))
        if r["status"] == "ok":
            self._current_doc_path = None
            return ToolResponse.ok("document_close", r["data"], f"Closed: {r['data'].get('name', '')}")
        return ToolResponse.error("document_close", "CLOSE_FAILED", r["message"])

    # Object operations
    def object_list(self) -> ToolResponse:
        r = self._execute_macro(textwrap.dedent("""\
            doc = FreeCAD.ActiveDocument
            objects = []
            for obj in doc.Objects:
                info = {
                    "name": obj.Name,
                    "label": obj.Label,
                    "type_id": obj.TypeId,
                }
                if hasattr(obj, "Placement"):
                    p = obj.Placement
                    info["placement"] = {
                        "position": [p.Base.x, p.Base.y, p.Base.z],
                        "rotation_axis": [p.Rotation.Axis.x, p.Rotation.Axis.y, p.Rotation.Axis.z],
                        "rotation_angle": p.Rotation.Angle,
                    }
                if hasattr(obj, "Shape") and obj.Shape:
                    bb = obj.Shape.BoundBox
                    info["bounding_box"] = {
                        "x_min": bb.XMin, "x_max": bb.XMax,
                        "y_min": bb.YMin, "y_max": bb.YMax,
                        "z_min": bb.ZMin, "z_max": bb.ZMax,
                    }
                objects.append(info)
            _fc_result["data"] = {"objects": objects, "count": len(objects)}
        """))
        if r["status"] == "ok":
            return ToolResponse.ok("object_list", r["data"])
        return ToolResponse.error("object_list", "LIST_FAILED", r["message"])

    def object_get(self, obj_name: str) -> ToolResponse:
        r = self._execute_macro(textwrap.dedent(f"""\
            doc = FreeCAD.ActiveDocument
            obj = doc.getObject("{obj_name}")
            if obj is None:
                raise ValueError(f"Object '{{obj_name}}' not found in document")
            info = {{"name": obj.Name, "label": obj.Label, "type_id": obj.TypeId}}
            if hasattr(obj, "Placement"):
                p = obj.Placement
                info["placement"] = {{
                    "position": [p.Base.x, p.Base.y, p.Base.z],
                    "rotation_axis": [p.Rotation.Axis.x, p.Rotation.Axis.y, p.Rotation.Axis.z],
                    "rotation_angle": p.Rotation.Angle,
                }}
            if hasattr(obj, "Shape") and obj.Shape:
                bb = obj.Shape.BoundBox
                info["bounding_box"] = {{
                    "x_min": bb.XMin, "x_max": bb.XMax,
                    "y_min": bb.YMin, "y_max": bb.YMax,
                    "z_min": bb.ZMin, "z_max": bb.ZMax,
                }}
                info["shape"] = {{
                    "volume": obj.Shape.Volume,
                    "area": obj.Shape.Area,
                    "length": obj.Shape.Length,
                    "center_of_mass": list(obj.Shape.CenterOfMass),
                    "solid_count": len(obj.Shape.Solids),
                    "face_count": len(obj.Shape.Faces),
                    "edge_count": len(obj.Shape.Edges),
                }}
            # Include all properties
            for prop in obj.PropertiesList:
                try:
                    val = getattr(obj, prop)
                    if isinstance(val, (int, float, str, bool)):
                        info[prop] = val
                except Exception:
                    pass
            _fc_result["data"] = info
        """))
        if r["status"] == "ok":
            return ToolResponse.ok("object_get", r["data"])
        return ToolResponse.error("object_get", "GET_FAILED", r["message"])

    def object_create(self, obj_type: str, obj_name: str,
                      properties: dict[str, Any] | None = None) -> ToolResponse:
        props_json = json.dumps(properties or {})
        r = self._execute_macro(textwrap.dedent(f"""\
            doc = FreeCAD.ActiveDocument
            obj = doc.addObject("{obj_type}", "{obj_name}")
            props = json.loads(r'{props_json}')
            for key, value in props.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            doc.recompute()
            _fc_result["data"] = {{"name": obj.Name, "label": obj.Label, "type_id": obj.TypeId}}
        """))
        if r["status"] == "ok":
            return ToolResponse.ok("object_create", r["data"],
                                   f"Created {obj_type}: {obj_name}")
        return ToolResponse.error("object_create", "CREATE_FAILED", r["message"])

    def object_edit(self, obj_name: str,
                    properties: dict[str, Any]) -> ToolResponse:
        props_json = json.dumps(properties)
        r = self._execute_macro(textwrap.dedent(f"""\
            doc = FreeCAD.ActiveDocument
            obj = doc.getObject("{obj_name}")
            if obj is None:
                raise ValueError(f"Object '{{obj_name}}' not found")
            props = json.loads(r'{props_json}')
            for key, value in props.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            doc.recompute()
            _fc_result["data"] = {{"name": obj.Name, "label": obj.Label}}
        """))
        if r["status"] == "ok":
            return ToolResponse.ok("object_edit", r["data"], f"Edited: {obj_name}")
        return ToolResponse.error("object_edit", "EDIT_FAILED", r["message"])

    def object_delete(self, obj_name: str) -> ToolResponse:
        r = self._execute_macro(textwrap.dedent(f"""\
            doc = FreeCAD.ActiveDocument
            doc.removeObject("{obj_name}")
            doc.recompute()
            _fc_result["data"] = {{"name": "{obj_name}"}}
        """))
        if r["status"] == "ok":
            return ToolResponse.ok("object_delete", r["data"], f"Deleted: {obj_name}")
        return ToolResponse.error("object_delete", "DELETE_FAILED", r["message"])

    # Sketch operations
    def sketch_new(self, plane: str = "XY", offset: float = 0.0,
                   name: str = "") -> ToolResponse:
        sketch_name = name or "Sketch"
        r = self._execute_macro(textwrap.dedent(f"""\
            doc = FreeCAD.ActiveDocument
            sketch = doc.addObject("Sketcher::SketchObject", "{sketch_name}")
            # Set sketch plane via attachment
            import Part
            if "{plane}" == "XY":
                sketch.AttachmentOffset = FreeCAD.Placement(
                    FreeCAD.Vector(0, 0, {offset}), FreeCAD.Rotation())
            elif "{plane}" == "XZ":
                sketch.AttachmentOffset = FreeCAD.Placement(
                    FreeCAD.Vector(0, {offset}, 0), FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90))
            elif "{plane}" == "YZ":
                sketch.AttachmentOffset = FreeCAD.Placement(
                    FreeCAD.Vector({offset}, 0, 0), FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), 90))
            doc.recompute()
            _fc_result["data"] = {{"name": sketch.Name, "label": sketch.Label, "plane": "{plane}"}}
        """))
        if r["status"] == "ok":
            return ToolResponse.ok("sketch_new", r["data"], f"Created sketch: {sketch_name}")
        return ToolResponse.error("sketch_new", "CREATE_FAILED", r["message"])

    # PartDesign operations
    def body_new(self, name: str = "") -> ToolResponse:
        body_name = name or "Body"
        r = self._execute_macro(textwrap.dedent(f"""\
            doc = FreeCAD.ActiveDocument
            body = doc.addObject("PartDesign::Body", "{body_name}")
            doc.recompute()
            _fc_result["data"] = {{"name": body.Name, "label": body.Label}}
        """))
        if r["status"] == "ok":
            return ToolResponse.ok("body_new", r["data"], f"Created body: {body_name}")
        return ToolResponse.error("body_new", "CREATE_FAILED", r["message"])

    def body_pad(self, body_name: str, sketch_name: str,
                 length: float = 10.0, **kwargs: Any) -> ToolResponse:
        symmetric = kwargs.get("symmetric", False)
        reversed_dir = kwargs.get("reversed", False)
        r = self._execute_macro(textwrap.dedent(f"""\
            doc = FreeCAD.ActiveDocument
            body = doc.getObject("{body_name}")
            sketch = doc.getObject("{sketch_name}")
            if body is None:
                raise ValueError(f"Body '{{body_name}}' not found")
            if sketch is None:
                raise ValueError(f"Sketch '{{sketch_name}}' not found")
            pad = body.newObject("PartDesign::Pad", "Pad")
            pad.Profile = sketch
            pad.Length = {length}
            pad.Symmetric = {"true" if symmetric else "false"}
            pad.Reversed = {"true" if reversed_dir else "false"}
            doc.recompute()
            _fc_result["data"] = {{"name": pad.Name, "label": pad.Label, "length": {length}}}
        """))
        if r["status"] == "ok":
            return ToolResponse.ok("body_pad", r["data"], f"Added pad: length={length}")
        return ToolResponse.error("body_pad", "PAD_FAILED", r["message"])

    def _import_file(self, file_path: str, fmt: str) -> ToolResponse:
        """Import a file using the io module."""
        from fc_core.io.import_mod import import_file
        return import_file(self, file_path)

    # Export
    def export(self, file_path: str, fmt: str | None = None, verify: bool = True) -> ToolResponse:
        path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        ext = fmt or Path(path).suffix.lstrip(".").lower()

        # Build export code based on format
        if ext in ("step", "stp"):
            export_code = f'Part.export([FreeCAD.ActiveDocument.Objects], r"{path}")'
        elif ext in ("iges", "igs"):
            export_code = f'Part.export([FreeCAD.ActiveDocument.Objects], r"{path}")'
        elif ext == "stl":
            export_code = textwrap.dedent(f"""\
                import Mesh
                shapes = [obj.Shape for obj in FreeCAD.ActiveDocument.Objects if hasattr(obj, "Shape")]
                mesh = Mesh.Mesh()
                for shape in shapes:
                    mesh.addMesh(Mesh.Mesh(shape.tessellate(0.1)))
                mesh.write(r"{path}")
            """)
        elif ext == "brep":
            export_code = textwrap.dedent(f"""\
                doc = FreeCAD.ActiveDocument
                shapes = [obj.Shape for obj in doc.Objects if hasattr(obj, "Shape")]
                if shapes:
                    comp = Part.makeCompound(shapes)
                    comp.exportBrep(r"{path}")
            """)
        elif ext == "obj":
            export_code = textwrap.dedent(f"""\
                import Mesh
                shapes = [obj.Shape for obj in FreeCAD.ActiveDocument.Objects if hasattr(obj, "Shape")]
                mesh = Mesh.Mesh()
                for shape in shapes:
                    mesh.addMesh(Mesh.Mesh(shape.tessellate(0.1)))
                mesh.write(r"{path}")
            """)
        elif ext == "dxf":
            export_code = textwrap.dedent(f"""\
                import importDXF
                importDXF.export(FreeCAD.ActiveDocument.Objects, r"{path}")
            """)
        elif ext == "dwg":
            # DWG: first export to DXF, then convert via ODA File Converter
            dxf_path = path.rsplit(".", 1)[0] + ".dxf"
            export_code = textwrap.dedent(f"""\
                import importDXF
                importDXF.export(FreeCAD.ActiveDocument.Objects, r"{dxf_path}")
            """)
        elif ext == "svg":
            export_code = textwrap.dedent(f"""\
                import importSVG
                importSVG.export(FreeCAD.ActiveDocument.Objects, r"{path}")
            """)
        elif ext == "fcstd":
            export_code = f'FreeCAD.ActiveDocument.saveAs(r"{path}")'
        else:
            # Default: try Part.export
            export_code = f'Part.export([FreeCAD.ActiveDocument.Objects], r"{path}")'

        r = self._execute_macro(export_code)

        # Post-process DWG conversion
        if ext == "dwg" and r["status"] == "ok":
            from fc_core.io.dwg_converter import convert_dwg
            dxf_path = locals().get("_dwg_source", "")
            dwg_path = locals().get("_dwg_target", path)
            if dxf_path and os.path.isfile(dxf_path):
                conv_r = convert_dwg(dxf_path, dwg_path, replace=True)
                if conv_r.status == "ok":
                    r["status"] = "ok"
                    r["message"] = conv_r.message
                else:
                    r["status"] = "error"
                    r["message"] = conv_r.message

        if r["status"] == "ok" and os.path.isfile(path):
            file_size = os.path.getsize(path)
            data: dict[str, Any] = {
                "output": path, "format": ext, "file_size": file_size,
            }

            # 导出后自动验证几何正确性
            if verify and ext in ("step", "stp", "fcstd", "stl", "brep"):
                from fc_core.verify import CADVerifier
                verifier = CADVerifier()
                report = verifier.verify(path, fmt=ext)
                data["verification"] = report.to_dict()
                if not report.passed:
                    failed_msgs = [c.message for c in report.checks if not c.passed]
                    return ToolResponse.error(
                        "export", "VERIFICATION_FAILED",
                        f"导出成功但验证失败: {'; '.join(failed_msgs)}",
                        suggestion="检查模型几何是否为空或参数是否正确",
                    )

            return ToolResponse.ok("export", data, f"Exported: {path}")
        return ToolResponse.error("export", "EXPORT_FAILED",
                                  r["message"] or f"Output file not created: {path}")

    # Raw code execution
    def execute_code(self, code: str) -> ToolResponse:
        r = self._execute_macro(code)
        if r["status"] == "ok":
            return ToolResponse.ok("execute_code", r["data"], r["message"])
        return ToolResponse.error("execute_code", "EXEC_FAILED", r["message"])


class RPCBackend(GeometryOpsMixin, BackendInterface):
    """RPC backend connecting to FreeCAD GUI via XML-RPC.

    Requires FreeCAD MCP addon running with RPC server started.
    Supports screenshots and real-time operations.
    """

    def __init__(self, host: str = "localhost", port: int = 9875, timeout: float = 150):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._server = None
        self._connected = False
        self._backend = self

    def connect(self) -> None:
        import xmlrpc.client
        from fc_core.backend._timeout_transport import _TimeoutTransport
        self._server = xmlrpc.client.ServerProxy(
            f"http://{self._host}:{self._port}",
            allow_none=True,
            transport=_TimeoutTransport(timeout=self._timeout),
        )
        if not self._ping():
            raise ConnectionError(
                f"Cannot connect to FreeCAD RPC server at {self._host}:{self._port}. "
                "Make sure FreeCAD MCP addon is running."
            )
        self._connected = True
        logger.info(f"Connected to FreeCAD RPC at {self._host}:{self._port}")

    def disconnect(self) -> None:
        if self._server:
            transport = getattr(self._server, "_ServerProxy__transport", None)
            close = getattr(transport, "close", None)
            if callable(close):
                close()
        self._server = None
        self._connected = False

    def is_connected(self) -> bool:
        if not self._connected or not self._server:
            return False
        try:
            return self._ping()
        except Exception:
            self._connected = False
            return False

    def _ping(self) -> bool:
        try:
            return self._server.ping()
        except Exception:
            return False

    def _call(self, method: str, *args: Any) -> dict[str, Any]:
        """Call an RPC method and return the result dict."""
        func = getattr(self._server, method)
        result = func(*args)
        if isinstance(result, dict):
            return result
        return {"status": "ok", "data": result}

    def get_version(self) -> str:
        r = self._call("get_version")
        return r.get("version", "unknown")

    def document_new(self, name: str = "Untitled") -> ToolResponse:
        r = self._call("create_document", name)
        if r.get("success"):
            return ToolResponse.ok("document_new", r, f"Document '{name}' created")
        return ToolResponse.error("document_new", "CREATE_FAILED", r.get("error", "Unknown error"))

    def document_open(self, file_path: str) -> ToolResponse:
        r = self._call("open_document", os.path.abspath(file_path))
        if r.get("success"):
            return ToolResponse.ok("document_open", r, f"Opened: {file_path}")
        return ToolResponse.error("document_open", "OPEN_FAILED", r.get("error", "Unknown error"))

    def document_save(self, file_path: str | None = None) -> ToolResponse:
        r = self._call("save_document", file_path or "")
        if r.get("success"):
            return ToolResponse.ok("document_save", r, f"Saved: {file_path or 'current'}")
        return ToolResponse.error("document_save", "SAVE_FAILED", r.get("error", "Unknown error"))

    def inject_gui_data(
        self,
        file_path: str | None = None,
        view: str = "isometric",
        fit_all: bool = True,
    ) -> ToolResponse:
        """通过 RPC 注入 GUI 视图数据并重新保存。"""
        r = self._call(
            "inject_gui_data",
            file_path or "",
            view,
            fit_all,
        )
        if r.get("success"):
            return ToolResponse.ok("inject_gui_data", r, r.get("message", "GUI 注入成功"))
        return ToolResponse.error(
            "inject_gui_data",
            "INJECT_FAILED",
            r.get("error", "Unknown error"),
        )

    def document_info(self) -> ToolResponse:
        r = self._call("get_objects")
        if r.get("success"):
            return ToolResponse.ok("document_info", r)
        return ToolResponse.error("document_info", "INFO_FAILED", r.get("error", "Unknown error"))

    def document_close(self) -> ToolResponse:
        return ToolResponse.ok("document_close", {}, "Document closed (RPC)")

    def object_list(self) -> ToolResponse:
        r = self._call("get_objects")
        if r.get("success"):
            return ToolResponse.ok("object_list", r)
        return ToolResponse.error("object_list", "LIST_FAILED", r.get("error", "Unknown error"))

    def object_get(self, obj_name: str) -> ToolResponse:
        r = self._call("get_object", obj_name)
        if r.get("success"):
            return ToolResponse.ok("object_get", r)
        return ToolResponse.error("object_get", "GET_FAILED", r.get("error", "Unknown error"))

    def object_create(self, obj_type: str, obj_name: str,
                      properties: dict[str, Any] | None = None) -> ToolResponse:
        obj_data = {"Name": obj_name, "Type": obj_type, "Properties": properties or {}}
        r = self._call("create_object", obj_data)
        if r.get("success"):
            return ToolResponse.ok("object_create", r, f"Created {obj_type}: {obj_name}")
        return ToolResponse.error("object_create", "CREATE_FAILED", r.get("error", "Unknown error"))

    def object_edit(self, obj_name: str, properties: dict[str, Any]) -> ToolResponse:
        r = self._call("edit_object", obj_name, {"Properties": properties})
        if r.get("success"):
            return ToolResponse.ok("object_edit", r, f"Edited: {obj_name}")
        return ToolResponse.error("object_edit", "EDIT_FAILED", r.get("error", "Unknown error"))

    def object_delete(self, obj_name: str) -> ToolResponse:
        r = self._call("delete_object", obj_name)
        if r.get("success"):
            return ToolResponse.ok("object_delete", r, f"Deleted: {obj_name}")
        return ToolResponse.error("object_delete", "DELETE_FAILED", r.get("error", "Unknown error"))

    def sketch_new(self, plane: str = "XY", offset: float = 0.0, name: str = "") -> ToolResponse:
        return self.object_create("Sketcher::SketchObject", name or "Sketch")

    def body_new(self, name: str = "") -> ToolResponse:
        return self.object_create("PartDesign::Body", name or "Body")

    def body_pad(self, body_name: str, sketch_name: str,
                 length: float = 10.0, **kwargs: Any) -> ToolResponse:
        code = textwrap.dedent(f"""\
            doc = FreeCAD.ActiveDocument
            body = doc.getObject("{body_name}")
            sketch = doc.getObject("{sketch_name}")
            pad = body.newObject("PartDesign::Pad", "Pad")
            pad.Profile = sketch
            pad.Length = {length}
            doc.recompute()
        """)
        return self.execute_code(code)

    def _import_file(self, file_path: str, fmt: str) -> ToolResponse:
        """Import a file via RPC."""
        r = self._call("import_file", os.path.abspath(file_path), fmt)
        if r.get("success"):
            return ToolResponse.ok("import", r, f"Imported: {file_path}")
        return ToolResponse.error("import", "IMPORT_FAILED", r.get("error", "Unknown error"))

    # Batch operations (RPC: no-op / not supported)
    def batch_start(self) -> None:
        """Batch mode not supported in RPC backend (no-op)."""
        pass

    def batch_add(self, body: str) -> None:
        """Batch mode not supported in RPC backend (no-op)."""
        pass

    def batch_execute(self, timeout: int | None = None) -> list[dict[str, Any]]:
        """Batch mode not supported in RPC backend (returns empty list)."""
        return []

    def export(self, file_path: str, fmt: str | None = None, verify: bool = True) -> ToolResponse:
        path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        ext = fmt or Path(path).suffix.lstrip(".").lower()

        # Build export code based on format (mirrors HeadlessBackend logic)
        if ext in ("step", "stp"):
            export_code = f'Part.export([FreeCAD.ActiveDocument.Objects], r"{path}")'
        elif ext in ("iges", "igs"):
            export_code = f'Part.export([FreeCAD.ActiveDocument.Objects], r"{path}")'
        elif ext == "stl":
            export_code = textwrap.dedent(f"""\
                import Mesh
                shapes = [obj.Shape for obj in FreeCAD.ActiveDocument.Objects if hasattr(obj, "Shape")]
                mesh = Mesh.Mesh()
                for shape in shapes:
                    mesh.addMesh(Mesh.Mesh(shape.tessellate(0.1)))
                mesh.write(r"{path}")
            """)
        elif ext == "brep":
            export_code = textwrap.dedent(f"""\
                doc = FreeCAD.ActiveDocument
                shapes = [obj.Shape for obj in doc.Objects if hasattr(obj, "Shape")]
                if shapes:
                    comp = Part.makeCompound(shapes)
                    comp.exportBrep(r"{path}")
            """)
        elif ext == "obj":
            export_code = textwrap.dedent(f"""\
                import Mesh
                shapes = [obj.Shape for obj in FreeCAD.ActiveDocument.Objects if hasattr(obj, "Shape")]
                mesh = Mesh.Mesh()
                for shape in shapes:
                    mesh.addMesh(Mesh.Mesh(shape.tessellate(0.1)))
                mesh.write(r"{path}")
            """)
        elif ext == "dxf":
            export_code = textwrap.dedent(f"""\
                import importDXF
                importDXF.export(FreeCAD.ActiveDocument.Objects, r"{path}")
            """)
        elif ext == "dwg":
            # DWG: first export to DXF, then convert via ODA File Converter
            dxf_path = path.rsplit(".", 1)[0] + ".dxf"
            export_code = textwrap.dedent(f"""\
                import importDXF
                importDXF.export(FreeCAD.ActiveDocument.Objects, r"{dxf_path}")
            """)
        elif ext == "svg":
            export_code = textwrap.dedent(f"""\
                import importSVG
                importSVG.export(FreeCAD.ActiveDocument.Objects, r"{path}")
            """)
        elif ext == "fcstd":
            export_code = f'FreeCAD.ActiveDocument.saveAs(r"{path}")'
        else:
            # Default: try Part.export
            export_code = f'Part.export([FreeCAD.ActiveDocument.Objects], r"{path}")'

        r = self.execute_code(export_code)

        # Post-process DWG conversion
        if ext == "dwg" and r.status == "ok":
            from fc_core.io.dwg_converter import convert_dwg
            dxf_path = path.rsplit(".", 1)[0] + ".dxf"
            if os.path.isfile(dxf_path):
                conv_r = convert_dwg(dxf_path, path, replace=True)
                if conv_r.status == "ok":
                    r = conv_r
                else:
                    return conv_r

        if r.status == "ok":
            data: dict[str, Any] = {"output": path, "format": ext}

            # 导出后自动几何正确性验证
            if verify and ext in ("step", "stp", "fcstd", "stl", "brep"):
                from fc_core.verify import CADVerifier
                verifier = CADVerifier()
                report = verifier.verify(path, fmt=ext)
                data["verification"] = report.to_dict()
                if not report.passed:
                    failed_msgs = [c.message for c in report.checks if not c.passed]
                    return ToolResponse.error(
                        "export", "VERIFICATION_FAILED",
                        f"导出成功但验证失败: {'; '.join(failed_msgs)}",
                        suggestion="检查模型几何是否为空或参数是否正确",
                    )

            return ToolResponse.ok("export", data, f"Exported: {path}")
        return r

    def execute_code(self, code: str) -> ToolResponse:
        """Execute arbitrary Python code in the running FreeCAD instance via RPC."""
        r = self._call("execute_code", code)
        if r.get("success") or r.get("status") == "ok":
            return ToolResponse.ok("execute_code", r, r.get("message", "Code executed"))
        return ToolResponse.error("execute_code", "EXEC_FAILED",
                                  r.get("error", r.get("message", "Unknown error")))
