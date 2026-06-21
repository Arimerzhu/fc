"""CAD 输出验证模块。

保存/导出后自动检查文件几何正确性，
避免"文件存在但内容为空"的静默失败。

典型用法（HeadlessBackend 内部）::

    verifier = CADVerifier()
    result = verifier.verify_step("model.step", min_solids=1)
    if not result.passed:
        return ToolResponse.error(...)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """单项验证结果。"""

    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerifyReport:
    """完整验证报告。"""

    file_path: str
    file_exists: bool
    file_size: int
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def summary(self) -> str:
        ok = sum(1 for c in self.checks if c.passed)
        total = len(self.checks)
        return f"{ok}/{total} 项通过"

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_exists": self.file_exists,
            "file_size": self.file_size,
            "passed": self.passed,
            "summary": self.summary,
            "checks": [
                {"passed": c.passed, "message": c.message, "details": c.details}
                for c in self.checks
            ],
        }


class CADVerifier:
    """CAD 文件验证器。

    通过 FreeCADCmd 宏脚本重新打开导出的文件，
    检查几何数据的完整性。
    """

    def verify(
        self,
        file_path: str,
        fmt: str | None = None,
        min_objects: int = 1,
        min_volume: float = 0.0,
        max_objects: int = 10000,
    ) -> VerifyReport:
        """验证 CAD 文件。

        Args:
            file_path: 文件路径
            fmt: 格式（step/fcstd/stl），None 则自动推断
            min_objects: 最少对象/实体数
            min_volume: 最小总体积 (mm³)
            max_objects: 最多对象/实体数

        Returns:
            VerifyReport 包含所有检查项的结果
        """
        ext = fmt or os.path.splitext(file_path)[1].lstrip(".").lower()
        report = VerifyReport(
            file_path=file_path,
            file_exists=os.path.isfile(file_path),
            file_size=os.path.getsize(file_path) if os.path.isfile(file_path) else 0,
        )

        if not report.file_exists:
            report.checks.append(CheckResult(False, "文件不存在"))
            return report

        if report.file_size == 0:
            report.checks.append(CheckResult(False, "文件大小为 0 字节"))
            return report

        if ext in ("step", "stp"):
            self._verify_step(report, min_objects, min_volume, max_objects)
        elif ext == "fcstd":
            self._verify_fcstd(report, min_objects, min_volume, max_objects)
        elif ext == "stl":
            self._verify_stl(report, min_objects, min_volume)
        elif ext in ("brep", "brp"):
            self._verify_brep(report, min_objects, min_volume)
        else:
            report.checks.append(
                CheckResult(True, f"格式 {ext} 无特定验证规则，文件存在即通过")
            )

        return report

    def _verify_step(
        self, report: VerifyReport, min_solids: int, min_volume: float, max_solids: int
    ) -> None:
        """验证 STEP 文件：用 Part.read 重新加载检查。"""
        macro = f"""
import Part
shape = Part.read(r"{report.file_path}")
if shape.isNull():
    print("VERIFY_RESULT:NULL")
else:
    solids = len(shape.Solids)
    bb = shape.BoundBox
    vol = shape.Volume
    print(f"VERIFY_RESULT:OK solids={{solids}} vol={{vol:.2f}} bb=({{bb.XMin:.1f}},{{bb.YMin:.1f}},{{bb.ZMin:.1f}})-({{bb.XMax:.1f}},{{bb.YMax:.1f}},{{bb.ZMax:.1f}})")
"""
        result = self._run_verify_macro(macro)
        if result is None:
            report.checks.append(CheckResult(False, "无法执行验证宏"))
            return

        if result.get("status") == "NULL":
            report.checks.append(CheckResult(False, "STEP 文件几何为空 (null shape)"))
            return

        solids = result.get("solids", 0)
        vol = result.get("vol", 0.0)
        bb_str = result.get("bb", "")

        # 检查实体数
        if solids < min_solids:
            report.checks.append(
                CheckResult(
                    False,
                    f"实体数 {solids} < 期望最小 {min_solids}",
                    {"solids": solids, "min_expected": min_solids},
                )
            )
        elif solids > max_solids:
            report.checks.append(
                CheckResult(
                    False,
                    f"实体数 {solids} > 期望最大 {max_solids}",
                    {"solids": solids, "max_expected": max_solids},
                )
            )
        else:
            report.checks.append(
                CheckResult(True, f"实体数 {solids} 在预期范围内", {"solids": solids})
            )

        # 检查体积
        if vol < min_volume:
            report.checks.append(
                CheckResult(
                    False,
                    f"体积 {vol:.2f} mm³ < 期望最小 {min_volume}",
                    {"volume": vol, "min_expected": min_volume},
                )
            )
        else:
            report.checks.append(
                CheckResult(True, f"体积 {vol:.2f} mm³", {"volume": vol})
            )

        # 检查边界框
        if bb_str:
            report.checks.append(
                CheckResult(True, f"边界框 {bb_str}", {"boundbox": bb_str})
            )

    def _verify_fcstd(
        self, report: VerifyReport, min_objects: int, min_volume: float, max_objects: int
    ) -> None:
        """验证 FCStd 文件：重新打开检查对象数和体积。"""
        macro = f"""
import FreeCAD
doc = FreeCAD.open(r"{report.file_path}")
objs = [o for o in doc.Objects if hasattr(o, "Shape") and o.Shape and not o.Shape.isNull()]
count = len(objs)
total_vol = sum(o.Shape.Volume for o in objs if o.Shape.Volume > 0)
bbs = []
for o in objs:
    bb = o.Shape.BoundBox
    if not bb.isValid():
        bbs.append(f"{{o.Name}}:({{bb.XMin:.0f}},{{bb.YMin:.0f}},{{bb.ZMin:.0f}})-({{bb.XMax:.0f}},{{bb.YMax:.0f}},{{bb.ZMax:.0f}})")
FreeCAD.closeDocument(doc.Name)
print(f"VERIFY_RESULT:OK count={{count}} vol={{total_vol:.2f}} objects={{';'.join(bbs[:5])}}")
"""
        result = self._run_verify_macro(macro)
        if result is None:
            report.checks.append(CheckResult(False, "无法执行验证宏"))
            return

        count = result.get("count", 0)
        vol = result.get("vol", 0.0)

        if count < min_objects:
            report.checks.append(
                CheckResult(
                    False,
                    f"对象数 {count} < 期望最小 {min_objects}",
                    {"count": count, "min_expected": min_objects},
                )
            )
        elif count > max_objects:
            report.checks.append(
                CheckResult(
                    False,
                    f"对象数 {count} > 期望最大 {max_objects}",
                    {"count": count, "max_expected": max_objects},
                )
            )
        else:
            report.checks.append(
                CheckResult(True, f"对象数 {count} 在预期范围内", {"count": count})
            )

        if vol < min_volume and count > 0:
            report.checks.append(
                CheckResult(
                    False,
                    f"总体积 {vol:.2f} mm³ < 期望最小 {min_volume}",
                    {"volume": vol, "min_expected": min_volume},
                )
            )
        else:
            report.checks.append(
                CheckResult(True, f"总体积 {vol:.2f} mm³", {"volume": vol})
            )

        objects_str = result.get("objects", "")
        if objects_str:
            report.checks.append(
                CheckResult(True, f"零件边界框: {objects_str}", {"objects": objects_str})
            )

    def _verify_stl(
        self, report: VerifyReport, min_objects: int, min_volume: float
    ) -> None:
        """验证 STL 文件：用 Mesh 模块加载检查。"""
        macro = f"""
import Mesh
mesh = Mesh.Mesh(r"{report.file_path}")
if mesh.countPoints() == 0:
    print("VERIFY_RESULT:NULL")
else:
    pts = mesh.countPoints()
    faces = mesh.countFacets()
    bb = mesh.BoundBox
    print(f"VERIFY_RESULT:OK points={{pts}} faces={{faces}} bb=({{bb.XMin:.1f}},{{bb.YMin:.1f}},{{bb.ZMin:.1f}})-({{bb.XMax:.1f}},{{bb.YMax:.1f}},{{bb.ZMax:.1f}})")
"""
        result = self._run_verify_macro(macro)
        if result is None:
            report.checks.append(CheckResult(False, "无法执行验证宏"))
            return

        if result.get("status") == "NULL":
            report.checks.append(CheckResult(False, "STL 文件网格为空"))
            return

        points = result.get("points", 0)
        faces = result.get("faces", 0)
        if points == 0 or faces == 0:
            report.checks.append(
                CheckResult(False, f"STL 网格为空: {points} 点, {faces} 面")
            )
        else:
            report.checks.append(
                CheckResult(
                    True,
                    f"STL 网格: {points} 点, {faces} 面",
                    {"points": points, "faces": faces},
                )
            )

    def _verify_brep(
        self, report: VerifyReport, min_objects: int, min_volume: float
    ) -> None:
        """验证 BREP 文件。"""
        macro = f"""
import Part
shape = Part.read(r"{report.file_path}")
if shape.isNull():
    print("VERIFY_RESULT:NULL")
else:
    solids = len(shape.Solids)
    vol = shape.Volume
    print(f"VERIFY_RESULT:OK solids={{solids}} vol={{vol:.2f}}")
"""
        result = self._run_verify_macro(macro)
        if result is None:
            report.checks.append(CheckResult(False, "无法执行验证宏"))
            return

        if result.get("status") == "NULL":
            report.checks.append(CheckResult(False, "BREP 文件几何为空"))
            return

        solids = result.get("solids", 0)
        vol = result.get("vol", 0.0)
        if solids < min_objects:
            report.checks.append(
                CheckResult(False, f"实体数 {solids} < 期望 {min_objects}")
            )
        else:
            report.checks.append(
                CheckResult(True, f"实体数 {solids}, 体积 {vol:.2f} mm³")
            )

    def _run_verify_macro(self, macro_code: str) -> dict[str, Any] | None:
        """执行验证宏并解析结果。

        在无 FreeCAD 环境时返回 None（跳过验证）。
        """
        try:
            import FreeCAD  # noqa: F401
        except ImportError:
            logger.debug("FreeCAD 不可用，跳过验证")
            return None

        # 用 exec 执行宏代码，捕获 stdout
        import io
        import contextlib

        stdout_buf = io.StringIO()
        local_ns: dict[str, Any] = {}
        try:
            with contextlib.redirect_stdout(stdout_buf):
                exec(macro_code, local_ns)
        except Exception as e:
            logger.warning("验证宏执行失败: %s", e)
            return None

        output = stdout_buf.getvalue().strip()
        return self._parse_verify_output(output)

    @staticmethod
    def _parse_verify_output(output: str) -> dict[str, Any] | None:
        """解析 VERIFY_RESULT 输出行。"""
        for line in output.splitlines():
            line = line.strip()
            if not line.startswith("VERIFY_RESULT:"):
                continue
            payload = line[len("VERIFY_RESULT:"):]
            if payload == "NULL":
                return {"status": "NULL"}

            # 格式: OK solids=15 vol=12345.67 bb=(0,0,0)-(520,270,280)
            result: dict[str, Any] = {"status": "OK"}
            for token in payload.split():
                if "=" in token:
                    key, val = token.split("=", 1)
                    if key in ("solids", "count", "vol", "points", "faces"):
                        try:
                            result[key] = float(val) if key in ("vol",) else int(val)
                        except ValueError:
                            result[key] = val
                    elif key == "bb":
                        result[key] = val
                    elif key == "objects":
                        result[key] = val
            return result
        return None
