"""verify.py 单元测试。

测试 CADVerifier 的验证逻辑，包括：
- 文件不存在 / 空文件检测
- 输出解析逻辑
- 无 FreeCAD 环境的降级行为
"""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from fc_core.verify import CADVerifier, CheckResult, VerifyReport


# ─── CheckResult ───

class TestCheckResult:
    def test_passed_result(self):
        r = CheckResult(True, "OK")
        assert r.passed is True
        assert r.message == "OK"

    def test_failed_result(self):
        r = CheckResult(False, "失败", {"reason": "empty"})
        assert r.passed is False
        assert r.details["reason"] == "empty"


# ─── VerifyReport ───

class TestVerifyReport:
    def test_all_passed(self):
        report = VerifyReport(
            file_path="model.step",
            file_exists=True,
            file_size=1024,
            checks=[CheckResult(True, "实体数 15"), CheckResult(True, "体积 12345")],
        )
        assert report.passed is True
        assert "2/2" in report.summary

    def test_partial_failure(self):
        report = VerifyReport(
            file_path="model.step",
            file_exists=True,
            file_size=1024,
            checks=[CheckResult(True, "实体数 15"), CheckResult(False, "体积为 0")],
        )
        assert report.passed is False
        assert "1/2" in report.summary

    def test_to_dict(self):
        report = VerifyReport(
            file_path="model.step",
            file_exists=True,
            file_size=1024,
            checks=[CheckResult(True, "OK")],
        )
        d = report.to_dict()
        assert d["file_path"] == "model.step"
        assert d["passed"] is True
        assert len(d["checks"]) == 1


# ─── CADVerifier: 文件基础检查 ───

class TestCADVerifierFileChecks:
    def setup_method(self):
        self.verifier = CADVerifier()

    def test_file_not_exist(self):
        report = self.verifier.verify("/nonexistent/model.step")
        assert report.file_exists is False
        assert report.passed is False
        assert "文件不存在" in report.checks[0].message

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.step"
        f.write_text("")
        report = self.verifier.verify(str(f))
        assert report.file_size == 0
        assert report.passed is False
        assert "0 字节" in report.checks[0].message

    def test_unknown_format_passes(self, tmp_path):
        f = tmp_path / "model.xyz"
        f.write_text("dummy content")
        report = self.verifier.verify(str(f))
        assert report.passed is True
        assert "无特定验证规则" in report.checks[0].message

    def test_format_inference(self, tmp_path):
        f = tmp_path / "model.FCStd"
        f.write_text("dummy")
        # 无 FreeCAD 时 _run_verify_macro 返回 None
        with patch.object(self.verifier, "_run_verify_macro", return_value=None):
            report = self.verifier.verify(str(f))
        assert report.file_exists is True
        # FCStd 格式会尝试验证，None → "无法执行验证宏"
        assert any("无法执行验证宏" in c.message for c in report.checks)


# ─── CADVerifier: 输出解析 ───

class TestParseVerifyOutput:
    def setup_method(self):
        self.verifier = CADVerifier()

    def test_parse_null(self):
        result = self.verifier._parse_verify_output("VERIFY_RESULT:NULL")
        assert result == {"status": "NULL"}

    def test_parse_ok_step(self):
        output = "VERIFY_RESULT:OK solids=15 vol=12345.67 bb=(0.0,0.0,0.0)-(520.0,270.0,280.0)"
        result = self.verifier._parse_verify_output(output)
        assert result["status"] == "OK"
        assert result["solids"] == 15
        assert result["vol"] == 12345.67
        assert "520" in result["bb"]

    def test_parse_ok_fcstd(self):
        output = "VERIFY_RESULT:OK count=15 vol=50000.00 objects=Housing:(0,0,0)-(520,220,265);Shaft_1:(46,-50,101)-(74,270,129)"
        result = self.verifier._parse_verify_output(output)
        assert result["status"] == "OK"
        assert result["count"] == 15
        assert result["vol"] == 50000.0
        assert "Housing" in result["objects"]

    def test_parse_no_result_line(self):
        result = self.verifier._parse_verify_output("some other output\nno verify line")
        assert result is None

    def test_parse_empty(self):
        result = self.verifier._parse_verify_output("")
        assert result is None


# ─── CADVerifier: STEP 验证逻辑 ───

class TestVerifyStep:
    def setup_method(self):
        self.verifier = CADVerifier()

    def test_step_null_shape(self, tmp_path):
        f = tmp_path / "model.step"
        f.write_text("dummy step content")
        with patch.object(
            self.verifier, "_run_verify_macro", return_value={"status": "NULL"}
        ):
            report = self.verifier.verify(str(f), min_objects=1)
        assert report.passed is False
        assert "几何为空" in report.checks[0].message

    def test_step_too_few_solids(self, tmp_path):
        f = tmp_path / "model.step"
        f.write_text("dummy")
        with patch.object(
            self.verifier,
            "_run_verify_macro",
            return_value={"status": "OK", "solids": 1, "vol": 1000.0, "bb": "(0,0,0)-(10,10,10)"},
        ):
            report = self.verifier.verify(str(f), min_objects=5)
        assert report.passed is False
        assert any("1 < 期望最小 5" in c.message for c in report.checks)

    def test_step_correct_solids(self, tmp_path):
        f = tmp_path / "model.step"
        f.write_text("dummy")
        with patch.object(
            self.verifier,
            "_run_verify_macro",
            return_value={"status": "OK", "solids": 15, "vol": 50000.0, "bb": "(0,0,0)-(520,270,280)"},
        ):
            report = self.verifier.verify(str(f), min_objects=1, min_volume=100.0)
        assert report.passed is True
        assert any("15" in c.message for c in report.checks)

    def test_step_macro_failure(self, tmp_path):
        f = tmp_path / "model.step"
        f.write_text("dummy")
        with patch.object(self.verifier, "_run_verify_macro", return_value=None):
            report = self.verifier.verify(str(f))
        assert report.passed is False
        assert "无法执行验证宏" in report.checks[0].message


# ─── CADVerifier: FCStd 验证逻辑 ───

class TestVerifyFCStd:
    def setup_method(self):
        self.verifier = CADVerifier()

    def test_fcstd_correct(self, tmp_path):
        f = tmp_path / "model.FCStd"
        f.write_text("dummy")
        with patch.object(
            self.verifier,
            "_run_verify_macro",
            return_value={
                "status": "OK",
                "count": 15,
                "vol": 50000.0,
                "objects": "Housing:(0,0,0)-(520,220,265)",
            },
        ):
            report = self.verifier.verify(str(f), min_objects=1, min_volume=100.0)
        assert report.passed is True
        assert any("15" in c.message for c in report.checks)

    def test_fcstd_too_few_objects(self, tmp_path):
        f = tmp_path / "model.FCStd"
        f.write_text("dummy")
        with patch.object(
            self.verifier,
            "_run_verify_macro",
            return_value={"status": "OK", "count": 0, "vol": 0.0, "objects": ""},
        ):
            report = self.verifier.verify(str(f), min_objects=5)
        assert report.passed is False
        assert any("0 < 期望最小 5" in c.message for c in report.checks)


# ─── CADVerifier: 无 FreeCAD 降级 ───

class TestNoFreeCAD:
    def test_returns_none_without_freecad(self):
        verifier = CADVerifier()
        with patch.dict("sys.modules", {"FreeCAD": None}):
            # FreeCAD import 失败 → _run_verify_macro 返回 None
            result = verifier._run_verify_macro("print('test')")
            assert result is None
