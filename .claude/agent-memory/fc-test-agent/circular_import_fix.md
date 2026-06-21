---
name: circular-import-fix
description: Fixed circular import in fc_core.geometry that prevented all core imports
metadata:
  type: project
---

Fixed circular import in `packages/core/src/fc_core/geometry/__init__.py` on 2026-06-10.

The import chain was: `fc_core.__init__` -> `fc_core.backend` -> `fc_core.geometry.operations` -> `fc_core.geometry.__init__` -> `fc_core.backend` (circular).

**Fix:** Changed `geometry/__init__.py` to use `TYPE_CHECKING` guard for the `BackendInterface` import instead of a top-level import.

**Why:** This was blocking ALL imports from `fc_core`, making the entire package unusable. Every test that imports from `fc_core.backend`, `fc_core.types`, etc. was failing.

**How to apply:** If any new circular import issues appear in this area, the pattern is to use `from typing import TYPE_CHECKING` with `if TYPE_CHECKING:` guards for cross-module type references.
