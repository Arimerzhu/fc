#!/usr/bin/env python3
"""Generate OpenAI Function Calling schemas from TOOL_SCHEMA.json.

Usage:
    python scripts/generate_function_schemas.py

Output:
    docs/FUNCTION_SCHEMAS.json
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
TOOL_SCHEMA_PATH = ROOT_DIR / "docs" / "TOOL_SCHEMA.json"
OUTPUT_PATH = ROOT_DIR / "docs" / "FUNCTION_SCHEMAS.json"


def parse_arg_string(arg: str) -> tuple[str, str, bool]:
    """Parse an argument string like '--name STR' or 'name STR' into (name, type, required)."""
    arg = arg.strip()

    # Determine if required (positional args are required, optional args start with --)
    required = not arg.startswith("--")

    # Extract name
    if arg.startswith("--"):
        # --name STR or --name
        parts = arg.split()
        name = parts[0].lstrip("-").replace("-", "_")
    else:
        # positional: "name STR" or "path PATH" or "op CUT|FUSE|COMMON"
        parts = arg.split()
        name = parts[0].replace("-", "_")

    # Determine type from the second part
    type_hint = parts[1] if len(parts) > 1 else ""

    return name, type_hint, required


def type_hint_to_json_schema(type_hint: str) -> dict:
    """Convert a type hint like 'STR', 'FLOAT', 'x,y,z' to JSON Schema type."""
    if not type_hint:
        return {"type": "string"}

    upper = type_hint.upper()

    # Integer types
    if upper in ("INT", "INTEGER", "N", "COUNT", "STEPS"):
        return {"type": "integer"}

    # Float types
    if upper in ("FLOAT", "FACTOR", "RADIUS", "SIZE", "DISTANCE", "THICKNESS",
                 "TOLERANCE", "ANGLE", "OFFSET", "SPACING", "REDUCTION"):
        return {"type": "number"}

    # Boolean / flag
    if upper in ("FLAG", "BOOL"):
        return {"type": "boolean"}

    # Comma-separated coordinates: "x,y,z" or "x,y"
    if "," in type_hint and all(p.strip().isalpha() for p in type_hint.split(",")):
        parts = [p.strip() for p in type_hint.split(",")]
        return {
            "type": "string",
            "description": f"Comma-separated coordinates ({', '.join(parts)})",
        }

    # Choice types: "CUT|FUSE|COMMON" or "XY|XZ|YZ"
    if "|" in type_hint:
        choices = [c.strip() for c in type_hint.split("|")]
        # Check if all choices are numeric
        try:
            [float(c) for c in choices]
            return {"type": "number", "enum": [float(c) for c in choices]}
        except ValueError:
            return {"type": "string", "enum": choices}

    # Default: string
    return {"type": "string"}


def arg_to_description(name: str, type_hint: str) -> str:
    """Generate a human-readable description for an argument."""
    # Common patterns
    descriptions = {
        "name": "Unique element name (e.g., Box_001)",
        "path": "File path",
        "output": "Output file path",
        "input": "Input file path",
        "type": "Primitive type",
        "op": "Operation type",
        "base": "Base object name",
        "tool": "Tool object name",
        "factor": "Scale factor",
        "radius": "Radius in mm",
        "size": "Size in mm",
        "diameter": "Diameter in mm",
        "depth": "Depth in mm",
        "length": "Length in mm",
        "width": "Width in mm",
        "height": "Height in mm",
        "thickness": "Thickness in mm",
        "distance": "Distance in mm",
        "angle": "Angle in degrees",
        "plane": "Plane (XY, XZ, or YZ)",
        "offset": "Offset distance in mm",
        "tolerance": "Tolerance value",
        "count": "Number of items",
        "spacing": "Spacing in mm",
        "plane": "Reference plane",
        "sketch": "Sketch name",
        "sheet": "Spreadsheet name",
        "cell": "Cell reference (e.g., A1)",
        "value": "Cell value",
        "formula": "Cell formula",
        "alias": "Cell alias",
        "object": "Object name",
        "material": "Material name",
        "analysis": "Analysis name",
        "job": "CAM job name",
        "format": "File format",
        "template": "Template path",
        "page": "Page name",
        "view": "View name",
        "source": "Source object name",
        "property": "Property name",
        "library": "Library name",
        "assembly": "Assembly name",
        "timeout": "Timeout in seconds",
        "description": "Description text",
        "text": "Text content",
        "rotation": "Rotation axis (rx,ry,rz)",
        "direction": "Direction vector (x,y,z)",
        "edges": "Edge selection (all or comma-separated indices)",
        "faces": "Face selection (all or comma-separated indices)",
        "range": "Cell range (e.g., A1:C10)",
        "start": "Start value",
        "end": "End value",
        "steps": "Number of steps",
        "reversed": "Reverse direction (flag)",
        "symmetric": "Symmetric extent (flag)",
        "solid": "Create solid (flag)",
        "ruled": "Ruled surface (flag)",
        "closed": "Close wire (flag)",
        "overwrite": "Overwrite existing file (flag)",
        "fix_degenerates": "Fix degenerate mesh elements (flag)",
        "fix_duplicates": "Fix duplicate mesh elements (flag)",
        "fix_normals": "Fix mesh normals (flag)",
        "iterations": "Number of iterations",
        "reduction": "Reduction ratio (0.0-1.0)",
        "max_size": "Maximum mesh element size",
        "min_size": "Minimum mesh element size",
        "speed": "Tool speed",
        "feed": "Feed rate",
        "post": "Post-processor name",
    }

    if name in descriptions:
        return descriptions[name]

    # Generic description
    clean_name = name.replace("_", " ").title()
    if type_hint:
        return f"{clean_name} ({type_hint})"
    return clean_name


def generate_function_schemas(toolkit: dict) -> list[dict]:
    """Generate OpenAI function calling schemas from toolkit command groups."""
    functions = []
    groups = toolkit.get("command_groups", {})

    for group_name, group_data in groups.items():
        commands = group_data.get("commands", {})

        for cmd_name, cmd_data in commands.items():
            # Build function name: group_command (e.g., part_add, document_new)
            fn_name = f"{group_name}_{cmd_name}".replace("-", "_")

            # Build description
            fn_desc = cmd_data.get("fn", f"{group_name} {cmd_name}")
            ret = cmd_data.get("ret", "")
            if ret:
                fn_desc += f" Returns: {ret}."

            # Build parameters
            properties = {}
            required = []

            args = cmd_data.get("args", [])
            for arg in args:
                arg_name, type_hint, is_required = parse_arg_string(arg)
                prop = type_hint_to_json_schema(type_hint)
                prop["description"] = arg_to_description(arg_name, type_hint)
                properties[arg_name] = prop
                if is_required:
                    required.append(arg_name)

            # Add --json flag as optional
            properties["json_output"] = {
                "type": "boolean",
                "description": "Output in JSON format (recommended for agents)",
                "default": True,
            }

            function_def = {
                "type": "function",
                "function": {
                    "name": fn_name,
                    "description": fn_desc,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                    },
                },
            }

            if required:
                function_def["function"]["parameters"]["required"] = required

            # Add example
            example = cmd_data.get("ex", "")
            if example:
                function_def["function"]["example"] = example

            functions.append(function_def)

    return functions


def main():
    # Load TOOL_SCHEMA.json
    if not TOOL_SCHEMA_PATH.exists():
        print(f"Error: {TOOL_SCHEMA_PATH} not found", file=sys.stderr)
        sys.exit(1)

    with open(TOOL_SCHEMA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    toolkit = data["FreeCAD_CLI_Toolkit"]

    # Generate function schemas
    functions = generate_function_schemas(toolkit)

    # Build output
    output = {
        "schema_version": "1.0",
        "generated": "2026-06-11",
        "description": "OpenAI Function Calling schemas for FreeCAD CLI",
        "source": "docs/TOOL_SCHEMA.json",
        "total_functions": len(functions),
        "functions": functions,
    }

    # Write output
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(functions)} function schemas")
    print(f"Output: {OUTPUT_PATH}")

    # Print summary by group
    from collections import Counter
    group_counts = Counter()
    for fn in functions:
        group = fn["function"]["name"].split("_")[0]
        group_counts[group] += 1

    print("\nFunctions by group:")
    for group, count in sorted(group_counts.items()):
        print(f"  {group}: {count}")


if __name__ == "__main__":
    main()
