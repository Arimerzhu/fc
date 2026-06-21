"""Agent IO JSON Schema — 6类Agent标准化输入输出。

符合方法论v1.0第三章：语义与几何分离，装配关系前置，可验证的中间表示。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────── 枚举类型 ───────────────────────────────

class PartType(str, Enum):
    """标准零件类型。"""
    BOX = "box"
    CYLINDER = "cylinder"
    SPHERE = "sphere"
    CONE = "cone"
    TORUS = "torus"
    PLATE = "plate"
    SHAFT = "shaft"
    GEAR = "gear"
    HOUSING = "housing"
    BRACKET = "bracket"
    FLANGE = "flange"
    CUSTOM = "custom"


class ToleranceGrade(str, Enum):
    """GB/T 1800.1公差等级。"""
    IT5 = "IT5"
    IT6 = "IT6"
    IT7 = "IT7"
    IT8 = "IT8"
    IT9 = "IT9"
    IT10 = "IT10"


class Standard(str, Enum):
    """适用标准体系。"""
    GB = "GB"
    ISO = "ISO"
    ANSI = "ANSI"


class ConstraintType(str, Enum):
    """装配约束类型。"""
    COINCIDENT = "coincident"
    CONCENTRIC = "concentric"
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"
    TANGENT = "tangent"


class FeatureOperation(str, Enum):
    """建模特征操作。"""
    SKETCH = "sketch"
    PAD = "pad"
    POCKET = "pocket"
    FILLET = "fillet"
    CHAMFER = "chamfer"
    REVOLUTION = "revolution"
    GROOVE = "groove"
    BOOLEAN_UNION = "boolean_union"
    BOOLEAN_CUT = "boolean_cut"
    HOLE = "hole"
    PATTERN_LINEAR = "pattern_linear"


class ErrorLevel(str, Enum):
    """三级错误分级。"""
    DESIGN = "DESIGN"
    CODE = "CODE"
    DRAWING = "DRAWING"
    NONE = "NONE"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


# ─────────────────────────────── 连接点 (Connector) ──────────────────────

class Connector(BaseModel):
    """装配连接点前置定义。

    在设计阶段定义，避免装配阶段依赖LLM的3D空间推理。
    """
    name: str
    position: str = Field(pattern=r"^-?\d+(\.\d+)?,-?\d+(\.\d+)?,-?\d+(\.\d+)?$",
                          description="x,y,z 坐标，单位mm")
    constraint_type: ConstraintType
    mating_part: str | None = Field(default=None, description="配对零件名")


# ─────────────────────────────── Agent 1: 需求分析 ────────────────────────

class RequirementDocument(BaseModel):
    """需求文档 — 需求分析Agent的唯一输出。"""
    part_type: PartType
    dimensions: dict[str, float] = Field(description="关键尺寸，单位mm")
    material: str = Field(default="Q235", description="材料牌号")
    tolerance_grade: ToleranceGrade = Field(default=ToleranceGrade.IT7)
    standard: Standard = Field(default=Standard.GB)
    surface_roughness: float = Field(default=3.2, ge=0.1, le=100.0)
    quantity: int = Field(default=1, ge=1)
    description: str = Field(default="", description="自然语言补充说明")
    connectors: list[Connector] = Field(default_factory=list,
                                        description="装配连接点前置定义")
    notes: list[str] = Field(default_factory=list)

    @field_validator("dimensions")
    @classmethod
    def _positive_dims(cls, v: dict[str, float]) -> dict[str, float]:
        for k, val in v.items():
            if val <= 0:
                raise ValueError(f"Dimension '{k}' must be positive, got {val}")
        return v


# ─────────────────────────────── Agent 2: 设计规划 ────────────────────────

class FeatureStep(BaseModel):
    """单个特征操作步骤。"""
    step: int = Field(ge=1)
    operation: FeatureOperation
    parameters: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[int] = Field(default_factory=list, description="依赖的步骤编号")


class ModelingPlan(BaseModel):
    """建模计划 — 设计规划Agent输出。"""
    features: list[FeatureStep]
    connectors: list[Connector] = Field(default_factory=list)
    parametric_constraints: dict[str, str] = Field(
        default_factory=dict,
        description="参数化约束表达式，如 {'diameter': 'length * 0.5'}")

    @field_validator("features")
    @classmethod
    def _ordered_steps(cls, v: list[FeatureStep]) -> list[FeatureStep]:
        if not v:
            raise ValueError("At least one feature step is required")
        seen = set()
        for f in v:
            if f.step in seen:
                raise ValueError(f"Duplicate step number: {f.step}")
            seen.add(f.step)
        steps_sorted = sorted(v, key=lambda x: x.step)
        expected = list(range(1, len(v) + 1))
        if [f.step for f in steps_sorted] != expected:
            raise ValueError(f"Feature steps must be 1..N, got {[f.step for f in steps_sorted]}")
        return steps_sorted


# ─────────────────────────────── Agent 3: CAD建模 ────────────────────────

class CADModelingOutput(BaseModel):
    """CAD建模Agent输出。"""
    script_path: str = Field(description="生成的FreeCAD Python脚本路径")
    fcstd_path: str = Field(description="生成的FCStd模型文件路径")
    step_path: str | None = None
    script_hash: str = Field(default="")
    execution_time_sec: float = Field(default=0.0, ge=0)
    # ── P3 新增：几何信息，供 GeometryReviewAgent 直接审查 ──
    face_count: int = Field(default=0, ge=0)
    volume: float = Field(default=0.0, ge=0.0)
    is_connected: bool | None = None
    is_valid: bool | None = None
    is_closed: bool | None = None
    bounding_box: tuple[float, float, float] = Field(
        default=(0.0, 0.0, 0.0), description="(X_length, Y_length, Z_length) mm"
    )


# ─────────────────────────────── Agent 4: 出图 ────────────────────────

class DrawingOutput(BaseModel):
    """出图Agent输出。"""
    svg_path: str
    dxf_path: str | None = None
    pdf_path: str | None = None
    views: list[str] = Field(default_factory=list, description="生成的视图列表")
    template: str = Field(default="ISO_A3_Landscape.svg")
    projection: str = Field(default="First Angle", pattern=r"^(First|Third) Angle$")


# ─────────────────────────────── Agent 5: 几何审查 ────────────────────────

class GeometryCheck(BaseModel):
    check_name: str
    passed: bool
    detail: str = ""
    suggestion: str = ""


class GeometryReviewReport(BaseModel):
    """几何审查报告。"""
    verdict: Verdict
    checks: list[GeometryCheck]
    error_level: ErrorLevel = ErrorLevel.NONE


# ─────────────────────────────── Agent 6: 标注合规 ────────────────────────

class AnnotationCheck(BaseModel):
    check_name: str
    passed: bool
    detail: str = ""
    suggestion: str = ""


class AnnotationReviewReport(BaseModel):
    """标注合规报告。"""
    verdict: Verdict
    checks: list[AnnotationCheck]
    error_level: ErrorLevel = ErrorLevel.NONE


# ─────────────────────────────── 全局编排状态 ────────────────────────

class AgentState(BaseModel):
    """编排器全局状态。遵循语义与几何分离原则。"""
    requirement: RequirementDocument | None = None
    modeling_plan: ModelingPlan | None = None
    cad_output: CADModelingOutput | None = None
    drawing: DrawingOutput | None = None
    geometry_review: GeometryReviewReport | None = None
    annotation_review: AnnotationReviewReport | None = None
    error_level: ErrorLevel = ErrorLevel.NONE
    retry_count: int = Field(default=0, ge=0)
    last_error_message: str = ""

    model_config = {"extra": "allow"}
