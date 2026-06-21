"""Supplementary tests for BOM — edge cases not in test_runtime.py.

Covers:
- BOMItem.to_dict() with zero values and rounding
- BOM.to_csv() / to_markdown() / to_table() with empty items
- BOM.to_json() formatting
- BOMGenerator._parse_objects() with various data structures
- BOMGenerator._object_to_bom_item() with shape/bounding_box/material
- BOMGenerator.from_plan() with sphere (radius-only volume)
- BOMGenerator.export_bom() default formats, empty project name, txt format
"""

from __future__ import annotations

import json
import math
import os

import pytest

from fc_runtime.bom import BOM, BOMGenerator, BOMItem
from fc_runtime.planner import Planner, Task, TaskType, TaskStatus


# ---------------------------------------------------------------------------
# BOMItem edge cases
# ---------------------------------------------------------------------------

class TestBOMItemToDictEdgeCases:
    """Test BOMItem.to_dict() with edge values."""

    def test_zero_volume_area_mass(self):
        """to_dict() should return 0 for zero volume/area/mass."""
        item = BOMItem(index=1, name="Empty")
        d = item.to_dict()
        assert d["volume_mm3"] == 0
        assert d["area_mm2"] == 0
        assert d["mass_g"] == 0

    def test_rounding_volume(self):
        """to_dict() rounds volume to 2 decimal places."""
        item = BOMItem(index=1, name="Rounding", volume=123.456789)
        d = item.to_dict()
        assert d["volume_mm3"] == 123.46

    def test_rounding_area(self):
        """to_dict() rounds area to 2 decimal places."""
        item = BOMItem(index=1, name="Area", area=99.999)
        d = item.to_dict()
        assert d["area_mm2"] == 100.0

    def test_rounding_mass(self):
        """to_dict() rounds mass to 2 decimal places."""
        item = BOMItem(index=1, name="Mass", mass=0.001)
        d = item.to_dict()
        assert d["mass_g"] == 0.0

    def test_negative_volume(self):
        """to_dict() handles negative volume (edge case from bad data)."""
        item = BOMItem(index=1, name="Neg", volume=-5.0)
        d = item.to_dict()
        assert d["volume_mm3"] == -5.0

    def test_all_fields_populated(self):
        """to_dict() includes all expected keys."""
        item = BOMItem(
            index=1, name="Full", label="F-001", type_id="Part::Box",
            quantity=3, material="Steel", dimensions={"l": 10},
            volume=100.0, area=50.0, mass=2.5, notes="test",
        )
        d = item.to_dict()
        assert d["index"] == 1
        assert d["name"] == "Full"
        assert d["label"] == "F-001"
        assert d["type_id"] == "Part::Box"
        assert d["quantity"] == 3
        assert d["material"] == "Steel"
        assert d["dimensions"] == {"l": 10}
        assert d["volume_mm3"] == 100.0
        assert d["area_mm2"] == 50.0
        assert d["mass_g"] == 2.5
        assert d["notes"] == "test"

    def test_default_dimensions_is_empty_dict(self):
        """Default dimensions should be an empty dict, not None."""
        item = BOMItem()
        assert item.dimensions == {}


# ---------------------------------------------------------------------------
# BOM format methods with empty items
# ---------------------------------------------------------------------------

class TestBOMFormatsEmpty:
    """Test BOM format methods when items list is empty."""

    def test_to_csv_empty(self):
        bom = BOM(project_name="Empty")
        csv = bom.to_csv()
        lines = csv.strip().split("\n")
        assert len(lines) == 1  # header only
        assert lines[0] == "Index,Name,Label,Type,Quantity,Material,Volume_mm3,Area_mm2,Mass_g,Notes"

    def test_to_markdown_empty(self):
        bom = BOM(project_name="Empty")
        md = bom.to_markdown()
        assert "# Bill of Materials: Empty" in md
        assert "**Total Parts:** 0" in md
        # Should still have table header
        assert "| # | Name | Type |" in md

    def test_to_table_empty(self):
        bom = BOM(project_name="Empty")
        table = bom.to_table()
        assert "Bill of Materials: Empty" in table
        assert "TOTAL" in table

    def test_to_json_empty(self):
        bom = BOM(project_name="Empty")
        data = json.loads(bom.to_json())
        assert data["total_parts"] == 0
        assert data["items"] == []

    def test_to_dict_empty(self):
        bom = BOM(project_name="Empty")
        d = bom.to_dict()
        assert d["total_parts"] == 0
        assert d["items"] == []
        assert d["total_volume_mm3"] == 0
        assert d["total_mass_g"] == 0


# ---------------------------------------------------------------------------
# BOM format methods with multiple items
# ---------------------------------------------------------------------------

class TestBOMFormatsMultiple:
    """Test BOM format methods with multiple items."""

    def _make_bom(self):
        bom = BOM(project_name="Multi")
        bom.items.append(BOMItem(
            index=1, name="Box", label="B1", type_id="Part::Box",
            quantity=1, material="Steel", volume=1000.0, area=600.0, mass=2.7,
        ))
        bom.items.append(BOMItem(
            index=2, name="Cylinder", label="C1", type_id="Part::Cylinder",
            quantity=2, material="Aluminum", volume=785.4, area=314.16, mass=2.12,
        ))
        bom.total_volume = 1785.4
        bom.total_mass = 4.82
        return bom

    def test_to_csv_two_items(self):
        bom = self._make_bom()
        csv = bom.to_csv()
        lines = csv.strip().split("\n")
        assert len(lines) == 3  # header + 2 items
        assert "Box" in lines[1]
        assert "Cylinder" in lines[2]

    def test_to_markdown_two_items(self):
        bom = self._make_bom()
        md = bom.to_markdown()
        assert "**Total Parts:** 2" in md
        assert "| 1 | Box | Part::Box |" in md
        assert "| 2 | Cylinder | Part::Cylinder |" in md

    def test_to_table_two_items(self):
        bom = self._make_bom()
        table = bom.to_table()
        assert "Box" in table
        assert "Cylinder" in table

    def test_to_json_two_items(self):
        bom = self._make_bom()
        data = json.loads(bom.to_json())
        assert len(data["items"]) == 2
        assert data["total_parts"] == 2


# ---------------------------------------------------------------------------
# BOMGenerator._parse_objects
# ---------------------------------------------------------------------------

class TestBOMGeneratorParseObjects:
    """Test BOMGenerator._parse_objects() with various data structures."""

    def setup_method(self):
        self.gen = BOMGenerator()

    def test_data_objects_structure(self):
        """Parse objects from {'data': {'objects': [...]}}."""
        data = {"data": {"objects": [{"name": "Box"}, {"name": "Cyl"}]}}
        result = self.gen._parse_objects(data)
        assert len(result) == 2
        assert result[0]["name"] == "Box"

    def test_top_level_objects(self):
        """Parse objects from {'objects': [...]}."""
        data = {"objects": [{"name": "A"}, {"name": "B"}]}
        result = self.gen._parse_objects(data)
        assert len(result) == 2

    def test_empty_dict(self):
        """Parse objects from empty dict returns empty list."""
        assert self.gen._parse_objects({}) == []

    def test_no_objects_key(self):
        """Parse objects when neither 'objects' nor 'data.objects' exist."""
        data = {"status": "ok", "count": 5}
        assert self.gen._parse_objects(data) == []

    def test_non_dict_input(self):
        """Parse objects with non-dict input returns empty list."""
        assert self.gen._parse_objects("not a dict") == []
        assert self.gen._parse_objects(None) == []


# ---------------------------------------------------------------------------
# BOMGenerator._object_to_bom_item
# ---------------------------------------------------------------------------

class TestBOMGeneratorObjectToBOMItem:
    """Test BOMGenerator._object_to_bom_item()."""

    def setup_method(self):
        self.gen = BOMGenerator()

    def test_basic_object(self):
        """Convert basic object dict to BOMItem."""
        obj = {"name": "Box", "label": "My Box", "type_id": "Part::Box"}
        item = self.gen._object_to_bom_item(obj, index=1)
        assert item.index == 1
        assert item.name == "Box"
        assert item.label == "My Box"
        assert item.type_id == "Part::Box"

    def test_object_with_shape(self):
        """Object with shape data extracts volume and area."""
        obj = {
            "name": "Box",
            "type_id": "Part::Box",
            "shape": {"volume": 1000.0, "area": 600.0},
        }
        item = self.gen._object_to_bom_item(obj, index=1)
        assert item.volume == 1000.0
        assert item.area == 600.0

    def test_object_with_bounding_box(self):
        """Object with bounding_box extracts dimensions."""
        obj = {
            "name": "Box",
            "type_id": "Part::Box",
            "bounding_box": {
                "x_min": 0, "x_max": 20,
                "y_min": 0, "y_max": 15,
                "z_min": 0, "z_max": 10,
            },
        }
        item = self.gen._object_to_bom_item(obj, index=1)
        assert item.dimensions["x"] == 20
        assert item.dimensions["y"] == 15
        assert item.dimensions["z"] == 10

    def test_object_with_material(self):
        """Object with Material field extracts material."""
        obj = {"name": "Part", "type_id": "Part::Box", "Material": "Steel"}
        item = self.gen._object_to_bom_item(obj, index=1)
        assert item.material == "Steel"

    def test_object_missing_fields(self):
        """Object with minimal fields gets defaults."""
        obj = {"name": "Min"}
        item = self.gen._object_to_bom_item(obj, index=1)
        assert item.name == "Min"
        assert item.type_id == "Unknown"
        assert item.volume == 0.0
        assert item.material == ""

    def test_object_completely_empty(self):
        """Empty dict gets default name."""
        obj = {}
        item = self.gen._object_to_bom_item(obj, index=3)
        assert item.name == "Part_3"
        assert item.type_id == "Unknown"


# ---------------------------------------------------------------------------
# BOMGenerator.from_plan with sphere
# ---------------------------------------------------------------------------

class TestBOMGeneratorFromPlanSphere:
    """Test BOM generation from plan with sphere (radius-only volume)."""

    def test_sphere_volume(self):
        """Sphere volume should be (4/3) * pi * r^3."""
        planner = Planner()
        plan = planner.plan("design a sphere with radius 10")

        gen = BOMGenerator()
        bom = gen.from_plan(plan)

        # Find sphere items
        sphere_items = [i for i in bom.items if "sphere" in i.name.lower()]
        if sphere_items:
            expected = (4 / 3) * math.pi * 10 ** 3
            assert abs(sphere_items[0].volume - expected) < 0.01

    def test_cylinder_volume_from_plan(self):
        """Cylinder volume should be pi * r^2 * h."""
        planner = Planner()
        plan = planner.plan("create a cylinder with radius 5 and height 20")

        gen = BOMGenerator()
        bom = gen.from_plan(plan)

        cyl_items = [i for i in bom.items if "cylinder" in i.name.lower()]
        if cyl_items:
            expected = math.pi * 5 ** 2 * 20
            assert abs(cyl_items[0].volume - expected) < 0.01


# ---------------------------------------------------------------------------
# BOMGenerator.export_bom edge cases
# ---------------------------------------------------------------------------

class TestBOMGeneratorExportEdgeCases:
    """Test BOMGenerator.export_bom() edge cases."""

    def test_default_formats(self, tmp_path):
        """When formats=None, default to json, csv, md."""
        bom = BOM(project_name="DefaultFmt")
        bom.items.append(BOMItem(index=1, name="Box", volume=100.0))

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path))

        assert len(files) == 3
        extensions = {os.path.splitext(f)[1] for f in files}
        assert ".json" in extensions
        assert ".csv" in extensions
        assert ".md" in extensions

    def test_empty_project_name(self, tmp_path):
        """Empty project name should use 'BOM' as base name."""
        bom = BOM(project_name="")
        bom.items.append(BOMItem(index=1, name="Box", volume=100.0))

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path), formats=["json"])

        assert len(files) == 1
        assert "BOM.json" in files[0]

    def test_project_name_with_spaces(self, tmp_path):
        """Project name with spaces should be underscored in filename."""
        bom = BOM(project_name="My Project")
        bom.items.append(BOMItem(index=1, name="Box", volume=100.0))

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path), formats=["csv"])

        assert len(files) == 1
        assert "My_Project.csv" in files[0]

    def test_txt_format_export(self, tmp_path):
        """Test txt (table) format export."""
        bom = BOM(project_name="TxtTest")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box", volume=100.0))
        bom.total_volume = 100.0

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=str(tmp_path), formats=["txt"])

        assert len(files) == 1
        assert files[0].endswith(".txt")
        with open(files[0]) as f:
            content = f.read()
        assert "Bill of Materials" in content

    def test_unsupported_format_ignored(self, tmp_path):
        """Unsupported format strings are silently ignored."""
        bom = BOM(project_name="Unsupported")
        bom.items.append(BOMItem(index=1, name="Box", volume=100.0))

        gen = BOMGenerator()
        files = gen.export_bom(
            bom, output_dir=str(tmp_path), formats=["json", "xyz", "html"],
        )

        # Only json should be produced
        assert len(files) == 1
        assert files[0].endswith(".json")

    def test_creates_output_directory(self, tmp_path):
        """export_bom should create the output directory if missing."""
        bom = BOM(project_name="NewDir")
        bom.items.append(BOMItem(index=1, name="Box", volume=100.0))
        out = str(tmp_path / "subdir" / "deep")

        gen = BOMGenerator()
        files = gen.export_bom(bom, output_dir=out, formats=["json"])

        assert len(files) == 1
        assert os.path.isdir(out)
        assert os.path.isfile(files[0])

    def test_all_four_formats(self, tmp_path):
        """Export all 4 formats at once."""
        bom = BOM(project_name="AllFormats")
        bom.items.append(BOMItem(index=1, name="Box", type_id="Part::Box", volume=100.0))
        bom.total_volume = 100.0

        gen = BOMGenerator()
        files = gen.export_bom(
            bom, output_dir=str(tmp_path), formats=["json", "csv", "md", "txt"],
        )

        assert len(files) == 4
        for f in files:
            assert os.path.isfile(f)
            assert os.path.getsize(f) > 0
