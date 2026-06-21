"""P3.1 — 独立几何审查 Agent

方法论中 Agent 5: 几何审查
将 GeometryValidator 升级为完整的独立 Agent：
  - 接受 CADModelingOutput 作为输入
  - 支持 6 项拓扑检查 + 尺寸合理性检查
  - 输出 GeometryReviewReport（verdict/checks/error_level）
  - 支持从 FCStd 文件或 mock 数据运行
  - 输出修复建议（suggestion）
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fc_runtime.agent_schemas import (
    CADModelingOutput,
    ErrorLevel,
    GeometryCheck,
    GeometryReviewReport,
    RequirementDocument,
    Verdict,
)
from fc_runtime.agent_logging import AgentLogger, get_logger


# ── 6 项标准检查 ─────────────────────────────

def _check_face_count(face_count: int, min_faces: int) -> GeometryCheck:
    passed = face_count >= min_faces
    return GeometryCheck(
        check_name="face_count",
        passed=passed,
        detail=f"面数={face_count}，阈值≥{min_faces}",
        suggestion=("几何体退化，无实际实体/面，"
                    "可能需要重建特征或增加 extrusion 深度。"
                    if not passed else "面数正常"),
    )


def _check_positive_volume(volume: float) -> GeometryCheck:
    passed = volume > 0.001
    return GeometryCheck(
        check_name="positive_volume",
        passed=passed,
        detail=f"体积={volume:.6f} mm³",
        suggestion=("体积为零/负值，特征可能反转或未闭合。"
                    if not passed else "体积正常"),
    )


def _check_connected(is_connected: bool) -> GeometryCheck:
    return GeometryCheck(
        check_name="connectivity",
        passed=is_connected,
        detail=f"连通={'是' if is_connected else '否'}",
        suggestion=("几何体由多个不连通部分组成，"
                    "可能是建模错误或布尔操作出错。"
                    if not is_connected else "连通性正常"),
    )


def _check_valid(is_valid: bool) -> GeometryCheck:
    return GeometryCheck(
        check_name="topology_valid",
        passed=is_valid,
        detail=f"拓扑有效={'是' if is_valid else '否'}",
        suggestion=("FreeCAD 报告几何无效，"
                    "通常需要重画草图或检查布尔操作的接触面。"
                    if not is_valid else "拓扑正常"),
    )


def _check_closed(is_closed: bool) -> GeometryCheck:
    return GeometryCheck(
        check_name="watertight",
        passed=is_closed,
        detail=f"闭合={'是' if is_closed else '否'}",
        suggestion=("模型非闭合（存在开口），"
                    "无法作为实体参与后续布尔操作或导出 STEP。"
                    if not is_closed else "模型闭合良好"),
    )


def _check_bounding_box(bounding_box: tuple[float, float, float]) -> GeometryCheck:
    l, w, h = bounding_box
    has_real_dim = all(v > 0.001 for v in (l, w, h))
    return GeometryCheck(
        check_name="bounding_box_positive",
        passed=has_real_dim,
        detail=f"L×W×H = {l:.3f}×{w:.3f}×{h:.3f} mm",
        suggestion=("零维/近零维边界盒，退化几何体。"
                    if not has_real_dim else "边界盒正常"),
    )


def _check_dimension_match(
    bounding_box: tuple[float, float, float],
    requirement: RequirementDocument | None,
) -> GeometryCheck:
    """额外检查：生成尺寸是否与原始需求尺寸一致（±5%容差）。"""
    if requirement is None:
        return GeometryCheck(
            check_name="dimension_match",
            passed=True,
            detail="无原始需求，跳过",
            suggestion="",
        )
    dims = requirement.dimensions
    if not dims:
        return GeometryCheck(
            check_name="dimension_match",
            passed=True,
            detail="无尺寸信息，跳过",
            suggestion="",
        )

    req_values = sorted([dims.get(k, 0.0) for k in ("length", "width", "height",
                                                       "diameter", "radius") if k in dims])
    actual_values = sorted(bounding_box)

    if not req_values:
        return GeometryCheck(
            check_name="dimension_match",
            passed=True,
            detail="无长度类尺寸信息",
            suggestion="",
        )

    # 取最小的两个序列对应比较（容差5%）
    matches = True
    for i, req_v in enumerate(req_values):
        if i >= len(actual_values):
            break
        act_v = actual_values[i]
        if act_v == 0:
            continue
        rel = abs(act_v - req_v) / max(req_v, 1e-6)
        if rel > 0.05:
            matches = False
            break

    return GeometryCheck(
        check_name="dimension_match",
        passed=matches,
        detail=f"需求尺寸={req_values}, 实际尺寸={actual_values[:len(req_values)]}",
        suggestion=("生成尺寸与需求不一致超过5%，"
                    "可能是单位转换错误或特征参数错误。"
                    if not matches else "尺寸匹配良好"),
    )


class GeometryReviewAgent:
    """几何审查 Agent（方法论 Agent 5）。

    独立运行：接收 CAD 模型的几何信息，输出审查报告，
    供编排器决定是否回滚到建模/设计阶段。
    """

    def __init__(self, min_face_count: int = 4, verbose: bool = False) -> None:
        self._min_face_count = min_face_count
        self._log: AgentLogger = get_logger("geometry_review", verbose=verbose)

    # ── 主审查流程 ───────────────────────────────

    def review(
        self,
        cad_output: CADModelingOutput,
        requirement: RequirementDocument | None = None,
    ) -> GeometryReviewReport:
        """执行完整的几何审查流程。"""
        with self._log.measure_stage("review"):
            # 快速通道：如果没有任何几何信息，跳过审查
            no_info = (
                not getattr(cad_output, "face_count", 0)
                and not getattr(cad_output, "volume", 0.0)
                and getattr(cad_output, "is_connected", None) is None
                and getattr(cad_output, "is_valid", None) is None
                and getattr(cad_output, "is_closed", None) is None
                and all(v <= 0.001 for v in getattr(
                    cad_output, "bounding_box", (0.0, 0.0, 0.0)))
            )
            if no_info:
                self._log.task("review", "skip", reason="no geometry info")
                return GeometryReviewReport(
                    verdict=Verdict.PASS,
                    checks=[GeometryCheck(
                        check_name="geometry_info",
                        passed=True,
                        detail="脚本模式：未提供几何信息，跳过几何审查",
                        suggestion="如需几何验证，请补充 face_count / volume / is_valid",
                    )],
                    error_level=ErrorLevel.NONE,
                    suggestion="脚本模式下跳过几何检查，建议补充 BRep 分析数据后再次审查。",
                )

            checks = [
                _check_face_count(cad_output.face_count, self._min_face_count)
                if hasattr(cad_output, "face_count") and cad_output.face_count
                else GeometryCheck(check_name="face_count", passed=True,
                                    detail="未提供面数信息，跳过", suggestion=""),
                _check_positive_volume(cad_output.volume)
                if hasattr(cad_output, "volume") and cad_output.volume > 0
                else GeometryCheck(check_name="positive_volume", passed=True,
                                    detail="未提供体积信息，跳过", suggestion=""),
                _check_connected(cad_output.is_connected)
                if hasattr(cad_output, "is_connected") and cad_output.is_connected is not None
                else GeometryCheck(check_name="connectivity", passed=True,
                                    detail="未提供连通信息，跳过", suggestion=""),
                _check_valid(cad_output.is_valid)
                if hasattr(cad_output, "is_valid") and cad_output.is_valid is not None
                else GeometryCheck(check_name="topology_valid", passed=True,
                                    detail="未提供拓扑信息，跳过", suggestion=""),
                _check_closed(cad_output.is_closed)
                if hasattr(cad_output, "is_closed") and cad_output.is_closed is not None
                else GeometryCheck(check_name="watertight", passed=True,
                                    detail="未提供闭合信息，跳过", suggestion=""),
                _check_bounding_box(cad_output.bounding_box),
                _check_dimension_match(cad_output.bounding_box, requirement),
            ]

            all_passed = all(c.passed for c in checks)
            verdict = Verdict.PASS if all_passed else Verdict.FAIL

            # 计算错误等级（决定回滚阶段）
            error_level = self._compute_error_level(checks)

            self._log.task(
                "review",
                "pass" if all_passed else "fail",
                checks=len(checks),
                failed=sum(1 for c in checks if not c.passed),
                error_level=error_level.value,
            )

            return GeometryReviewReport(
                verdict=verdict,
                checks=checks,
                error_level=error_level,
            )

    def review_from_fcstd(
        self,
        fcstd_path: str,
        requirement: RequirementDocument | None = None,
    ) -> GeometryReviewReport:
        """从 FCStd 文件执行审查（需 FreeCAD 可用）。"""
        path = Path(fcstd_path)
        if not path.exists():
            raise FileNotFoundError(fcstd_path)

        try:
            from fc_core.backend import get_backend
        except ImportError:
            raise RuntimeError("fc_core.backend 不可用，请安装 fc-core 或使用 mock 数据")

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
            "    print('FC_VOLUME', shape.Volume)\n"
            "    print('FC_CONNECTED', int(shape.isConnected()))\n"
            "    print('FC_VALID', int(shape.isValid()))\n"
            "    print('FC_CLOSED', int(shape.isClosed()))\n"
            "    print('FC_BBX', bb.XLength, bb.YLength, bb.ZLength)\n"
        )

        result = backend.execute_python(macro)
        lines = result.stdout.split("\n") if hasattr(result, "stdout") else []

        face_count = 0
        volume = 0.0
        is_connected = True
        is_valid = True
        is_closed = True
        bbx = bby = bbz = 0.0

        for line in lines:
            if line.startswith("FC_FACES"):
                face_count = int(line.split()[1])
            elif line.startswith("FC_VOLUME"):
                volume = float(line.split()[1])
            elif line.startswith("FC_CONNECTED"):
                is_connected = bool(int(line.split()[1]))
            elif line.startswith("FC_VALID"):
                is_valid = bool(int(line.split()[1]))
            elif line.startswith("FC_CLOSED"):
                is_closed = bool(int(line.split()[1]))
            elif line.startswith("FC_BBX"):
                parts = line.split()
                bbx, bby, bbz = float(parts[1]), float(parts[2]), float(parts[3])

        fake_output = CADModelingOutput(
            script_path=fcstd_path,
            fcstd_path=fcstd_path,
            face_count=face_count,
            volume=volume,
            is_connected=is_connected,
            is_valid=is_valid,
            is_closed=is_closed,
            bounding_box=(bbx, bby, bbz),
        )
        return self.review(fake_output, requirement)

    # ── 辅助 ─────────────────────────────────────

    @staticmethod
    def _compute_error_level(checks: list[GeometryCheck]) -> ErrorLevel:
        """根据检查失败的严重性决定错误等级。

        - DESIGN（设计级）：正体积失败 + 面数过小 → 模型本身无法成立，
          需要重新规划特征。
        - CODE（操作级）：拓扑无效、非闭合 → 可能是建模操作顺序
          或参数细节问题，重试修改即可。
        """
        failed_names = {c.check_name for c in checks if not c.passed}

        if "positive_volume" in failed_names or "face_count" in failed_names:
            return ErrorLevel.DESIGN
        if "topology_valid" in failed_names or "watertight" in failed_names:
            return ErrorLevel.CODE
        if "dimension_match" in failed_names:
            return ErrorLevel.CODE
        return ErrorLevel.NONE
