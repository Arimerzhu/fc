"""fc_runtime — FreeCAD Agent Runtime Package

Provides the `fc agent` command for autonomous CAD design from natural language.
Includes planning, tool execution, self-correction, and BOM generation.
"""

from __future__ import annotations

__version__ = "01.0"

from fc_runtime.planner import Plan, Planner, Task
from fc_runtime.executor import Executor, TaskResult
from fc_runtime.corrector import Corrector
from fc_runtime.bom import BOM, BOMGenerator
from fc_runtime.agent_schemas import (
    AgentState,
    AnnotationCheck,
    AnnotationReviewReport,
    CADModelingOutput,
    Connector,
    ConstraintType,
    DrawingOutput,
    ErrorLevel,
    FeatureOperation,
    FeatureStep,
    GeometryCheck,
    GeometryReviewReport,
    ModelingPlan,
    PartType,
    RequirementDocument,
    Standard,
    ToleranceGrade,
    Verdict,
)
from fc_runtime.requirement_agent import RequirementAgent
from fc_runtime.error_classifier import ErrorClassifier
from fc_runtime.geometry_validator import GeometryValidator
from fc_runtime.design_agent import DesignAgent
from fc_runtime.modeling_agent import CADModelingAgent
from fc_runtime.drafting_agent import DraftingAgent
from fc_runtime.visual_verifier import (
    VisualVerifier, ViewAngle, ActionType,
    VisualVerificationPlan, VisualVerificationResult,
    generate_visual_plan, analyze_visual,
)
from fc_runtime.orchestrator import Orchestrator, PipelineResult, PipelineStage, run_pipeline

__all__ = [
    "Plan",
    "Planner",
    "Task",
    "Executor",
    "TaskResult",
    "Corrector",
    "BOM",
    "BOMGenerator",
    "AgentState",
    "AnnotationCheck",
    "AnnotationReviewReport",
    "CADModelingOutput",
    "Connector",
    "ConstraintType",
    "DrawingOutput",
    "ErrorLevel",
    "FeatureOperation",
    "FeatureStep",
    "GeometryCheck",
    "GeometryReviewReport",
    "ModelingPlan",
    "PartType",
    "RequirementDocument",
    "RequirementAgent",
    "ErrorClassifier",
    "GeometryValidator",
    "DesignAgent",
    "CADModelingAgent",
    "DraftingAgent",
    "VisualVerifier",
    "ViewAngle",
    "ActionType",
    "VisualVerificationPlan",
    "VisualVerificationResult",
    "generate_visual_plan",
    "analyze_visual",
    "Orchestrator",
    "PipelineResult",
    "PipelineStage",
    "run_pipeline",
    "Standard",
    "ToleranceGrade",
    "Verdict",
]
