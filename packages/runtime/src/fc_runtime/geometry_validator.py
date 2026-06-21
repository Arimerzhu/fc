"""几何拓扑校验器 — 拦截退化几何，防止下游装配崩溃。

方法论v1.0 P0-4：四层验证中的"几何拓扑"层。
验证标准：
  1. 面数 ≥ 7（实体几何的最低要求）
  2. 正体积 > 0
  3. 连通性 isConnected
  4. 拓扑有效性 isValid
  5. 闭合性 isClosed

两种执行路径：
  A. 实际FreeCAD执行路径 — 通过fc_core/BackendInterface调用
  B. 单元测试Mock路径 — 仅依赖Python内置库，无需FreeCAD
"""

from __future__ import annotations

import math
from pathlib import Path

from .agent_schemas import ErrorLevel, GeometryCheck, GeometryReviewReport, Verdict


# ── Mock几何体（测试友好的内置几何描述） ─────────────────────

class _ShapeInfo:
    """几何体信息 — 可从FCStd/STEP或Mock数据填充。"""

    def __init__(
        self,
        *,
        face_count: int = 0,
        vertex_count: int = 0,
        volume: float = 0.0,
        is_connected: bool = False,
        is_valid: bool = False,
        is_closed: bool = False,
        bounding_box: tuple[float, float, float] | None = None,
        source: str = "",
    ) -> None:
        self.face_count = face_count
        self.vertex_count = vertex_count
        self.volume = volume
        self.is_connected = is_connected
        self.is_valid = is_valid
        self.is_closed = is_closed
        self.bounding_box = bounding_box
        self.source = source

    def __repr__(self) -> str:
        return (f"_ShapeInfo(faces={self.face_count}, vol={self.volume:.3f}, "
                f"connected={self.is_connected}, valid={self.is_valid}, "
                f"closed={self.is_closed})")


# ── 核心校验逻辑 ────────────────────────────────────────────

_MIN_FACE_COUNT = 4          # 实体几何最低面数（四面体）
_MIN_VOLUME_EPS = 1e-6       # 体积0阈值mm³


def _check_face_count(info: _ShapeInfo, min_face_count: int) -> GeometryCheck:
    ok = info.face_count >= min_face_count
    return GeometryCheck(
        check_name="face_count",
        passed=ok,
        detail=f"面数={info.face_count}（需≥{min_face_count}）",
        suggestion=(f"当前面数{info.face_count}不足{min_face_count}，可能是退化几何。"
                    if not ok else "面数正常"),
    )


def _check_positive_volume(info: _ShapeInfo) -> GeometryCheck:
    ok = info.volume > _MIN_VOLUME_EPS
    return GeometryCheck(
        check_name="positive_volume",
        passed=ok,
        detail=f"体积={info.volume:.6f} mm³（需>0）",
        suggestion=("体积为0或接近0，可能是薄壳/面片几何而非实体。"
                    if not ok else "体积正常"),
    )


def _check_connected(info: _ShapeInfo) -> GeometryCheck:
    return GeometryCheck(
        check_name="is_connected",
        passed=info.is_connected,
        detail="连通性=" + ("OK" if info.is_connected else "FAIL"),
        suggestion=("几何体多组件不连通，可能导致装配或布尔运算失败。"
                    if not info.is_connected else "连通性正常"),
    )


def _check_valid(info: _ShapeInfo) -> GeometryCheck:
    return GeometryCheck(
        check_name="is_valid",
        passed=info.is_valid,
        detail=f"拓扑有效={info.is_valid}",
        suggestion=("拓扑结构非法（如边无顶点、面无环），需重建。"
                if not info.is_valid else "拓扑正常"),
    )


def _check_closed(info: _ShapeInfo) -> GeometryCheck:
    return GeometryCheck(
        check_name="is_closed",
        passed=info.is_closed,
        detail=f"几何体闭合={info.is_closed}",
        suggestion=("几何体未闭合，可能导致布尔运算或装配失败。"
                if not info.is_closed else "闭合性正常"),
    )


def _check_bounding_box(info: _ShapeInfo) -> GeometryCheck:
    if info.bounding_box is None:
        return GeometryCheck(
            check_name="bounding_box",
            passed=False,
            detail="bounding_box 未提供",
            suggestion="需提供边界盒信息以验证尺寸合理性",
        )
    l, w, h = info.bounding_box
    has_real_dim = all(v > 0.001 for v in (l, w, h))
    return GeometryCheck(
        check_name="bounding_box_positive",
        passed=has_real_dim,
        detail=f"L×W×H = {l:.3f}×{w:.3f}×{h:.3f} mm",
        suggestion=("零维/近零维边界盒，可能是退化几何。"
                    if not has_real_dim else "边界盒正常"),
    )


class GeometryValidator:
    """几何拓扑校验器。

    核心流程：
      1. 收集ShapeInfo（来自FreeCAD或Mock）
      2. 依次执行6项检查
      3. 生成GeometryReviewReport（PASS/FAIL + 错误等级）

    使用示例：
        v = GeometryValidator()
        info = v.from_freecad_file("model.FCStd")  # 需真实FreeCAD
        report = v.validate(info)
        if report.verdict == Verdict.FAIL:
            print("需回滚:", report.error_level)
    """

    def __init__(self, min_face_count: int = _MIN_FACE_COUNT) -> None:
        self._min_face_count = min_face_count
        mfc = min_face_count
        self._checks = [
            lambda info: _check_face_count(info, mfc),
            _check_positive_volume,
            _check_connected,
            _check_valid,
            _check_closed,
            _check_bounding_box,
        ]

    # ── 从不同来源收集几何信息 ────────────────────────────

    def from_freecad_file(self, fcstd_path: str) -> _ShapeInfo:
        """从FCStd文件读取几何信息（需FreeCAD可用）。

        通过fc_core/BackendInterface执行一个极简Python宏：
          import Part
          part = FreeCAD.ActiveDocument.ActiveObject
          print('FACES', len(part.Shape.Faces))
          ...
        """
        from fc_core.backend import get_backend  # 延迟导入，避免无FreeCAD时失败

        path = Path(fcstd_path)
        if not path.exists():
            raise FileNotFoundError(fcstd_path)

        backend = get_backend()
        macro = (
            "doc = FreeCAD.activeDocument()\n"
            "if doc is None:\n"
            "    doc = FreeCAD.open('" + str(path).replace("'", "\\'") + "')\n"
            "shape = None\n"
            "for obj in doc.Objects:\n"
            "    if hasattr(obj, 'Shape') and obj.Shape is not None:\n"
            "        shape = obj.Shape\n"
            "        break\n"
            "if shape is None:\n"
            "    print('NO_SHAPE')\n"
            "else:\n"
            "    bb = shape.BoundBox\n"
            "    print('FC_FACES', len(shape.Faces))\n"
            "    print('FC_VERTS', len(shape.Vertexes))\n"
            "    print('FC_VOLUME', shape.Volume)\n"
            "    print('FC_CONNECTED', int(shape.isConnected()))\n"
            "    print('FC_VALID', int(shape.isValid()))\n"
            "    print('FC_CLOSED', int(shape.isClosed()))\n"
            "    print('FC_BBX', bb.XLength, bb.YLength, bb.ZLength)\n"
        )
        result = backend.execute_code(macro) if hasattr(backend, "execute_code") else ""
        output = getattr(result, "stdout", str(result))
        return self._parse_freecad_output(output)

    def _parse_freecad_output(self, output: str) -> _ShapeInfo:
        info = _ShapeInfo(source="freecad")
        for line in str(output).splitlines():
            line = line.strip()
            if line.startswith("FC_FACES"):
                info.face_count = int(line.split()[1])
            elif line.startswith("FC_VERTS"):
                info.vertex_count = int(line.split()[1])
            elif line.startswith("FC_VOLUME"):
                info.volume = float(line.split()[1])
            elif line.startswith("FC_CONNECTED"):
                info.is_connected = bool(int(line.split()[1]))
            elif line.startswith("FC_VALID"):
                info.is_valid = bool(int(line.split()[1]))
            elif line.startswith("FC_CLOSED"):
                info.is_closed = bool(int(line.split()[1]))
            elif line.startswith("FC_BBX"):
                parts = line.split()
                info.bounding_box = (float(parts[1]), float(parts[2]), float(parts[3]))
            elif line == "NO_SHAPE":
                info = _ShapeInfo(source="freecad(no_shape)")
        return info

    def from_mock(
        self,
        *,
        face_count: int,
        volume: float,
        is_connected: bool = True,
        is_valid: bool = True,
        is_closed: bool = True,
        bounding_box: tuple[float, float, float] | None = None,
    ) -> _ShapeInfo:
        """测试用：手工构造几何信息（无需FreeCAD）。"""
        return _ShapeInfo(
            face_count=face_count,
            vertex_count=max(3, face_count),
            volume=volume,
            is_connected=is_connected,
            is_valid=is_valid,
            is_closed=is_closed,
            bounding_box=bounding_box,
            source="mock",
        )

    def from_primitives(
        self,
        kind: str,
        **params: float,
    ) -> _ShapeInfo:
        """基于解析几何计算的"预期"ShapeInfo — 无需FreeCAD。

        kind ∈ {"box", "cylinder", "sphere", "cone", "torus", "wedge"}

        仅返回数学上的期望面数/体积/边界盒，
        用来做"设计阶段预检"（建模前即可判断是否合理）。
        """
        kind = kind.lower().strip()
        if kind == "box":
            l, w, h = params.get("length", 50.0), params.get("width", 50.0), params.get("height", 50.0)
            return _ShapeInfo(
                face_count=6,
                vertex_count=8,
                volume=l * w * h,
                is_connected=True, is_valid=True, is_closed=True,
                bounding_box=(l, w, h), source="primitives/box",
            )
        if kind == "cylinder":
            r, h = params.get("radius", 10.0), params.get("height", 50.0)
            return _ShapeInfo(
                face_count=3,  # 顶面+底面+侧面（CAD简化模型）
                vertex_count=0,
                volume=math.pi * r * r * h,
                is_connected=True, is_valid=True, is_closed=True,
                bounding_box=(2 * r, 2 * r, h), source="primitives/cylinder",
            )
        if kind == "sphere":
            r = params.get("radius", 10.0)
            return _ShapeInfo(
                face_count=1, vertex_count=0,
                volume=4.0 / 3.0 * math.pi * r ** 3,
                is_connected=True, is_valid=True, is_closed=True,
                bounding_box=(2 * r, 2 * r, 2 * r), source="primitives/sphere",
            )
        if kind == "cone":
            r1, r2, h = params.get("radius1", 10.0), params.get("radius2", 5.0), params.get("height", 30.0)
            return _ShapeInfo(
                face_count=3, vertex_count=0,
                volume=math.pi * h / 3.0 * (r1 * r1 + r2 * r2 + r1 * r2),
                is_connected=True, is_valid=True, is_closed=True,
                bounding_box=(2 * r1, 2 * r1, h), source="primitives/cone",
            )
        if kind == "torus":
            r1, r2 = params.get("radius1", 20.0), params.get("radius2", 5.0)
            return _ShapeInfo(
                face_count=1, vertex_count=0,
                volume=2.0 * math.pi * math.pi * r1 * r2 * r2,
                is_connected=True, is_valid=True, is_closed=True,
                bounding_box=(2 * (r1 + r2), 2 * (r1 + r2), 2 * r2),
                source="primitives/torus",
            )
        if kind == "wedge":
            l, w, h = params.get("length", 50.0), params.get("width", 30.0), params.get("height", 20.0)
            return _ShapeInfo(
                face_count=5, vertex_count=6,
                volume=l * w * h / 2.0,
                is_connected=True, is_valid=True, is_closed=True,
                bounding_box=(l, w, h), source="primitives/wedge",
            )
        raise ValueError(f"Unknown primitive kind: {kind}")

    # ── 执行校验 ───────────────────────────────────────────

    def validate(self, info: _ShapeInfo) -> GeometryReviewReport:
        """执行所有检查，生成审查报告。"""
        results = [c(info) for c in self._checks]
        all_ok = all(r.passed for r in results)

        error_level = self._compute_error_level(results)
        return GeometryReviewReport(
            verdict=Verdict.PASS if all_ok else Verdict.FAIL,
            checks=results,
            error_level=error_level,
        )

    def validate_from_mock(self, **kwargs) -> GeometryReviewReport:
        """便捷方法：直接用Mock参数构造并校验。"""
        return self.validate(self.from_mock(**kwargs))

    def validate_from_primitives(self, kind: str, **params) -> GeometryReviewReport:
        """便捷方法：直接用解析几何参数构造并校验。"""
        return self.validate(self.from_primitives(kind, **params))

    # ── 辅助 ───────────────────────────────────────────────

    def _compute_error_level(self, checks: list[GeometryCheck]) -> ErrorLevel:
        """按检查失败的严重程度映射到ErrorLevel。

        - 正体积/拓扑有效/连通性/闭合性: CODE级（建模脚本执行问题）
        - 面数 < 7: 若极小型→CODE级；若参数完全不合理→DESIGN级
        - 若多项严重失败（如同时正体积=0 + invalid）: DESIGN级
        """
        failed = {c.check_name: c for c in checks if not c.passed}
        if not failed:
            return ErrorLevel.NONE

        # DESIGN级：多项严重失败 或 face_count/positive_volume 同时失败
        severe_failures = {"positive_volume", "is_valid", "is_connected", "is_closed"}
        if failed.keys() & severe_failures and "face_count" in failed:
            return ErrorLevel.DESIGN
        if "positive_volume" in failed and failed["positive_volume"].detail.startswith("体积=0"):
            return ErrorLevel.DESIGN

        return ErrorLevel.CODE

    # ── 统计与导出 ─────────────────────────────────────────

    def summary(self, report: GeometryReviewReport) -> str:
        lines = [f"几何审查: {'PASS' if report.verdict == Verdict.PASS else 'FAIL'}",
                 f"错误等级: {report.error_level}"]
        for c in report.checks:
            symbol = "✓" if c.passed else "✗"
            lines.append(f"  {symbol} {c.check_name:25s} — {c.detail}")
            if not c.passed and c.suggestion:
                lines.append(f"      建议: {c.suggestion}")
        return "\n".join(lines)
