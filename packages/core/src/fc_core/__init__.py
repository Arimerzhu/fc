"""fc_core — FreeCAD CLI Core Package

Provides dual-backend (Headless + RPC) abstraction, document management,
geometry operations, sketching, PartDesign features, and engineering APIs.
"""

__version__ = "0.1.0"

from fc_core.backend import (
    BackendInterface,
    HeadlessBackend,
    RPCBackend,
    find_freecad,
)
from fc_core.security import (
    SecurityError,
    validate_export_path,
    validate_import_path,
    validate_name,
    validate_path,
)
from fc_core.session import SessionInfo, SessionManager
from fc_core.verify import (
    CADVerifier,
    CheckResult,
    VerifyReport,
)
from fc_core.types import (
    BoundingBox,
    Color,
    DocumentInfo,
    ExportFormat,
    ImportFormat,
    ObjectInfo,
    Placement,
    ToolResponse,
    Units,
    Vec3,
)

__all__ = [
    "BackendInterface",
    "HeadlessBackend",
    "RPCBackend",
    "find_freecad",
    "BoundingBox",
    "CADVerifier",
    "CheckResult",
    "Color",
    "DocumentInfo",
    "ExportFormat",
    "ImportFormat",
    "ObjectInfo",
    "Placement",
    "SecurityError",
    "SessionInfo",
    "SessionManager",
    "ToolResponse",
    "Units",
    "Vec3",
    "VerifyReport",
    "validate_export_path",
    "validate_import_path",
    "validate_name",
    "validate_path",
]
