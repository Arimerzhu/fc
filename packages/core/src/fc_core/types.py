"""Core types and data models for FreeCAD CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Units(str, Enum):
    """Supported length units."""
    MM = "mm"
    CM = "cm"
    M = "m"
    INCH = "in"
    FOOT = "ft"


class ExportFormat(str, Enum):
    """Supported export formats."""
    STEP = "step"
    IGES = "iges"
    STL = "stl"
    OBJ = "obj"
    BREP = "brep"
    DXF = "dxf"
    DWG = "dwg"
    SVG = "svg"
    GLTF = "gltf"
    THREE_MF = "3mf"
    PLY = "ply"
    OFF = "off"
    AMF = "amf"
    PDF = "pdf"
    FCSTD = "fcstd"
    PNG = "png"
    JPG = "jpg"


class ImportFormat(str, Enum):
    """Supported import formats."""
    STEP = "step"
    IGES = "iges"
    STL = "stl"
    OBJ = "obj"
    DXF = "dxf"
    DWG = "dwg"
    SVG = "svg"
    BREP = "brep"
    THREE_MF = "3mf"
    PLY = "ply"
    OFF = "off"
    GLTF = "gltf"


@dataclass
class Vec3:
    """3D vector."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_list(self) -> list[float]:
        return [self.x, self.y, self.z]

    @classmethod
    def from_list(cls, v: list[float]) -> Vec3:
        return cls(x=v[0], y=v[1], z=v[2])

    @classmethod
    def parse(cls, s: str) -> Vec3:
        """Parse 'x,y,z' string to Vec3."""
        parts = s.split(",")
        if len(parts) != 3:
            raise ValueError(f"Expected x,y,z format, got: {s}")
        return cls(x=float(parts[0].strip()), y=float(parts[1].strip()), z=float(parts[2].strip()))


@dataclass
class Placement:
    """FreeCAD placement (position + rotation)."""
    position: Vec3 = field(default_factory=Vec3)
    rotation_axis: Vec3 = field(default_factory=lambda: Vec3(0, 0, 1))
    rotation_angle: float = 0.0  # degrees


@dataclass
class Color:
    """RGBA color (0.0-1.0 range)."""
    r: float = 0.5
    g: float = 0.5
    b: float = 0.5
    a: float = 1.0

    def to_list(self) -> list[float]:
        return [self.r, self.g, self.b, self.a]


@dataclass
class BoundingBox:
    """3D bounding box."""
    x_min: float = 0.0
    x_max: float = 0.0
    y_min: float = 0.0
    y_max: float = 0.0
    z_min: float = 0.0
    z_max: float = 0.0

    @property
    def dimensions(self) -> Vec3:
        return Vec3(
            x=self.x_max - self.x_min,
            y=self.y_max - self.y_min,
            z=self.z_max - self.z_min,
        )


@dataclass
class DocumentInfo:
    """Document information."""
    name: str
    file_path: str | None = None
    label: str = ""
    objects_count: int = 0
    units: str = "mm"
    modified: bool = False


@dataclass
class ObjectInfo:
    """FreeCAD object information."""
    name: str
    label: str = ""
    type_id: str = ""
    placement: Placement = field(default_factory=Placement)
    bounding_box: BoundingBox | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResponse:
    """Standard tool/command response."""
    status: str  # "ok" | "error"
    operation: str
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error_code: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"status": self.status, "operation": self.operation}
        if self.data:
            result["data"] = self.data
        if self.message:
            result["message"] = self.message
        if self.status == "error":
            result["error"] = {
                "code": self.error_code,
                "message": self.message,
            }
            if self.suggestion:
                result["error"]["suggestion"] = self.suggestion
        return result

    @classmethod
    def ok(cls, operation: str, data: dict[str, Any] | None = None, message: str = "") -> ToolResponse:
        return cls(status="ok", operation=operation, data=data or {}, message=message)

    @classmethod
    def error(cls, operation: str, error_code: str, message: str, suggestion: str = "") -> ToolResponse:
        return cls(status="error", operation=operation, error_code=error_code,
                   message=message, suggestion=suggestion)
