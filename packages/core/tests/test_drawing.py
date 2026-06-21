"""Tests for fc_core.drawing module."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import pytest
from fc_core.drawing import (
    BoundBox,
    Edge3D,
    EngineeringDrawingSVG,
    ShapeData,
    Vector3,
)


class TestVector3:
    """Tests for Vector3."""

    def test_basic_arithmetic(self):
        a = Vector3(1, 2, 3)
        b = Vector3(4, 5, 6)
        assert a + b == Vector3(5, 7, 9)
        assert b - a == Vector3(3, 3, 3)
        assert a * 2 == Vector3(2, 4, 6)

    def test_dot_product(self):
        a = Vector3(1, 0, 0)
        b = Vector3(0, 1, 0)
        assert a.dot(b) == 0
        assert a.dot(a) == 1

    def test_cross_product(self):
        a = Vector3(1, 0, 0)
        b = Vector3(0, 1, 0)
        assert a.cross(b) == Vector3(0, 0, 1)

    def test_length_and_normalize(self):
        v = Vector3(3, 4, 0)
        assert v.length() == 5
        n = v.normalize()
        assert math.isclose(n.length(), 1.0)


class TestBoundBox:
    """Tests for BoundBox."""

    def test_dimensions(self):
        bb = BoundBox(0, 0, 0, 100, 50, 20)
        assert bb.width == 100
        assert bb.height == 50
        assert bb.depth == 20
        assert bb.center == Vector3(50, 25, 10)

    def test_diagonal(self):
        bb = BoundBox(0, 0, 0, 3, 4, 0)
        assert bb.diagonal == 5


class TestShapeData:
    """Tests for ShapeData."""

    def test_creation(self):
        edges = [Edge3D(Vector3(0, 0, 0), Vector3(100, 0, 0))]
        vertices = [Vector3(0, 0, 0), Vector3(100, 0, 0)]
        bb = BoundBox(0, 0, 0, 100, 0, 0)
        shape = ShapeData(edges=edges, vertices=vertices, bound_box=bb)
        assert len(shape.edges) == 1
        assert shape.bound_box.width == 100


class TestEngineeringDrawingSVG:
    """Tests for EngineeringDrawingSVG."""

    @staticmethod
    def _box_shape() -> ShapeData:
        """Create a simple box shape (12 edges)."""
        # Bottom face
        edges = [
            Edge3D(Vector3(0, 0, 0), Vector3(100, 0, 0)),
            Edge3D(Vector3(100, 0, 0), Vector3(100, 50, 0)),
            Edge3D(Vector3(100, 50, 0), Vector3(0, 50, 0)),
            Edge3D(Vector3(0, 50, 0), Vector3(0, 0, 0)),
            # Top face
            Edge3D(Vector3(0, 0, 30), Vector3(100, 0, 30)),
            Edge3D(Vector3(100, 0, 30), Vector3(100, 50, 30)),
            Edge3D(Vector3(100, 50, 30), Vector3(0, 50, 30)),
            Edge3D(Vector3(0, 50, 30), Vector3(0, 0, 30)),
            # Vertical edges
            Edge3D(Vector3(0, 0, 0), Vector3(0, 0, 30)),
            Edge3D(Vector3(100, 0, 0), Vector3(100, 0, 30)),
            Edge3D(Vector3(100, 50, 0), Vector3(100, 50, 30)),
            Edge3D(Vector3(0, 50, 0), Vector3(0, 50, 30)),
        ]
        vertices = [
            Vector3(0, 0, 0),
            Vector3(100, 0, 0),
            Vector3(100, 50, 0),
            Vector3(0, 50, 0),
            Vector3(0, 0, 30),
            Vector3(100, 0, 30),
            Vector3(100, 50, 30),
            Vector3(0, 50, 30),
        ]
        bb = BoundBox(0, 0, 0, 100, 50, 30)
        return ShapeData(edges=edges, vertices=vertices, bound_box=bb)

    def test_invalid_page_size(self):
        with pytest.raises(ValueError, match="不支持的图幅"):
            EngineeringDrawingSVG(self._box_shape(), page_size="A5")

    def test_svg_structure(self):
        drawing = EngineeringDrawingSVG(self._box_shape(), scale=0.4, page_size="A3")
        drawing.add_view("front", direction=(0, -1, 0), x=50, y=100)
        svg_string = drawing.to_string()

        # Parse as XML
        root = ET.fromstring(svg_string)
        assert root.tag.endswith("svg")
        assert root.get("width") == "297.0mm"
        assert root.get("height") == "420.0mm"

        # Should contain lines (edges)
        lines = root.findall(".//{http://www.w3.org/2000/svg}line")
        # Each of 12 edges becomes one line
        assert len(lines) >= 12

    def test_three_views(self):
        drawing = EngineeringDrawingSVG(self._box_shape(), scale=0.4, page_size="A3")
        drawing.add_view("front", direction=(0, -1, 0), x=50, y=100)
        drawing.add_view("top", direction=(0, 0, -1), x=50, y=250)
        drawing.add_view("side", direction=(-1, 0, 0), x=200, y=100)

        svg_string = drawing.to_string()
        root = ET.fromstring(svg_string)

        # Should have 3 view groups
        groups = [g for g in root.iter("{http://www.w3.org/2000/svg}g")
                  if g.get("class", "").startswith("view-")]
        assert len(groups) == 3

        # Each view should have lines
        for group in groups:
            lines = group.findall("{http://www.w3.org/2000/svg}line")
            assert len(lines) > 0

    def test_title_block(self):
        drawing = EngineeringDrawingSVG(self._box_shape())
        drawing.add_title_block(
            title="TestPart",
            scale="1:1",
            material="Steel",
            weight="1.2kg",
            unit="AI Lab",
            drawing_no="DRW-001",
            version="A",
            date="2026-06-17",
            quantity="1",
            drawn_by="AI",
            checked_by="Engineer",
        )
        svg_string = drawing.to_string()
        root = ET.fromstring(svg_string)

        tb_groups = [g for g in root.iter("{http://www.w3.org/2000/svg}g")
                     if g.get("class") == "title-block"]
        assert len(tb_groups) == 1

        text_elements = tb_groups[0].findall("{http://www.w3.org/2000/svg}text")
        texts = [t.text or "" for t in text_elements]
        assert "TestPart" in texts
        assert "1:1" in texts
        assert "Steel" in texts
        assert "AI Lab" in texts
        assert "DRW-001" in texts
        assert "2026-06-17" in texts

        # 分格标题栏应包含多个矩形单元格
        rects = tb_groups[0].findall("{http://www.w3.org/2000/svg}rect")
        assert len(rects) >= 11

    def test_dimension(self):
        drawing = EngineeringDrawingSVG(self._box_shape())
        drawing.add_dimension("linear", (0, 0, 0), (100, 0, 0), "100")
        svg_string = drawing.to_string()
        root = ET.fromstring(svg_string)

        dim_groups = [g for g in root.iter("{http://www.w3.org/2000/svg}g")
                      if g.get("class") == "dimension-linear"]
        assert len(dim_groups) == 1

        text_elements = dim_groups[0].findall("{http://www.w3.org/2000/svg}text")
        assert any("100" in (t.text or "") for t in text_elements)

        # 线性标注应包含引线和尺寸线
        lines = dim_groups[0].findall("{http://www.w3.org/2000/svg}line")
        assert len(lines) >= 3

    def test_diameter_dimension(self):
        drawing = EngineeringDrawingSVG(self._box_shape())
        # 圆心 (50, 25, 15)，圆上点 (70, 25, 15)，半径 20
        drawing.add_dimension("diameter", (50, 25, 15), (70, 25, 15), "40")
        svg_string = drawing.to_string()
        root = ET.fromstring(svg_string)

        dim_groups = [g for g in root.iter("{http://www.w3.org/2000/svg}g")
                      if g.get("class") == "dimension-diameter"]
        assert len(dim_groups) == 1

        text_elements = dim_groups[0].findall("{http://www.w3.org/2000/svg}text")
        assert any("φ40" in (t.text or "") for t in text_elements)

        # 直径标注应包含一条穿过圆心的尺寸线
        lines = dim_groups[0].findall("{http://www.w3.org/2000/svg}line")
        assert len(lines) >= 1

    def test_radius_dimension(self):
        drawing = EngineeringDrawingSVG(self._box_shape())
        drawing.add_dimension("radius", (50, 25, 15), (70, 25, 15), "20")
        svg_string = drawing.to_string()
        root = ET.fromstring(svg_string)

        dim_groups = [g for g in root.iter("{http://www.w3.org/2000/svg}g")
                      if g.get("class") == "dimension-radius"]
        assert len(dim_groups) == 1

        text_elements = dim_groups[0].findall("{http://www.w3.org/2000/svg}text")
        assert any("R20" in (t.text or "") for t in text_elements)

        lines = dim_groups[0].findall("{http://www.w3.org/2000/svg}line")
        assert len(lines) >= 1

    def test_angle_dimension(self):
        drawing = EngineeringDrawingSVG(self._box_shape())
        # 顶点在原点，两条边分别沿 X 轴和 Z 轴（front 视图可见），夹角 90°
        drawing.add_dimension("angle", (0, 0, 0), (50, 0, 0), "90", p3=(0, 0, 50))
        svg_string = drawing.to_string()
        root = ET.fromstring(svg_string)

        dim_groups = [g for g in root.iter("{http://www.w3.org/2000/svg}g")
                      if g.get("class") == "dimension-angle"]
        assert len(dim_groups) == 1

        text_elements = dim_groups[0].findall("{http://www.w3.org/2000/svg}text")
        assert any("90" in (t.text or "") for t in text_elements)

        # 角度标注应包含弧线 path
        paths = dim_groups[0].findall("{http://www.w3.org/2000/svg}path")
        assert len(paths) == 1

    def test_arrow_heads(self):
        drawing = EngineeringDrawingSVG(self._box_shape())
        drawing.add_dimension("linear", (0, 0, 0), (100, 0, 0), "100")
        svg_string = drawing.to_string()
        root = ET.fromstring(svg_string)

        dim_groups = [g for g in root.iter("{http://www.w3.org/2000/svg}g")
                      if g.get("class") == "dimension-linear"]
        arrow_groups = [g for g in dim_groups[0].iter("{http://www.w3.org/2000/svg}g")
                        if g.get("class") == "arrow-head"]
        assert len(arrow_groups) == 2

        # 每个箭头由两条线组成
        for arrow in arrow_groups:
            assert len(arrow.findall("{http://www.w3.org/2000/svg}line")) == 2

    def test_surface_roughness(self):
        drawing = EngineeringDrawingSVG(self._box_shape())
        drawing.add_surface_roughness((50, 25, 30), "3.2", (40, 80), method="车削")
        svg_string = drawing.to_string()
        root = ET.fromstring(svg_string)

        groups = [g for g in root.iter("{http://www.w3.org/2000/svg}g")
                  if g.get("class") == "symbol-surface_roughness"]
        assert len(groups) == 1

        text_elements = groups[0].findall("{http://www.w3.org/2000/svg}text")
        assert any("Ra 3.2" in (t.text or "") for t in text_elements)
        assert any("车削" in (t.text or "") for t in text_elements)

        lines = groups[0].findall("{http://www.w3.org/2000/svg}line")
        assert len(lines) >= 3

    def test_geometric_tolerance(self):
        drawing = EngineeringDrawingSVG(self._box_shape())
        drawing.add_geometric_tolerance("⊥", "0.05", "A", (40, 80))
        svg_string = drawing.to_string()
        root = ET.fromstring(svg_string)

        groups = [g for g in root.iter("{http://www.w3.org/2000/svg}g")
                  if g.get("class") == "symbol-geometric_tolerance"]
        assert len(groups) == 1

        text_elements = groups[0].findall("{http://www.w3.org/2000/svg}text")
        texts = [t.text or "" for t in text_elements]
        assert "⊥" in texts
        assert "0.05" in texts
        assert "A" in texts

        rects = groups[0].findall("{http://www.w3.org/2000/svg}rect")
        assert len(rects) == 1

    def test_weld_symbol(self):
        drawing = EngineeringDrawingSVG(self._box_shape())
        drawing.add_weld_symbol("V", (40, 80), side="both")
        svg_string = drawing.to_string()
        root = ET.fromstring(svg_string)

        groups = [g for g in root.iter("{http://www.w3.org/2000/svg}g")
                  if g.get("class") == "symbol-weld_symbol"]
        assert len(groups) == 1

        lines = groups[0].findall("{http://www.w3.org/2000/svg}line")
        assert len(lines) >= 4

    def test_save(self, tmp_path):
        drawing = EngineeringDrawingSVG(self._box_shape())
        drawing.add_view("front", direction=(0, -1, 0), x=50, y=100)
        output_path = tmp_path / "drawing.svg"
        drawing.save(str(output_path))

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert content.startswith("<svg")
        assert "front" in content

    def test_page_sizes(self):
        for size, (w, h) in [("A4", (210.0, 297.0)), ("A3", (297.0, 420.0))]:
            drawing = EngineeringDrawingSVG(self._box_shape(), page_size=size)
            svg_string = drawing.to_string()
            root = ET.fromstring(svg_string)
            assert root.get("width") == f"{w}mm"
            assert root.get("height") == f"{h}mm"

    def test_empty_shape(self):
        shape = ShapeData(edges=[], vertices=[], bound_box=BoundBox(0, 0, 0, 1, 1, 1))
        drawing = EngineeringDrawingSVG(shape)
        drawing.add_view("front", direction=(0, -1, 0), x=50, y=100)
        svg_string = drawing.to_string()
        assert "<svg" in svg_string
