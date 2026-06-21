"""BOM Generator — Bill of Materials extraction and generation.

Extracts part information from FreeCAD documents and generates
structured BOM reports in multiple formats.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BOMItem:
    """A single item in the Bill of Materials."""
    index: int = 0
    name: str = ""
    label: str = ""
    type_id: str = ""
    quantity: int = 1
    material: str = ""
    dimensions: dict[str, float] = field(default_factory=dict)
    volume: float = 0.0
    area: float = 0.0
    mass: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "label": self.label,
            "type_id": self.type_id,
            "quantity": self.quantity,
            "material": self.material,
            "dimensions": self.dimensions,
            "volume_mm3": round(self.volume, 2) if self.volume else 0,
            "area_mm2": round(self.area, 2) if self.area else 0,
            "mass_g": round(self.mass, 2) if self.mass else 0,
            "notes": self.notes,
        }


@dataclass
class BOM:
    """Complete Bill of Materials for a design."""
    project_name: str = ""
    items: list[BOMItem] = field(default_factory=list)
    total_parts: int = 0
    total_volume: float = 0.0
    total_mass: float = 0.0
    units: str = "mm"

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "total_parts": len(self.items),
            "total_volume_mm3": round(self.total_volume, 2),
            "total_mass_g": round(self.total_mass, 2),
            "units": self.units,
            "items": [item.to_dict() for item in self.items],
        }

    def to_table(self) -> str:
        """Format as a readable table."""
        lines = []
        lines.append(f"{'='*70}")
        lines.append(f"  Bill of Materials: {self.project_name}")
        lines.append(f"{'='*70}")
        lines.append(f"  {'#':<4} {'Name':<20} {'Type':<20} {'Qty':>4} {'Volume(mm³)':>12}")
        lines.append(f"  {'-'*4} {'-'*20} {'-'*20} {'-'*4} {'-'*12}")

        for item in self.items:
            lines.append(
                f"  {item.index:<4} {item.name:<20} {item.type_id:<20} "
                f"{item.quantity:>4} {item.volume:>12.2f}"
            )

        lines.append(f"  {'-'*4} {'-'*20} {'-'*20} {'-'*4} {'-'*12}")
        lines.append(f"  {'TOTAL':<4} {len(self.items):<20} {'':<20} {'':>4} {self.total_volume:>12.2f}")
        lines.append(f"{'='*70}")

        return "\n".join(lines)

    def to_csv(self) -> str:
        """Format as CSV."""
        lines = ["Index,Name,Label,Type,Quantity,Material,Volume_mm3,Area_mm2,Mass_g,Notes"]
        for item in self.items:
            lines.append(
                f"{item.index},{item.name},{item.label},{item.type_id},"
                f"{item.quantity},{item.material},{item.volume:.2f},"
                f"{item.area:.2f},{item.mass:.2f},{item.notes}"
            )
        return "\n".join(lines)

    def to_json(self) -> str:
        """Format as JSON."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Format as Markdown."""
        lines = []
        lines.append(f"# Bill of Materials: {self.project_name}")
        lines.append("")
        lines.append(f"**Total Parts:** {len(self.items)}  ")
        lines.append(f"**Total Volume:** {self.total_volume:.2f} mm³  ")
        lines.append(f"**Total Mass:** {self.total_mass:.2f} g  ")
        lines.append("")
        lines.append("| # | Name | Type | Qty | Volume (mm³) | Mass (g) |")
        lines.append("|---|------|------|-----|-------------|---------|")
        for item in self.items:
            lines.append(
                f"| {item.index} | {item.name} | {item.type_id} | "
                f"{item.quantity} | {item.volume:.2f} | {item.mass:.2f} |"
            )
        return "\n".join(lines)


class BOMGenerator:
    """Generates BOM from FreeCAD documents."""

    def __init__(self, fc_path: str = "fc", timeout: int = 120):
        self._fc_path = fc_path
        self._timeout = timeout

    def from_document(self, doc_path: str | None = None) -> BOM:
        """Generate BOM from the current or specified document.

        Args:
            doc_path: Path to .FCStd file. If None, uses current document.

        Returns:
            BOM with all parts
        """
        bom = BOM()

        # Get object list
        if doc_path:
            cmd = [self._fc_path, "document", "open", doc_path, "--json"]
            self._run(cmd)

        cmd = [self._fc_path, "part", "list", "--json"]
        result = self._run(cmd)

        if result:
            objects = self._parse_objects(result)
            idx = 0
            for obj in objects:
                idx += 1
                item = self._object_to_bom_item(obj, idx)
                bom.items.append(item)
                bom.total_volume += item.volume

        return bom

    def from_plan(self, plan, working_dir: str | None = None) -> BOM:
        """Generate BOM from an executed plan's context.

        Args:
            plan: The executed Plan object
            working_dir: Working directory where output files exist

        Returns:
            BOM with parts from the plan
        """
        bom = BOM(project_name=plan.goal[:50])

        idx = 0
        for task in plan.tasks:
            task_status = task.status.value if hasattr(task.status, "value") else task.status
            task_type = task.type.value if hasattr(task.type, "value") else task.type
            if task_status == "success" and task_type == "part_add":
                idx += 1
                item = BOMItem(
                    index=idx,
                    name=task.params.get(f"part_type", "unknown").capitalize(),
                    type_id=f"Part::{task.params.get('part_type', 'unknown').capitalize()}",
                    quantity=1,
                )
                # Extract dimensions from params
                dims = {}
                for key in ["length", "width", "height", "radius", "radius1", "radius2"]:
                    if key in task.params:
                        dims[key] = float(task.params[key])
                item.dimensions = dims

                # Calculate volume
                if "length" in dims and "width" in dims and "height" in dims:
                    item.volume = dims["length"] * dims["width"] * dims["height"]
                elif "radius" in dims and "height" in dims:
                    import math
                    item.volume = math.pi * dims["radius"] ** 2 * dims["height"]
                elif "radius" in dims:
                    import math
                    item.volume = (4 / 3) * math.pi * dims["radius"] ** 3

                bom.items.append(item)
                bom.total_volume += item.volume

        bom.total_mass = bom.total_volume * 0.0027  # Rough Al density g/mm³
        return bom

    def export_bom(self, bom: BOM, output_dir: str = ".",
                   formats: list[str] | None = None) -> list[str]:
        """Export BOM to files.

        Args:
            bom: The BOM to export
            output_dir: Output directory
            formats: List of formats ('json', 'csv', 'md', 'txt')

        Returns:
            List of output file paths
        """
        if formats is None:
            formats = ["json", "csv", "md"]

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        files = []
        base_name = bom.project_name.replace(" ", "_") or "BOM"

        if "json" in formats:
            path = output_path / f"{base_name}.json"
            path.write_text(bom.to_json(), encoding="utf-8")
            files.append(str(path))

        if "csv" in formats:
            path = output_path / f"{base_name}.csv"
            path.write_text(bom.to_csv(), encoding="utf-8")
            files.append(str(path))

        if "md" in formats:
            path = output_path / f"{base_name}.md"
            path.write_text(bom.to_markdown(), encoding="utf-8")
            files.append(str(path))

        if "txt" in formats:
            path = output_path / f"{base_name}.txt"
            path.write_text(bom.to_table(), encoding="utf-8")
            files.append(str(path))

        return files

    def _run(self, cmd: list[str]) -> dict[str, Any] | None:
        """Run an fc command and parse JSON output."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    # Try to find JSON in output
                    for line in result.stdout.splitlines():
                        line = line.strip()
                        if line.startswith("{"):
                            try:
                                return json.loads(line)
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"Command failed: {' '.join(cmd)} — {e}")
        return None

    def _parse_objects(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse object list from command output."""
        if isinstance(data, dict):
            # Try common structures
            if "data" in data and isinstance(data["data"], dict):
                if "objects" in data["data"]:
                    return data["data"]["objects"]
            if "objects" in data:
                return data["objects"]
        return []

    def _object_to_bom_item(self, obj: dict[str, Any], index: int) -> BOMItem:
        """Convert an object dict to a BOMItem."""
        item = BOMItem(
            index=index,
            name=obj.get("name", f"Part_{index}"),
            label=obj.get("label", ""),
            type_id=obj.get("type_id", "Unknown"),
        )

        # Extract shape info
        shape = obj.get("shape", {})
        if shape:
            item.volume = shape.get("volume", 0)
            item.area = shape.get("area", 0)

        # Extract bounding box for dimensions
        bb = obj.get("bounding_box", {})
        if bb:
            item.dimensions = {
                "x": bb.get("x_max", 0) - bb.get("x_min", 0),
                "y": bb.get("y_max", 0) - bb.get("y_min", 0),
                "z": bb.get("z_max", 0) - bb.get("z_min", 0),
            }

        # Extract material if available
        if "Material" in obj:
            item.material = str(obj["Material"])

        return item
