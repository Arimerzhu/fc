"""IO package for fc_core.

Provides high-level import/export utilities with format auto-detection,
export presets, and batch operations.
"""

from fc_core.io.export import (
    EXPORT_PRESETS,
    export_batch,
    export_with_preset,
    get_preset,
    list_presets,
)
from fc_core.io.import_mod import (
    detect_format,
    get_import_info,
    import_file,
    list_supported_formats,
)

__all__ = [
    # Export
    "EXPORT_PRESETS",
    "export_batch",
    "export_with_preset",
    "get_preset",
    "list_presets",
    # Import
    "detect_format",
    "get_import_info",
    "import_file",
    "list_supported_formats",
]
