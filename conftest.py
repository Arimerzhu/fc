"""Root conftest for fc project.

This file exists to prevent ImportPathMismatchError when pytest collects
tests from multiple packages that each have their own conftest.py.

Each package (core, cli, mcp, runtime) has its own conftest.py with
package-specific fixtures. pytest will load the nearest conftest.py
for each test file.
"""
