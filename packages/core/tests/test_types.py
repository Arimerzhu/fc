"""Tests for fc_core types."""

import pytest
from fc_core.types import (
    Vec3, Placement, Color, BoundingBox,
    ToolResponse, Units, ExportFormat, ImportFormat,
)


class TestVec3:
    def test_default(self):
        v = Vec3()
        assert v.x == 0.0
        assert v.y == 0.0
        assert v.z == 0.0

    def test_from_list(self):
        v = Vec3.from_list([1.0, 2.0, 3.0])
        assert v.x == 1.0
        assert v.y == 2.0
        assert v.z == 3.0

    def test_parse(self):
        v = Vec3.parse("10,20,30")
        assert v.x == 10.0
        assert v.y == 20.0
        assert v.z == 30.0

    def test_parse_invalid(self):
        with pytest.raises(ValueError, match="Expected x,y,z"):
            Vec3.parse("10,20")

    def test_to_list(self):
        v = Vec3(1.0, 2.0, 3.0)
        assert v.to_list() == [1.0, 2.0, 3.0]


class TestToolResponse:
    def test_ok(self):
        r = ToolResponse.ok("test", {"key": "value"}, "Success")
        assert r.status == "ok"
        assert r.operation == "test"
        assert r.data == {"key": "value"}
        assert r.message == "Success"

    def test_error(self):
        r = ToolResponse.error("test", "ERR_CODE", "Something failed", "Try again")
        assert r.status == "error"
        assert r.error_code == "ERR_CODE"
        assert r.message == "Something failed"
        assert r.suggestion == "Try again"

    def test_to_dict_ok(self):
        r = ToolResponse.ok("test", {"x": 1})
        d = r.to_dict()
        assert d["status"] == "ok"
        assert "error" not in d

    def test_to_dict_error(self):
        r = ToolResponse.error("test", "ERR", "msg", "fix it")
        d = r.to_dict()
        assert d["status"] == "error"
        assert d["error"]["code"] == "ERR"
        assert d["error"]["suggestion"] == "fix it"


class TestBoundingBox:
    def test_dimensions(self):
        bb = BoundingBox(x_min=0, x_max=10, y_min=0, y_max=20, z_min=0, z_max=30)
        dims = bb.dimensions
        assert dims.x == 10
        assert dims.y == 20
        assert dims.z == 30


class TestEnums:
    def test_units(self):
        assert Units.MM == "mm"
        assert Units.M == "m"

    def test_export_format(self):
        assert ExportFormat.STEP == "step"
        assert ExportFormat.STL == "stl"


class TestColor:
    def test_default(self):
        c = Color()
        assert c.to_list() == [0.5, 0.5, 0.5, 1.0]


class TestPlacement:
    def test_default(self):
        p = Placement()
        assert p.position.x == 0.0
        assert p.rotation_angle == 0.0
