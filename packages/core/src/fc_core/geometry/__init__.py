"""Geometry primitive operations.

Provides high-level API for creating basic 3D primitives:
Box, Cylinder, Sphere, Cone, Torus, Wedge, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fc_core.geometry.operations import GeometryOpsMixin
from fc_core.types import ToolResponse, Vec3

if TYPE_CHECKING:
    from fc_core.backend import BackendInterface

__all__ = ["PrimitivesMixin", "GeometryOpsMixin"]


class PrimitivesMixin:
    """Mixin providing primitive creation methods.

    Designed to be used with a backend that implements BackendInterface.
    This mixin provides the high-level geometry API that CLI commands call.
    """

    _backend: BackendInterface

    def add_box(self, name: str = "", length: float = 10.0, width: float = 10.0,
                height: float = 10.0, position: Vec3 | None = None,
                rotation: Vec3 | None = None) -> ToolResponse:
        """Add a box (rectangular prism) primitive."""
        obj_name = name or "Box"
        props = {"Length": length, "Width": width, "Height": height}
        if position:
            props["Placement"] = {
                "Base": {"x": position.x, "y": position.y, "z": position.z}
            }
        r = self._backend.object_create("Part::Box", obj_name, props)
        if r.status == "ok":
            r.data["dimensions"] = {"length": length, "width": width, "height": height}
            r.data["volume"] = length * width * height
            r.message = f"Added box: {obj_name} ({length}x{width}x{height})"
        return r

    def add_cylinder(self, name: str = "", radius: float = 5.0, height: float = 10.0,
                     position: Vec3 | None = None) -> ToolResponse:
        """Add a cylinder primitive."""
        obj_name = name or "Cylinder"
        props = {"Radius": radius, "Height": height}
        if position:
            props["Placement"] = {
                "Base": {"x": position.x, "y": position.y, "z": position.z}
            }
        r = self._backend.object_create("Part::Cylinder", obj_name, props)
        import math
        if r.status == "ok":
            r.data["dimensions"] = {"radius": radius, "height": height}
            r.data["volume"] = math.pi * radius ** 2 * height
            r.message = f"Added cylinder: {obj_name} (r={radius}, h={height})"
        return r

    def add_sphere(self, name: str = "", radius: float = 5.0,
                   position: Vec3 | None = None) -> ToolResponse:
        """Add a sphere primitive."""
        obj_name = name or "Sphere"
        props = {"Radius": radius}
        if position:
            props["Placement"] = {
                "Base": {"x": position.x, "y": position.y, "z": position.z}
            }
        r = self._backend.object_create("Part::Sphere", obj_name, props)
        import math
        if r.status == "ok":
            r.data["dimensions"] = {"radius": radius}
            r.data["volume"] = (4 / 3) * math.pi * radius ** 3
            r.message = f"Added sphere: {obj_name} (r={radius})"
        return r

    def add_cone(self, name: str = "", radius1: float = 5.0, radius2: float = 0.0,
                 height: float = 10.0, position: Vec3 | None = None) -> ToolResponse:
        """Add a cone primitive."""
        obj_name = name or "Cone"
        props = {"Radius1": radius1, "Radius2": radius2, "Height": height}
        if position:
            props["Placement"] = {
                "Base": {"x": position.x, "y": position.y, "z": position.z}
            }
        r = self._backend.object_create("Part::Cone", obj_name, props)
        if r.status == "ok":
            r.data["dimensions"] = {"radius1": radius1, "radius2": radius2, "height": height}
            r.message = f"Added cone: {obj_name} (r1={radius1}, r2={radius2}, h={height})"
        return r

    def add_torus(self, name: str = "", radius1: float = 10.0, radius2: float = 2.0,
                  position: Vec3 | None = None) -> ToolResponse:
        """Add a torus primitive."""
        obj_name = name or "Torus"
        props = {"Radius1": radius1, "Radius2": radius2}
        if position:
            props["Placement"] = {
                "Base": {"x": position.x, "y": position.y, "z": position.z}
            }
        r = self._backend.object_create("Part::Torus", obj_name, props)
        if r.status == "ok":
            r.data["dimensions"] = {"radius1": radius1, "radius2": radius2}
            r.message = f"Added torus: {obj_name} (R={radius1}, r={radius2})"
        return r

    def add_wedge(self, name: str = "", xmin: float = 0.0, ymin: float = 0.0,
                  zmin: float = 0.0, xmax: float = 10.0, ymax: float = 10.0,
                  zmax: float = 10.0, x2min: float = 0.0, z2min: float = 0.0,
                  x2max: float = 10.0, z2max: float = 10.0,
                  position: Vec3 | None = None) -> ToolResponse:
        """Add a wedge primitive."""
        obj_name = name or "Wedge"
        props = {
            "XMin": xmin, "YMin": ymin, "ZMin": zmin,
            "XMax": xmax, "YMax": ymax, "ZMax": zmax,
            "X2Min": x2min, "Z2Min": z2min,
            "X2Max": x2max, "Z2Max": z2max,
        }
        if position:
            props["Placement"] = {
                "Base": {"x": position.x, "y": position.y, "z": position.z}
            }
        r = self._backend.object_create("Part::Wedge", obj_name, props)
        if r.status == "ok":
            r.message = f"Added wedge: {obj_name}"
        return r

    def add_helix(self, name: str = "", pitch: float = 5.0, height: float = 20.0,
                  radius: float = 5.0, angle: float = 0.0, style: int = 0,
                  position: Vec3 | None = None) -> ToolResponse:
        """Add a helix (coil) primitive."""
        obj_name = name or "Helix"
        props = {"Pitch": pitch, "Height": height, "Radius": radius,
                 "Angle": angle, "LocalCoord": style}
        if position:
            props["Placement"] = {
                "Base": {"x": position.x, "y": position.y, "z": position.z}
            }
        r = self._backend.object_create("Part::Helix", obj_name, props)
        if r.status == "ok":
            r.message = f"Added helix: {obj_name} (pitch={pitch}, height={height})"
        return r
