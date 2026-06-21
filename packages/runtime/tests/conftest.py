import sys
from pathlib import Path

# Add runtime package to path
runtime_src = Path(__file__).resolve().parent.parent / "src"
if str(runtime_src) not in sys.path:
    sys.path.insert(0, str(runtime_src))

# Also add core package (dependency)
core_src = Path(__file__).resolve().parent.parent.parent / "core" / "src"
if str(core_src) not in sys.path:
    sys.path.insert(0, str(core_src))
