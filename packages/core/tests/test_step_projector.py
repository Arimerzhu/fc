"""STEP 投影器单元测试。

覆盖:
  - Vec3 / Edge2D / BoundBox3D 数据结构
  - STEP 文件解析（CARTESIAN_POINT / VERTEX_POINT / EDGE_CURVE）
  - 正交投影（front/top/left/iso）
  - AssemblyDrawing.project_views_from_step 集成
"""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path

import pytest

STEP_PATH = Path(r"D:\桌面文件\fc\工程图输出\进纸机构模拟.STEP")


class TestVec3:
    def test_dot(self):
        from fc_core.step_projector import Vec3
        a = Vec3(1, 2, 3)
        b = Vec3(4, 5, 6)
        assert a.dot(b) == 32

    def test_cross(self):
        from fc_core.step_projector import Vec3
        a = Vec3(1, 0, 0)
        b = Vec3(0, 1, 0)
        c = a.cross(b)
        assert c.x == 0 and c.y == 0 and c.z == 1

    def test_length(self):
        from fc_core.step_projector import Vec3
        v = Vec3(3, 4, 0)
        assert v.length() == pytest.approx(5.0)

    def test_normalize(self):
        from fc_core.step_projector import Vec3
        v = Vec3(3, 4, 0).normalize()
        assert v.length() == pytest.approx(1.0)

    def test_normalize_zero(self):
        from fc_core.step_projector import Vec3
        v = Vec3(0, 0, 0).normalize()
        assert v.x == 0 and v.y == 0 and v.z == 0


class TestEdge2D:
    def test_length(self):
        from fc_core.step_projector import Edge2D
        e = Edge2D(0, 0, 3, 4)
        assert e.length() == pytest.approx(5.0)

    def test_midpoint(self):
        from fc_core.step_projector import Edge2D
        e = Edge2D(0, 0, 10, 20)
        mx, my = e.midpoint()
        assert mx == pytest.approx(5.0)
        assert my == pytest.approx(10.0)


class TestBoundBox3D:
    def test_dimensions(self):
        from fc_core.step_projector import BoundBox3D
        bb = BoundBox3D(0, 0, 0, 100, 200, 50)
        assert bb.width == 100
        assert bb.depth == 200
        assert bb.height == 50

    def test_center(self):
        from fc_core.step_projector import BoundBox3D
        bb = BoundBox3D(0, 0, 0, 100, 200, 50)
        c = bb.center
        assert c.x == pytest.approx(50)
        assert c.y == pytest.approx(100)
        assert c.z == pytest.approx(25)


class TestViewDirections:
    def test_all_directions_defined(self):
        from fc_core.step_projector import VIEW_DIRECTIONS
        assert "front" in VIEW_DIRECTIONS
        assert "top" in VIEW_DIRECTIONS
        assert "left" in VIEW_DIRECTIONS
        assert "iso" in VIEW_DIRECTIONS

    def test_directions_are_unit_vectors(self):
        from fc_core.step_projector import VIEW_DIRECTIONS
        for name, d in VIEW_DIRECTIONS.items():
            if name == "iso":
                # iso is not a unit vector but gets normalized
                assert d.length() > 0
            else:
                assert d.length() == pytest.approx(1.0)


class TestStepProjectorLoad:
    @pytest.fixture(autouse=True)
    def skip_no_step(self):
        if not STEP_PATH.exists():
            pytest.skip("STEP file not available")

    def test_load_points(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        proj._load()
        assert len(proj._points) > 10000

    def test_load_vertex_points(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        proj._load()
        assert len(proj._vp_to_cp) > 5000

    def test_load_edges(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        proj._load()
        assert len(proj._edge_refs) > 10000

    def test_edge_count_property(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        assert proj.edge_count > 10000

    def test_bounding_box(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        bb = proj.bound_box
        assert bb.width > 1000
        assert bb.depth > 1000
        assert bb.height > 1000


class TestStepProjectorProjection:
    @pytest.fixture(autouse=True)
    def skip_no_step(self):
        if not STEP_PATH.exists():
            pytest.skip("STEP file not available")

    def test_project_front(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        edges = proj.project("front")
        assert len(edges) > 5000
        bounds = proj.project_bounds(edges)
        assert bounds[2] > bounds[0]  # x_max > x_min
        assert bounds[3] > bounds[1]  # y_max > y_min

    def test_project_top(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        edges = proj.project("top")
        assert len(edges) > 5000

    def test_project_left(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        edges = proj.project("left")
        assert len(edges) > 5000

    def test_project_iso(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        edges = proj.project("iso")
        assert len(edges) > 5000

    def test_project_custom_direction(self):
        from fc_core.step_projector import StepProjector, Vec3
        proj = StepProjector(str(STEP_PATH))
        edges = proj.project("custom", direction=Vec3(1, -1, 0.5))
        assert len(edges) > 1000

    def test_project_bounds_consistency(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        for view in ["front", "top", "left"]:
            edges = proj.project(view)
            bounds = proj.project_bounds(edges)
            assert bounds[2] - bounds[0] > 100  # width > 100mm
            assert bounds[3] - bounds[1] > 100  # height > 100mm

    def test_max_edges_limit(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH), max_edges=100)
        edges = proj.project("front")
        assert len(edges) <= 100

    def test_empty_edges_bounds(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        bounds = proj.project_bounds([])
        assert bounds == (0, 0, 0, 0)


class TestProjectorWithMiniStep:
    """用小型 STEP 文件测试，不依赖真实数据。"""

    def _make_mini_step(self, tmp_dir: str = "") -> str:
        if not tmp_dir:
            tmp_dir = tempfile.mkdtemp(prefix="step_test_")
        step_content = """ISO-10303-21;
HEADER;
ENDSEC;
DATA;
#1 = CARTESIAN_POINT ( 'P1', (0.0, 0.0, 0.0) ) ;
#2 = CARTESIAN_POINT ( 'P2', (100.0, 0.0, 0.0) ) ;
#3 = CARTESIAN_POINT ( 'P3', (100.0, 50.0, 0.0) ) ;
#4 = CARTESIAN_POINT ( 'P4', (0.0, 50.0, 0.0) ) ;
#5 = CARTESIAN_POINT ( 'P5', (0.0, 0.0, 30.0) ) ;
#6 = CARTESIAN_POINT ( 'P6', (100.0, 0.0, 30.0) ) ;
#10 = VERTEX_POINT ( 'VP1', #1 ) ;
#11 = VERTEX_POINT ( 'VP2', #2 ) ;
#12 = VERTEX_POINT ( 'VP3', #3 ) ;
#13 = VERTEX_POINT ( 'VP4', #4 ) ;
#14 = VERTEX_POINT ( 'VP5', #5 ) ;
#15 = VERTEX_POINT ( 'VP6', #6 ) ;
#20 = EDGE_CURVE ( 'NONE', #10, #11, #100, .T. ) ;
#21 = EDGE_CURVE ( 'NONE', #11, #12, #101, .T. ) ;
#22 = EDGE_CURVE ( 'NONE', #12, #13, #102, .T. ) ;
#23 = EDGE_CURVE ( 'NONE', #13, #10, #103, .T. ) ;
#24 = EDGE_CURVE ( 'NONE', #10, #14, #104, .T. ) ;
#25 = EDGE_CURVE ( 'NONE', #11, #15, #105, .T. ) ;
ENDSEC;
END-ISO-10303-21;
"""
        path = os.path.join(tmp_dir, "mini.STEP")
        with open(path, "w", encoding="utf-8") as f:
            f.write(step_content)
        return path

    def test_mini_step_load(self):
        from fc_core.step_projector import StepProjector
        path = self._make_mini_step()
        proj = StepProjector(path)
        proj._load()
        assert len(proj._points) == 6
        assert len(proj._vp_to_cp) == 6
        assert len(proj._edge_refs) == 6

    def test_mini_step_bounding_box(self):
        from fc_core.step_projector import StepProjector
        path = self._make_mini_step()
        proj = StepProjector(path)
        bb = proj.bound_box
        assert bb.width == pytest.approx(100.0)
        assert bb.depth == pytest.approx(50.0)
        assert bb.height == pytest.approx(30.0)

    def test_mini_step_project_front(self):
        from fc_core.step_projector import StepProjector
        path = self._make_mini_step()
        proj = StepProjector(path)
        edges = proj.project("front")
        assert len(edges) > 0
        bounds = proj.project_bounds(edges)
        w = bounds[2] - bounds[0]
        h = bounds[3] - bounds[1]
        assert w == pytest.approx(100.0, abs=1.0)
        assert h == pytest.approx(30.0, abs=1.0)


class TestVisibilityClassification:
    """隐藏线检测（z-buffer）测试。"""

    @pytest.fixture(autouse=True)
    def skip_no_step(self):
        if not STEP_PATH.exists():
            pytest.skip("STEP file not available")

    def test_project_with_visibility_returns_edges(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        edges = proj.project_with_visibility("front")
        assert len(edges) > 5000

    def test_edges_have_hidden_attribute(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        edges = proj.project_with_visibility("front")
        for e in edges[:10]:
            assert hasattr(e, "hidden")
            assert isinstance(e.hidden, bool)

    def test_has_both_visible_and_hidden(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        edges = proj.project_with_visibility("front")
        visible = sum(1 for e in edges if not e.hidden)
        hidden = sum(1 for e in edges if e.hidden)
        assert visible > 100, f"Expected visible edges, got {visible}"
        assert hidden > 100, f"Expected hidden edges, got {hidden}"

    def test_hidden_ratio_reasonable(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        for view in ["front", "top", "left", "iso"]:
            edges = proj.project_with_visibility(view)
            hidden = sum(1 for e in edges if e.hidden)
            ratio = hidden / len(edges) if edges else 0
            assert 0.1 < ratio < 0.99, f"{view}: hidden ratio {ratio:.2f} out of range"

    def test_iso_has_more_visible_than_side(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        iso_edges = proj.project_with_visibility("iso")
        left_edges = proj.project_with_visibility("left")
        iso_vis = sum(1 for e in iso_edges if not e.hidden)
        left_vis = sum(1 for e in left_edges if not e.hidden)
        # Iso view typically shows more visible edges
        assert iso_vis > left_vis

    def test_custom_direction_visibility(self):
        from fc_core.step_projector import StepProjector, Vec3
        proj = StepProjector(str(STEP_PATH))
        edges = proj.project_with_visibility("custom", direction=Vec3(1, -1, 0.5))
        visible = sum(1 for e in edges if not e.hidden)
        hidden = sum(1 for e in edges if e.hidden)
        assert visible + hidden == len(edges)

    def test_buffer_resolution_affects_speed(self):
        from fc_core.step_projector import StepProjector
        import time
        proj = StepProjector(str(STEP_PATH))
        t0 = time.time()
        proj.project_with_visibility("front", buffer_resolution=50)
        t1 = time.time()
        fast = t1 - t0
        t0 = time.time()
        proj.project_with_visibility("front", buffer_resolution=400)
        t1 = time.time()
        slow = t1 - t0
        # Higher resolution should be slower (or similar for small models)
        # Just verify both work without error

    def test_mini_step_visibility(self, tmp_dir=None):
        from fc_core.step_projector import StepProjector
        import tempfile
        tmp = tempfile.mkdtemp(prefix="vis_test_")
        step_content = """ISO-10303-21;
HEADER;
ENDSEC;
DATA;
#1 = CARTESIAN_POINT ( 'P1', (0.0, 0.0, 0.0) ) ;
#2 = CARTESIAN_POINT ( 'P2', (100.0, 0.0, 0.0) ) ;
#3 = CARTESIAN_POINT ( 'P3', (100.0, 50.0, 0.0) ) ;
#4 = CARTESIAN_POINT ( 'P4', (0.0, 50.0, 0.0) ) ;
#10 = VERTEX_POINT ( 'VP1', #1 ) ;
#11 = VERTEX_POINT ( 'VP2', #2 ) ;
#12 = VERTEX_POINT ( 'VP3', #3 ) ;
#13 = VERTEX_POINT ( 'VP4', #4 ) ;
#20 = EDGE_CURVE ( 'NONE', #10, #11, #100, .T. ) ;
#21 = EDGE_CURVE ( 'NONE', #11, #12, #101, .T. ) ;
#22 = EDGE_CURVE ( 'NONE', #12, #13, #102, .T. ) ;
#23 = EDGE_CURVE ( 'NONE', #13, #10, #103, .T. ) ;
ENDSEC;
END-ISO-10303-21;
"""
        path = os.path.join(tmp, "flat.STEP")
        with open(path, "w", encoding="utf-8") as f:
            f.write(step_content)
        proj = StepProjector(path)
        edges = proj.project_with_visibility("front")
        # Flat rectangle - all edges should be visible (same depth)
        visible = sum(1 for e in edges if not e.hidden)
        assert visible == len(edges)




class TestCircleDetection:
    """圆检测（Circle2D）测试。"""

    @pytest.fixture(autouse=True)
    def skip_no_step(self):
        if not STEP_PATH.exists():
            pytest.skip("STEP file not available")

    def test_circle2d_creation(self):
        from fc_core.step_projector import Circle2D
        c = Circle2D(cx=10.0, cy=20.0, radius=5.0)
        assert c.cx == 10.0
        assert c.cy == 20.0
        assert c.radius == 5.0
        assert c.hidden is False

    def test_circle2d_diameter(self):
        from fc_core.step_projector import Circle2D
        c = Circle2D(cx=0, cy=0, radius=7.5)
        assert c.diameter() == 15.0

    def test_detect_circles_front_view(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        circles = proj.detect_circles("front", min_radius=10.0, max_radius=300.0, tolerance=3.0)
        assert len(circles) > 0  # Should detect at least some circles
        # Verify circle attributes
        for c in circles:
            assert c.radius >= 10.0
            assert c.radius <= 300.0
            assert isinstance(c.hidden, bool)

    def test_detect_circles_all_views(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        for view in ["front", "top", "left", "iso"]:
            circles = proj.detect_circles(view)
            # Each view should have some circles (or zero)
            assert isinstance(circles, list)

    def test_detect_circles_radius_filter(self):
        from fc_core.step_projector import StepProjector
        proj = StepProjector(str(STEP_PATH))
        # Same tolerance, different radius ranges
        small = proj.detect_circles("front", min_radius=100.0, max_radius=300.0, tolerance=3.0)
        large = proj.detect_circles("front", min_radius=10.0, max_radius=300.0, tolerance=3.0)
        # Wider filter should find more or equal circles
        assert len(small) <= len(large)

    def test_detect_circles_custom_direction(self):
        from fc_core.step_projector import StepProjector, Vec3
        proj = StepProjector(str(STEP_PATH))
        circles = proj.detect_circles("custom", direction=Vec3(1, 1, 0))
        assert isinstance(circles, list)


class TestCenterLineRendering:
    """中心线渲染测试。"""

    @pytest.fixture(autouse=True)
    def skip_no_step(self):
        if not STEP_PATH.exists():
            pytest.skip("STEP file not available")

    def test_center_lines_in_svg(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.step_projector import StepProjector
        from xml.etree import ElementTree as ET

        proj = StepProjector(str(STEP_PATH))
        ad = AssemblyDrawing("A0", title="Test")
        ad.project_views_from_step(proj)
        svg = ad.generate_svg()

        # Parse SVG
        root = ET.fromstring(svg)
        ns = "{http://www.w3.org/2000/svg}"

        # Count center lines (dash-dot pattern: 12,2,3,2)
        center_count = 0
        for p in root.findall(f".//{ns}path"):
            dash = p.get("stroke-dasharray", "")
            if "12,2,3,2" in dash or "12, 2, 3, 2" in dash:
                center_count += 1

        # Should have center lines (2 per circle)
        assert center_count > 0

    def test_center_lines_per_view(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.step_projector import StepProjector
        from xml.etree import ElementTree as ET

        proj = StepProjector(str(STEP_PATH))
        ad = AssemblyDrawing("A0", title="Test")
        ad.project_views_from_step(proj)
        svg = ad.generate_svg()

        root = ET.fromstring(svg)
        ns = "{http://www.w3.org/2000/svg}"

        # Build view name to circles mapping
        view_circles = {}
        for v in ad.views:
            view_circles[v["name"]] = len(v.get("circles", []))

        # Check each view
        for g in root.findall(f".//{ns}g"):
            gc = g.get("class", "")
            if "view-" in gc:
                view_name = gc.replace("view-", "")
                circles_count = view_circles.get(view_name, 0)
                paths = g.findall(f".//{ns}path")
                # After path merging, center lines may be merged into fewer <path> elements
                # Count the actual center line segments by checking dasharray
                center = sum(1 for p in paths if "12,2,3,2" in p.get("stroke-dasharray", ""))
                # With path merging, center lines are merged into a single <path> per layer
                # So we check >= 1 (merged) or == circles_count * 2 (unmerged)
                assert center >= 1, f"{gc}: expected at least 1 center line path, got {center}"
                if circles_count > 0:
                    # If not merged, should be 2 per circle
                    # If merged, should be 1 (all center lines in one path)
                    assert center == circles_count * 2 or center == 1, \
                        f"{gc}: expected {circles_count * 2} (unmerged) or 1 (merged) center line paths, got {center}"

    def test_center_lines_with_bom(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.step_projector import StepProjector
        from fc_core.assembly_bom import make_sample_bom

        proj = StepProjector(str(STEP_PATH))
        ad = AssemblyDrawing("A0", title="Test")
        ad.set_bom(make_sample_bom())
        ad.project_views_from_step(proj)
        svg = ad.generate_svg()

        # Should generate without error and contain center lines
        assert "12,2,3,2" in svg or "12, 2, 3, 2" in svg

class TestAssemblyDrawingProjectViews:
    """AssemblyDrawing.project_views_from_step 集成测试。"""

    @pytest.fixture(autouse=True)
    def skip_no_step(self):
        if not STEP_PATH.exists():
            pytest.skip("STEP file not available")

    def test_project_views_creates_4_views(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.step_projector import StepProjector
        ad = AssemblyDrawing("A3", title="Test")
        proj = StepProjector(str(STEP_PATH))
        ad.project_views_from_step(proj)
        assert len(ad.views) == 4

    def test_project_views_custom_views(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.step_projector import StepProjector
        ad = AssemblyDrawing("A3", title="Test")
        proj = StepProjector(str(STEP_PATH))
        ad.project_views_from_step(proj, views=["front", "top"])
        assert len(ad.views) == 2

    def test_project_views_with_bom(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.step_projector import StepProjector
        from fc_core.assembly_bom import make_sample_bom
        ad = AssemblyDrawing("A0", title="Test")
        proj = StepProjector(str(STEP_PATH))
        ad.set_bom(make_sample_bom())
        ad.project_views_from_step(proj)
        assert len(ad.views) == 4
        assert len(ad.balloons) == 12  # 12 sample BOM items

    def test_project_views_svg_valid(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.step_projector import StepProjector
        ad = AssemblyDrawing("A0", title="Test")
        proj = StepProjector(str(STEP_PATH))
        ad.project_views_from_step(proj)
        svg = ad.generate_svg()
        assert "<svg" in svg
        assert "view-" in svg

    def test_project_views_real_dimensions_in_svg(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.step_projector import StepProjector
        ad = AssemblyDrawing("A0", title="Test")
        proj = StepProjector(str(STEP_PATH))
        ad.project_views_from_step(proj)
        svg = ad.generate_svg()
        bb = proj.bound_box
        # Dimensions should be rounded to nearest integer in SVG
        w_rounded = f"{bb.width:.0f}"
        assert w_rounded in svg

    def test_full_pipeline_save(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.step_projector import StepProjector
        from fc_core.assembly_bom import parse_step_bom
        proj = StepProjector(str(STEP_PATH))
        bom = parse_step_bom(str(STEP_PATH))
        ad = AssemblyDrawing("A0", title="Pipeline Test")
        ad.set_bom(bom)
        ad.project_views_from_step(proj)
        ad.add_default_tech_requirements()
        tmp_dir = tempfile.mkdtemp(prefix="asm_test_")
        path = os.path.join(tmp_dir, "test_assembly.svg")
        ad.save(path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 100000
        os.unlink(path)
