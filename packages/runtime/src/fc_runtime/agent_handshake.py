"""Agent IO Schema 握手验证 — P2.2

对每个 Agent 的输入/输出 JSON 进行签名校验，确保：
1. 输出是合法的 Pydantic model（符合 Schema）
2. 关键字段齐全（如 dimensions 非空、part_type 合法）
3. 可跨进程/跨网络传递 — JSON 序列化往返保真

Karpathy 规范：写清晰的失败消息（"show, don't tell"）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from fc_runtime.agent_schemas import (
    AnnotationReviewReport,
    CADModelingOutput,
    DrawingOutput,
    ErrorLevel,
    GeometryReviewReport,
    ModelingPlan,
    PartType,
    RequirementDocument,
    Verdict,
)


# ── 校验结果 ───────────────────────────────────

@dataclass
class HandshakeResult:
    """Schema 握手结果。"""
    model_name: str
    valid: bool
    payload_hash: str
    errors: list[str]
    roundtrip_ok: bool  # JSON → dict → model → JSON 是否一致

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "valid": self.valid,
            "payload_hash": self.payload_hash,
            "errors": self.errors,
            "roundtrip_ok": self.roundtrip_ok,
        }


# ── 核心：model + payload 校验 ─────────

class AgentHandshake:
    """通用的 pydantic model IO 校验器。"""

    @staticmethod
    def _hash(obj: Any) -> str:
        serialized = json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def verify_output(cls, model_cls: type[BaseModel],
                       payload: dict[str, Any]) -> HandshakeResult:
        """校验 payload 能否被 model_cls 正确解析。"""
        errors: list[str] = []

        # 1. 能否直接从 dict 构造 model
        model: BaseModel | None = None
        try:
            model = model_cls.model_validate(payload)
        except ValidationError as ve:
            for err in ve.errors():
                loc = ".".join(str(x) for x in err.get("loc", []))
                errors.append(f"{loc}: {err.get('msg', 'unknown')}")
        except Exception as exc:
            errors.append(str(exc))

        # 2. JSON 往返保真
        roundtrip_ok = False
        if model is not None:
            try:
                j = model.model_dump_json()
                reparsed = model_cls.model_validate_json(j)
                reparsed_j = reparsed.model_dump_json()
                roundtrip_ok = j == reparsed_j
            except Exception:
                roundtrip_ok = False

        return HandshakeResult(
            model_name=model_cls.__name__,
            valid=len(errors) == 0,
            payload_hash=cls._hash(payload),
            errors=errors,
            roundtrip_ok=roundtrip_ok,
        )

    @classmethod
    def verify_output_json(cls, model_cls: type[BaseModel],
                           json_str: str) -> HandshakeResult:
        """从 JSON 字符串校验。"""
        try:
            payload = json.loads(json_str)
        except json.JSONDecodeError as e:
            return HandshakeResult(
                model_name=model_cls.__name__,
                valid=False,
                payload_hash="",
                errors=[f"JSON decode failed: {e}"],
                roundtrip_ok=False,
            )
        return cls.verify_output(model_cls, payload)

    # ── 便利方法：特定 Agent 的输出 ─────────

    @classmethod
    def verify_requirement(cls, doc: RequirementDocument) -> HandshakeResult:
        return cls.verify_output(RequirementDocument, doc.model_dump(mode="json"))

    @classmethod
    def verify_modeling_plan(cls, plan: ModelingPlan) -> HandshakeResult:
        return cls.verify_output(ModelingPlan, plan.model_dump(mode="json"))

    @classmethod
    def verify_cad_output(cls, out: CADModelingOutput) -> HandshakeResult:
        return cls.verify_output(CADModelingOutput, out.model_dump(mode="json"))

    @classmethod
    def verify_drawing(cls, d: DrawingOutput) -> HandshakeResult:
        return cls.verify_output(DrawingOutput, d.model_dump(mode="json"))

    @classmethod
    def verify_geometry_review(cls, r: GeometryReviewReport) -> HandshakeResult:
        return cls.verify_output(GeometryReviewReport, r.model_dump(mode="json"))

    @classmethod
    def verify_annotation(cls, r: AnnotationReviewReport) -> HandshakeResult:
        return cls.verify_output(AnnotationReviewReport, r.model_dump(mode="json"))


# ── 端到端握手：从一个完整 pipeline 结果生成校验报告 ─

def pipeline_handshake_report(result) -> dict[str, Any]:
    """对 PipelineResult 每个组件做握手校验，返回结构化报告。"""
    reports: dict[str, Any] = {}
    ok = True

    if getattr(result, "requirement", None) is not None:
        r = AgentHandshake.verify_requirement(result.requirement)
        reports["requirement"] = r.as_dict()
        ok = ok and r.valid
    if getattr(result, "plan", None) is not None:
        r = AgentHandshake.verify_modeling_plan(result.plan)
        reports["modeling_plan"] = r.as_dict()
        ok = ok and r.valid
    if getattr(result, "model_output", None) is not None:
        r = AgentHandshake.verify_cad_output(result.model_output)
        reports["cad_output"] = r.as_dict()
        ok = ok and r.valid
    if getattr(result, "geometry_review", None) is not None:
        r = AgentHandshake.verify_geometry_review(result.geometry_review)
        reports["geometry_review"] = r.as_dict()
        ok = ok and r.valid
    if getattr(result, "drawing_output", None) is not None:
        r = AgentHandshake.verify_drawing(result.drawing_output)
        reports["drawing"] = r.as_dict()
        ok = ok and r.valid
    if getattr(result, "annotation_review", None) is not None:
        r = AgentHandshake.verify_annotation(result.annotation_review)
        reports["annotation"] = r.as_dict()
        ok = ok and r.valid

    return {
        "all_valid": ok,
        "schema_count": len(reports),
        "reports": reports,
    }
