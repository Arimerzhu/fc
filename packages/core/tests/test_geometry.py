"""Tests for fc_core geometry modules.

Covers:
- PrimitivesMixin: add_box, add_cylinder, add_sphere, add_cone, add_torus, add_wedge, add_helix
- GeometryOpsMixin: boolean_*, fillet, chamfer, mirror, scale, transform_placement
"""

from unittest.mock import MagicMock, patch

import pytest

from fc_core.geometry import PrimitivesMixin
from fc_core.geometry.operations import GeometryOpsMixin
from fc_core.types import ToolResponse, Vec3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _PrimitiveHost(PrimitivesMixin):
    """Concrete class that wires PrimitivesMixin to a fake backend."""

    def __init__(self, backend):
        self._backend = backend


class _GeometryOpsHost(GeometryOpsMixin):
    """Concrete class that wires GeometryOpsMixin to a fake backend."""

    def __init__(self, backend):
        self._backend = backend


def _make_ok(operation: str, data: dict | None = None) -> ToolResponse:
    return ToolResponse.ok(operation, data or {})


def _make_backend(mock_responses: dict | None = None) -> MagicMock:
    """Create a MagicMock backend that returns ok responses by default."""
    backend = MagicMock()
    backend.object_create.return_value = _make_ok("object_create", {
        "name": "Obj", "label": "Obj", "type_id": "Part::Box"
    })
    backend.execute_code.return_value = _make_ok("execute_code")
    return backend


# ---------------------------------------------------------------------------
# PrimitivesMixin tests
# ---------------------------------------------------------------------------

class TestPrimitivesMixin:
    """Tests for all primitive creation methods."""

    @pytest.fixture
    def backend(self):
        return _make_backend()

    @pytest.fixture
    def host(self, backend):
        return _PrimitiveHost(backend)

    # -- add_box ------------------------------------------------------------

    def test_add_box_default_name(self, host, backend):
        r = host.add_box()
        assert r.status == "ok"
        backend.object_create.assert_called_once_with(
            "Part::Box", "Box",
            {"Length": 10.0, "Width": 10.0, "Height": 10.0}
        )

    def test_add_box_custom_name(self, host, backend):
        r = host.add_box(name="MyBox")
        backend.object_create.assert_called_once_with(
            "Part::Box", "MyBox",
            {"Length": 10.0, "Width": 10.0, "Height": 10.0}
        )

    def test_add_box_with_dimensions(self, host, backend):
        r = host.add_box(length=20, width=15, height=10)
        call_args = backend.object_create.call_args
        assert call_args[0][2] == {"Length": 20, "Width": 15, "Height": 10}

    def test_add_box_with_position(self, host, backend):
        r = host.add_box(position=Vec3(1, 2, 3))
        call_args = backend.object_create.call_args
        props = call_args[0][2]
        assert props["Placement"] == {"Base": {"x": 1.0, "y": 2.0, "z": 3.0}}

    def test_add_box_enriches_data(self, host):
        r = host.add_box(length=10, width=5, height=2)
        assert r.data["dimensions"] == {"length": 10, "width": 5, "height": 2}
        assert r.data["volume"] == 100.0

    def test_add_box_message(self, host):
        r = host.add_box(name="B", length=3, width=4, height=5)
        assert "B" in r.message
        assert "3" in r.message and "4" in r.message and "5" in r.message

    # -- add_cylinder --------------------------------------------------------

    def test_add_cylinder_default(self, host, backend):
        r = host.add_cylinder()
        backend.object_create.assert_called_once_with(
            "Part::Cylinder", "Cylinder",
            {"Radius": 5.0, "Height": 10.0}
        )

    def test_add_cylinder_custom_params(self, host, backend):
        r = host.add_cylinder(name="Cyl", radius=3, height=7)
        call_args = backend.object_create.call_args
        assert call_args[0] == ("Part::Cylinder", "Cyl", {"Radius": 3, "Height": 7})

    def test_add_cylinder_with_position(self, host, backend):
        r = host.add_cylinder(position=Vec3(10, 0, 0))
        props = backend.object_create.call_args[0][2]
        assert props["Placement"] == {"Base": {"x": 10.0, "y": 0.0, "z": 0.0}}

    def test_add_cylinder_enriches_data(self, host):
        import math
        r = host.add_cylinder(radius=2, height=5)
        assert r.data["dimensions"] == {"radius": 2, "height": 5}
        assert abs(r.data["volume"] - math.pi * 4 * 5) < 1e-10

    def test_add_cylinder_message(self, host):
        r = host.add_cylinder(name="Pipe", radius=1, height=3)
        assert "Pipe" in r.message
        assert "r=1" in r.message

    # -- add_sphere ----------------------------------------------------------

    def test_add_sphere_default(self, host, backend):
        r = host.add_sphere()
        backend.object_create.assert_called_once_with(
            "Part::Sphere", "Sphere", {"Radius": 5.0}
        )

    def test_add_sphere_custom(self, host, backend):
        r = host.add_sphere(name="Ball", radius=7)
        backend.object_create.assert_called_once_with(
            "Part::Sphere", "Ball", {"Radius": 7}
        )

    def test_add_sphere_with_position(self, host):
        r = host.add_sphere(position=Vec3(5, 5, 5))
        props = host._backend.object_create.call_args[0][2]
        assert props["Placement"] == {"Base": {"x": 5.0, "y": 5.0, "z": 5.0}}

    def test_add_sphere_enriches_data(self, host):
        import math
        r = host.add_sphere(radius=3)
        assert r.data["dimensions"] == {"radius": 3}
        assert abs(r.data["volume"] - (4 / 3) * math.pi * 27) < 1e-10

    def test_add_sphere_message(self, host):
        r = host.add_sphere(name="Globe", radius=10)
        assert "Globe" in r.message
        assert "r=10" in r.message

    # -- add_cone ------------------------------------------------------------

    def test_add_cone_default(self, host, backend):
        r = host.add_cone()
        backend.object_create.assert_called_once_with(
            "Part::Cone", "Cone",
            {"Radius1": 5.0, "Radius2": 0.0, "Height": 10.0}
        )

    def test_add_cone_truncated(self, host, backend):
        r = host.add_cone(radius1=10, radius2=5, height=20)
        props = backend.object_create.call_args[0][2]
        assert props == {"Radius1": 10, "Radius2": 5, "Height": 20}

    def test_add_cone_with_position(self, host):
        r = host.add_cone(position=Vec3(1, 1, 1))
        props = host._backend.object_create.call_args[0][2]
        assert "Placement" in props

    def test_add_cone_enriches_data(self, host):
        r = host.add_cone(radius1=5, radius2=2, height=10)
        assert r.data["dimensions"] == {"radius1": 5, "radius2": 2, "height": 10}

    def test_add_cone_message(self, host):
        r = host.add_cone(name="Cone", radius1=5, radius2=0, height=10)
        assert "Cone" in r.message

    # -- add_torus -----------------------------------------------------------

    def test_add_torus_default(self, host, backend):
        r = host.add_torus()
        backend.object_create.assert_called_once_with(
            "Part::Torus", "Torus",
            {"Radius1": 10.0, "Radius2": 2.0}
        )

    def test_add_torus_custom(self, host, backend):
        r = host.add_torus(name="Ring", radius1=20, radius2=3)
        props = backend.object_create.call_args[0][2]
        assert props == {"Radius1": 20, "Radius2": 3}

    def test_add_torus_with_position(self, host):
        r = host.add_torus(position=Vec3(0, 0, 5))
        props = host._backend.object_create.call_args[0][2]
        assert props["Placement"]["Base"]["z"] == 5.0

    def test_add_torus_enriches_data(self, host):
        r = host.add_torus(radius1=10, radius2=2)
        assert r.data["dimensions"] == {"radius1": 10, "radius2": 2}

    def test_add_torus_message(self, host):
        r = host.add_torus(name="Donut", radius1=10, radius2=2)
        assert "Donut" in r.message
        assert "R=10" in r.message

    # -- add_wedge -----------------------------------------------------------

    def test_add_wedge_default(self, host, backend):
        r = host.add_wedge()
        backend.object_create.assert_called_once_with(
            "Part::Wedge", "Wedge",
            {
                "XMin": 0, "YMin": 0, "ZMin": 0,
                "XMax": 10, "YMax": 10, "ZMax": 10,
                "X2Min": 0, "Z2Min": 0, "X2Max": 10, "Z2Max": 10,
            }
        )

    def test_add_wedge_custom(self, host, backend):
        r = host.add_wedge(name="W", xmin=1, ymin=2, zmin=3, xmax=4, ymax=5, zmax=6,
                           x2min=7, z2min=8, x2max=9, z2max=10)
        props = backend.object_create.call_args[0][2]
        assert props["XMin"] == 1
        assert props["ZMax"] == 6
        assert props["X2Max"] == 9

    def test_add_wedge_with_position(self, host):
        r = host.add_wedge(position=Vec3(1, 2, 3))
        props = host._backend.object_create.call_args[0][2]
        assert "Placement" in props

    def test_add_wedge_message(self, host):
        r = host.add_wedge(name="W1")
        assert "W1" in r.message

    # -- add_helix -----------------------------------------------------------

    def test_add_helix_default(self, host, backend):
        r = host.add_helix()
        backend.object_create.assert_called_once_with(
            "Part::Helix", "Helix",
            {"Pitch": 5, "Height": 20, "Radius": 5, "Angle": 0, "LocalCoord": 0}
        )

    def test_add_helix_custom(self, host, backend):
        r = host.add_helix(name="Spring", pitch=2, height=30, radius=4, angle=45, style=1)
        props = backend.object_create.call_args[0][2]
        assert props == {
            "Pitch": 2, "Height": 30, "Radius": 4,
            "Angle": 45, "LocalCoord": 1,
        }

    def test_add_helix_with_position(self, host):
        r = host.add_helix(position=Vec3(5, 5, 5))
        props = host._backend.object_create.call_args[0][2]
        assert props["Placement"]["Base"]["x"] == 5.0

    def test_add_helix_message(self, host):
        r = host.add_helix(name="Coil", pitch=3, height=15)
        assert "Coil" in r.message
        assert "pitch=3" in r.message

    # -- error propagation ---------------------------------------------------

    def test_add_box_error_propagates(self, host, backend):
        backend.object_create.return_value = ToolResponse.error(
            "object_create", "CREATE_FAIL", "backend error"
        )
        r = host.add_box()
        assert r.status == "error"

    def test_add_sphere_error_propagates(self, host, backend):
        backend.object_create.return_value = ToolResponse.error(
            "object_create", "FAIL", "fail"
        )
        r = host.add_sphere()
        assert r.status == "error"


# ---------------------------------------------------------------------------
# GeometryOpsMixin tests
# ---------------------------------------------------------------------------

class TestGeometryOpsMixin:
    """Tests for geometry operations (boolean, transform, etc.)."""

    @pytest.fixture
    def backend(self):
        return _make_backend()

    @pytest.fixture
    def host(self, backend):
        return _GeometryOpsHost(backend)

    # -- boolean_union -------------------------------------------------------

    def test_boolean_union(self, host, backend):
        r = host.boolean_union("Box001", "Box002")
        assert r.status == "ok"
        backend.execute_code.assert_called_once()
        code = backend.execute_code.call_args[0][0]
        assert "Part::MultiFuse" in code
        assert "Box001" in code
        assert "Box002" in code

    def test_boolean_union_custom_name(self, host, backend):
        r = host.boolean_union("A", "B", result_name="CustomFusion")
        code = backend.execute_code.call_args[0][0]
        assert "CustomFusion" in code
        assert "Fusion" not in code or "CustomFusion" in code

    def test_boolean_union_message(self, host):
        r = host.boolean_union("A", "B")
        assert "A" in r.message
        assert "B" in r.message

    # -- boolean_cut ---------------------------------------------------------

    def test_boolean_cut(self, host, backend):
        r = host.boolean_cut("Base", "Tool")
        assert r.status == "ok"
        code = backend.execute_code.call_args[0][0]
        assert "Part::Cut" in code
        assert 'result.Base = base' in code
        assert 'result.Tool = tool' in code

    def test_boolean_cut_custom_name(self, host, backend):
        r = host.boolean_cut("Base", "Tool", result_name="MyCut")
        code = backend.execute_code.call_args[0][0]
        assert "MyCut" in code

    def test_boolean_cut_message(self, host):
        r = host.boolean_cut("X", "Y")
        assert "X" in r.message
        assert "Y" in r.message

    # -- boolean_common ------------------------------------------------------

    def test_boolean_common(self, host, backend):
        r = host.boolean_common("A", "B")
        assert r.status == "ok"
        code = backend.execute_code.call_args[0][0]
        assert "Part::MultiCommon" in code
        assert "A" in code and "B" in code

    def test_boolean_common_custom_name(self, host, backend):
        r = host.boolean_common("A", "B", result_name="Intersect")
        code = backend.execute_code.call_args[0][0]
        assert "Intersect" in code

    def test_boolean_common_message(self, host):
        r = host.boolean_common("A", "B")
        assert "A" in r.message
        assert "B" in r.message

    # -- fillet_edges --------------------------------------------------------

    def test_fillet_edges(self, host, backend):
        r = host.fillet_edges("Box001", radius=2.0)
        assert r.status == "ok"
        code = backend.execute_code.call_args[0][0]
        assert "makeFillet" in code
        assert "2.0" in code
        assert "Box001" in code

    def test_fillet_edges_with_edge_list(self, host, backend):
        r = host.fillet_edges("Box001", radius=1.5, edges=[0, 1, 2])
        code = backend.execute_code.call_args[0][0]
        assert "shape.Edges[i]" in code

    def test_fillet_edges_custom_name(self, host, backend):
        r = host.fillet_edges("Obj", result_name="MyFillet")
        code = backend.execute_code.call_args[0][0]
        assert "MyFillet" in code

    def test_fillet_edges_message(self, host):
        r = host.fillet_edges("Obj", radius=3.0)
        assert "radius=3.0" in r.message

    # -- chamfer_edges -------------------------------------------------------

    def test_chamfer_edges(self, host, backend):
        r = host.chamfer_edges("Box001", size=1.0)
        assert r.status == "ok"
        code = backend.execute_code.call_args[0][0]
        assert "makeChamfer" in code
        assert "1.0" in code

    def test_chamfer_edges_with_edges(self, host, backend):
        r = host.chamfer_edges("Obj", size=0.5, edges=[0])
        code = backend.execute_code.call_args[0][0]
        assert "shape.Edges[i]" in code

    def test_chamfer_edges_message(self, host):
        r = host.chamfer_edges("Obj", size=2.0)
        assert "size=2.0" in r.message

    # -- mirror_object -------------------------------------------------------

    def test_mirror_object_xy(self, host, backend):
        r = host.mirror_object("Box001")
        assert r.status == "ok"
        code = backend.execute_code.call_args[0][0]
        assert "mirror" in code

    def test_mirror_object_xz(self, host, backend):
        r = host.mirror_object("Obj", plane="XZ")
        code = backend.execute_code.call_args[0][0]
        # XZ plane normal is (0, 1, 0)
        assert "0, 1, 0" in code

    def test_mirror_object_yz(self, host, backend):
        r = host.mirror_object("Obj", plane="YZ")
        code = backend.execute_code.call_args[0][0]
        assert "1, 0, 0" in code

    def test_mirror_object_custom_name(self, host, backend):
        r = host.mirror_object("Obj", result_name="MirroredObj")
        code = backend.execute_code.call_args[0][0]
        assert "MirroredObj" in code

    def test_mirror_object_message(self, host):
        r = host.mirror_object("Obj", plane="XY")
        assert "XY" in r.message

    # -- scale_object --------------------------------------------------------

    def test_scale_object_uniform(self, host, backend):
        r = host.scale_object("Box001", factor=2.0)
        assert r.status == "ok"
        code = backend.execute_code.call_args[0][0]
        assert "scale" in code
        assert "2.0" in code

    def test_scale_object_non_uniform(self, host, backend):
        r = host.scale_object("Obj", factor=[2.0, 3.0, 4.0])
        code = backend.execute_code.call_args[0][0]
        assert "2.0, 3.0, 4.0" in code

    def test_scale_object_custom_name(self, host, backend):
        r = host.scale_object("Obj", factor=3.0, result_name="BigObj")
        code = backend.execute_code.call_args[0][0]
        assert "BigObj" in code

    def test_scale_object_message(self, host):
        r = host.scale_object("Obj", factor=5.0)
        assert "5.0" in r.message

    # -- transform_placement -------------------------------------------------

    def test_transform_position(self, host, backend):
        r = host.transform_placement("Obj", position=(10, 20, 30))
        assert r.status == "ok"
        code = backend.execute_code.call_args[0][0]
        assert "Placement.Base" in code
        assert "10" in code and "20" in code and "30" in code

    def test_transform_rotation(self, host, backend):
        r = host.transform_placement("Obj", rotation=(45, 90, 0))
        assert r.status == "ok"
        code = backend.execute_code.call_args[0][0]
        assert "Placement.Rotation" in code
        assert "45" in code

    def test_transform_both(self, host, backend):
        r = host.transform_placement("Obj", position=(1, 2, 3), rotation=(4, 5, 6))
        code = backend.execute_code.call_args[0][0]
        assert "Placement.Base" in code
        assert "Placement.Rotation" in code

    def test_transform_message(self, host):
        r = host.transform_placement("MyObj", position=(1, 2, 3))
        assert "MyObj" in r.message

    # -- error propagation ---------------------------------------------------

    def test_boolean_union_error(self, host, backend):
        backend.execute_code.return_value = ToolResponse.error(
            "execute_code", "FAIL", "err"
        )
        r = host.boolean_union("A", "B")
        assert r.status == "error"

    def test_fillet_error(self, host, backend):
        backend.execute_code.return_value = ToolResponse.error(
            "execute_code", "FAIL", "no shape"
        )
        r = host.fillet_edges("Obj")
        assert r.status == "error"

    def test_mirror_error(self, host, backend):
        backend.execute_code.return_value = ToolResponse.error(
            "execute_code", "FAIL", "err"
        )
        r = host.mirror_object("Obj")
        assert r.status == "error"
