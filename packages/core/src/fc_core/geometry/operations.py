"""Geometry operations: boolean, fillet, chamfer, mirror, etc."""

from __future__ import annotations

from fc_core.types import ToolResponse


class GeometryOpsMixin:
    """Mixin providing geometry operations.

    Boolean operations, transformations, and feature operations.
    Requires the host class to have a `_backend` attribute with an
    ``execute_code(code) -> ToolResponse`` method (i.e. a BackendInterface).
    """

    _backend: object  # BackendInterface

    def boolean_union(self, base_name: str, tool_name: str,
                      result_name: str = "") -> ToolResponse:
        """Perform boolean union (fuse) of two objects."""
        name = result_name or "Fusion"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
base = doc.getObject("{base_name}")
tool = doc.getObject("{tool_name}")
if base is None:
    raise ValueError(f"Base object '{base_name}' not found")
if tool is None:
    raise ValueError(f"Tool object '{tool_name}' not found")
result = doc.addObject("Part::MultiFuse", "{name}")
result.Shapes = [base, tool]
doc.recompute()
"""
        r = self._backend.execute_code(code)
        r.operation = "boolean_union"
        if r.status == "ok":
            r.message = f"Boolean union: {name} = {base_name} + {tool_name}"
        else:
            r.error_code = "BOOLEAN_FAILED"
        return r

    def boolean_cut(self, base_name: str, tool_name: str,
                    result_name: str = "") -> ToolResponse:
        """Perform boolean cut (subtraction) of tool from base."""
        name = result_name or "Cut"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
base = doc.getObject("{base_name}")
tool = doc.getObject("{tool_name}")
if base is None:
    raise ValueError(f"Base object '{base_name}' not found")
if tool is None:
    raise ValueError(f"Tool object '{tool_name}' not found")
result = doc.addObject("Part::Cut", "{name}")
result.Base = base
result.Tool = tool
doc.recompute()
"""
        r = self._backend.execute_code(code)
        r.operation = "boolean_cut"
        if r.status == "ok":
            r.message = f"Boolean cut: {name} = {base_name} - {tool_name}"
        else:
            r.error_code = "BOOLEAN_FAILED"
        return r

    def boolean_common(self, obj1_name: str, obj2_name: str,
                       result_name: str = "") -> ToolResponse:
        """Perform boolean common (intersection) of two objects."""
        name = result_name or "Common"
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
obj1 = doc.getObject("{obj1_name}")
obj2 = doc.getObject("{obj2_name}")
if obj1 is None:
    raise ValueError(f"Object '{obj1_name}' not found")
if obj2 is None:
    raise ValueError(f"Object '{obj2_name}' not found")
result = doc.addObject("Part::MultiCommon", "{name}")
result.Shapes = [obj1, obj2]
doc.recompute()
"""
        r = self._backend.execute_code(code)
        r.operation = "boolean_common"
        if r.status == "ok":
            r.message = f"Boolean common: {name} = {obj1_name} ∩ {obj2_name}"
        else:
            r.error_code = "BOOLEAN_FAILED"
        return r

    def fillet_edges(self, obj_name: str, radius: float = 1.0,
                     edges: list[int] | None = None,
                     result_name: str = "") -> ToolResponse:
        """Apply fillet to edges of an object."""
        name = result_name or "Fillet"
        edges_str = ", ".join(str(e) for e in edges) if edges else ""
        edge_refs = f"[{edges_str}]" if edges else "None"
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{obj_name}")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
if hasattr(obj, "Shape"):
    shape = obj.Shape
    if {edge_refs} is None:
        fillet_shape = shape.makeFillet({radius}, shape.Edges)
    else:
        selected_edges = [shape.Edges[i] for i in [{edges_str}]]
        fillet_shape = shape.makeFillet({radius}, selected_edges)
    result = doc.addObject("Part::Feature", "{name}")
    result.Shape = fillet_shape
    doc.recompute()
else:
    raise ValueError("Object has no Shape")
"""
        r = self._backend.execute_code(code)
        r.operation = "fillet_edges"
        if r.status == "ok":
            r.message = f"Fillet: {name} (radius={radius})"
        else:
            r.error_code = "FILLET_FAILED"
        return r

    def chamfer_edges(self, obj_name: str, size: float = 1.0,
                      edges: list[int] | None = None,
                      result_name: str = "") -> ToolResponse:
        """Apply chamfer to edges of an object."""
        name = result_name or "Chamfer"
        edges_str = ", ".join(str(e) for e in edges) if edges else ""
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{obj_name}")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
if hasattr(obj, "Shape"):
    shape = obj.Shape
    if [{edges_str}]:
        selected_edges = [shape.Edges[i] for i in [{edges_str}]]
        chamfer_shape = shape.makeChamfer({size}, selected_edges)
    else:
        chamfer_shape = shape.makeChamfer({size}, shape.Edges)
    result = doc.addObject("Part::Feature", "{name}")
    result.Shape = chamfer_shape
    doc.recompute()
else:
    raise ValueError("Object has no Shape")
"""
        r = self._backend.execute_code(code)
        r.operation = "chamfer_edges"
        if r.status == "ok":
            r.message = f"Chamfer: {name} (size={size})"
        else:
            r.error_code = "CHAMFER_FAILED"
        return r

    def mirror_object(self, obj_name: str, plane: str = "XY",
                      result_name: str = "") -> ToolResponse:
        """Mirror an object across a plane."""
        name = result_name or "Mirrored"
        normal_map = {"XY": (0, 0, 1), "XZ": (0, 1, 0), "YZ": (1, 0, 0)}
        normal = normal_map.get(plane, (0, 0, 1))
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{obj_name}")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
if hasattr(obj, "Shape"):
    shape = obj.Shape
    mirrored = shape.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector{normal})
    result = doc.addObject("Part::Feature", "{name}")
    result.Shape = mirrored
    doc.recompute()
else:
    raise ValueError("Object has no Shape")
"""
        r = self._backend.execute_code(code)
        r.operation = "mirror_object"
        if r.status == "ok":
            r.message = f"Mirrored: {name} across {plane} plane"
        else:
            r.error_code = "MIRROR_FAILED"
        return r

    def scale_object(self, obj_name: str, factor: float | list[float],
                     result_name: str = "") -> ToolResponse:
        """Scale an object by a uniform or non-uniform factor."""
        name = result_name or "Scaled"
        if isinstance(factor, (list, tuple)):
            scale_str = f"FreeCAD.Vector({factor[0]}, {factor[1]}, {factor[2]})"
        else:
            scale_str = f"FreeCAD.Vector({factor}, {factor}, {factor})"
        code = f"""\
import FreeCAD
import Part
doc = FreeCAD.ActiveDocument
obj = doc.getObject("{obj_name}")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
if hasattr(obj, "Shape"):
    shape = obj.Shape
    scaled = shape.scale({scale_str})
    result = doc.addObject("Part::Feature", "{name}")
    result.Shape = scaled
    doc.recompute()
else:
    raise ValueError("Object has no Shape")
"""
        r = self._backend.execute_code(code)
        r.operation = "scale_object"
        if r.status == "ok":
            r.message = f"Scaled: {name} by factor {factor}"
        else:
            r.error_code = "SCALE_FAILED"
        return r

    def transform_placement(self, obj_name: str, position: tuple[float, float, float] | None = None,
                            rotation: tuple[float, float, float] | None = None) -> ToolResponse:
        """Transform an object's placement (position and/or rotation)."""
        code_lines = [
            'import FreeCAD',
            'doc = FreeCAD.ActiveDocument',
            f'obj = doc.getObject("{obj_name}")',
            f'if obj is None:',
            f'    raise ValueError(f"Object \'{obj_name}\' not found")',
        ]
        if position:
            code_lines.append(
                f'obj.Placement.Base = FreeCAD.Vector({position[0]}, {position[1]}, {position[2]})'
            )
        if rotation:
            code_lines.append(
                f'obj.Placement.Rotation = FreeCAD.Rotation({rotation[0]}, {rotation[1]}, {rotation[2]})'
            )
        code_lines.append('doc.recompute()')

        r = self._backend.execute_code("\n".join(code_lines))
        r.operation = "transform_placement"
        if r.status == "ok":
            r.message = f"Transformed: {obj_name}"
        else:
            r.error_code = "TRANSFORM_FAILED"
        return r
