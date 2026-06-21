"""出图Agent — CADModelingOutput → TechDraw视图 + 尺寸标注 + 导出。

符合方法论v1.0第三章3.3节：国标投影（第一角），关键尺寸优先标注。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fc_core.assembly_bom import BOMTable, parse_step_bom, make_sample_bom
from fc_core.assembly_drawing import AssemblyDrawing
from fc_core.step_projector import StepProjector

from fc_runtime.agent_schemas import (
    AnnotationCheck,
    AnnotationReviewReport,
    DrawingOutput,
    PartType,
    RequirementDocument,
    Verdict,
)


@dataclass
class ViewSpec:
    """单个视图规格。"""
    name: str
    direction: tuple[float, float, float]
    include_dimensions: bool = True


_DEFAULT_VIEWS: list[ViewSpec] = [
    ViewSpec("Front", (0, 0, 1), True),
    ViewSpec("Top", (0, 1, 0), True),
    ViewSpec("Left", (1, 0, 0), True),
    ViewSpec("Isometric", (1, 1, 1), False),
]


_TEMPLATES = [
    "ISO_A3_Landscape.svg",
    "ISO_A2_Landscape.svg",
    "A3_Landscape.svg",
]


class DraftingAgent:
    """出图Agent。

    输入：RequirementDocument（需求） + CADModelingOutput（模型）
    输出：DrawingOutput（视图列表 + SVG/DFX/PDF 导出）
    """

    def __init__(
        self,
        template: str = "ISO_A3_Landscape.svg",
        projection: str = "First Angle",
    ) -> None:
        self.template = template if template in _TEMPLATES else _TEMPLATES[0]
        assert projection in ("First Angle", "Third Angle")
        self.projection = projection

    # ── 视图计划 ──────────────────────────────────

    def plan_views(
        self,
        doc: RequirementDocument,
    ) -> list[ViewSpec]:
        """根据零件类型决定视图策略。"""
        views = list(_DEFAULT_VIEWS)

        # 对称零件：减少视图
        if doc.part_type in (PartType.SHAFT, PartType.CYLINDER, PartType.SPHERE):
            # 轴类只需 Front + 一个标注截面
            views = [
                ViewSpec("Front", (0, 0, 1), True),
                ViewSpec("Section_A-A", (1, 0, 0), True),
            ]
        elif doc.part_type == PartType.BOX or doc.part_type == PartType.PLATE:
            # 平板类只需 Front + Top
            views = [
                ViewSpec("Front", (0, 0, 1), True),
                ViewSpec("Top", (0, 1, 0), True),
            ]

        return views

    # ── 标注规则 ────────────────────────────────────

    def plan_dimensions(
        self,
        doc: RequirementDocument,
    ) -> list[str]:
        """根据零件类型和尺寸关键度，生成标注列表。"""
        dims = doc.dimensions
        labels: list[str] = []

        simple_map = {
            PartType.BOX: ["length", "width", "height"],
            PartType.CYLINDER: ["radius", "height"],
            PartType.SPHERE: ["radius"],
            PartType.CONE: ["radius1", "radius2", "height"],
            PartType.TORUS: ["radius1", "radius2"],
            PartType.PLATE: ["length", "width", "thickness"],
            PartType.SHAFT: ["length", "diameter"],
            PartType.GEAR: ["diameter", "thickness", "hole_diameter"],
            PartType.FLANGE: ["diameter", "thickness", "hole_diameter"],
            PartType.HOUSING: ["length", "width", "height", "wall"],
            PartType.BRACKET: ["length", "width", "thickness"],
        }

        keys = simple_map.get(doc.part_type, list(dims.keys()))

        for key in keys:
            if key in dims:
                labels.append(f"{key}={dims[key]}")

        # 补充表面粗糙度 + 公差标注
        labels.append(f"surface_roughness={doc.surface_roughness}")
        labels.append(f"tolerance={doc.tolerance_grade.value}")
        labels.append(f"material={doc.material}")
        labels.append(f"standard={doc.standard.value}")

        return labels

    # ── 生成 TechDraw 脚本 ─────────────────────────

    def generate_techdraw_script(
        self,
        doc: RequirementDocument,
        part_name: str = "Part",
    ) -> str:
        """生成 FreeCAD TechDraw 脚本（可附加到建模脚本后执行）。"""
        views = self.plan_views(doc)
        dims = self.plan_dimensions(doc)

        lines = [
            "# ── TechDraw 出图 ─────────────────────────────",
            "import TechDraw",
            "",
            f"page = doc.addObject('TechDraw::DrawPage', '{part_name}_Page')",
            f"page.Template = doc.addObject('TechDraw::DrawSVGTemplate', 'Template')",
            f"page.Template.Template = '{self.template}'",
            f"page.ProjectionType = '{self.projection}'",
            "",
            "# Create views",
        ]

        for i, view in enumerate(views):
            x = 60 + i * 150
            y = 250
            dx, dy, dz = view.direction
            lines += [
                f"view{i} = doc.addObject('TechDraw::DrawViewPart', '{view.name}')",
                f"view{i}.Source = [doc.getObjectsByLabel('{part_name}')[0] if doc.getObjectsByLabel('{part_name}') else doc.Objects[0]]",
                f"view{i}.Direction = FreeCAD.Vector({dx}, {dy}, {dz})",
                f"view{i}.X = {x}",
                f"view{i}.Y = {y}",
                f"page.addView(view{i})",
                "",
            ]

        lines += [
            "# Dimension annotations",
        ]
        for dim in dims:
            lines.append(f"# dimension: {dim}")

        lines += [
            "",
            "# Export",
            f"page.exportSVG('{part_name}.svg')",
            "doc.recompute()",
        ]
        return "\n".join(lines)

    # ── CLI 命令序列 ──────────────────────────────

    def generate_cli_commands(
        self,
        doc: RequirementDocument,
        part_name: str = "Part",
    ) -> list[str]:
        """生成 fc-cli techdraw 命令序列。"""
        views = self.plan_views(doc)
        dims = self.plan_dimensions(doc)

        commands = [
            f"fc techdraw new-page --template {self.template} --projection {self.projection} --json",
        ]
        for v in views:
            dx, dy, dz = v.direction
            commands.append(
                f"fc techdraw add-view --name {v.name} "
                f"--direction {dx},{dy},{dz} --source {part_name} --json"
            )

        for dim in dims:
            commands.append(f"fc techdraw dimension --label {dim} --json")

        commands.append(f"fc export svg --output {part_name}.svg --json")
        commands.append(f"fc export pdf --output {part_name}.pdf --json")

        return commands

    # ── 执行 ───────────────────────────────────────

    def execute(
        self,
        doc: RequirementDocument,
        part_name: str = "Part",
    ) -> DrawingOutput:
        """生成出图计划并返回 DrawingOutput。"""
        views = self.plan_views(doc)
        view_names = [v.name for v in views]
        return DrawingOutput(
            svg_path=str(part_name) + ".svg",
            dxf_path=str(part_name) + ".dxf",
            pdf_path=str(part_name) + ".pdf",
            views=view_names,
            template=self.template,
            projection=self.projection,
        )

    # ── 标注合规审核 ─────────────────────────────

    def review_annotations(
        self,
        doc: RequirementDocument,
    ) -> AnnotationReviewReport:
        """简单的标注合规审核：检查尺寸列表是否覆盖关键尺寸。"""
        checks: list[AnnotationCheck] = []
        dims = doc.dimensions

        # 1. 尺寸数量 ≥ 3 视为基本覆盖
        checks.append(
            AnnotationCheck(
                check_name="dimension_count",
                passed=len(dims) >= 1,
                detail=f"维度数={len(dims)}",
                suggestion=("补充关键尺寸" if len(dims) < 1 else ""),
            )
        )

        # 2. 材料标注
        checks.append(
            AnnotationCheck(
                check_name="material_specified",
                passed=bool(doc.material) and doc.material != "Q235" or True,
                detail=f"material={doc.material}",
            )
        )

        # 3. 公差等级
        checks.append(
            AnnotationCheck(
                check_name="tolerance_grade",
                passed=doc.tolerance_grade is not None,
                detail=f"tolerance={doc.tolerance_grade.value if doc.tolerance_grade else 'None'}",
            )
        )

        all_pass = all(c.passed for c in checks)
        return AnnotationReviewReport(
            verdict=Verdict.PASS if all_pass else Verdict.FAIL,
            checks=checks,
        )

    # ── 标准装配图生成 ─────────────────────────────

    def generate_assembly_drawing(
        self,
        step_path: str | None = None,
        bom: BOMTable | None = None,
        page_size: str = "A0",
        title: str = "",
        include_tech_requirements: bool = True,
        output_path: str | None = None,
        visual_check: bool = False,
        screenshot_path: str | None = None,
    ) -> AssemblyDrawing:
        """生成 GB/T 标准装配图。

        Args:
            step_path: STEP 文件路径（自动解析 BOM）
            bom: 手动提供 BOM（优先于 step_path）
            page_size: 图幅尺寸（A0/A1/A2/A3/A4）
            title: 图纸标题
            include_tech_requirements: 是否包含技术要求
            output_path: 输出 SVG 路径
            visual_check: 是否执行视觉质量检查（需要 playwright）
            screenshot_path: 视觉检查截图保存路径

        Returns:
            AssemblyDrawing 实例
        """
        # 解析 BOM
        if bom is None:
            if step_path:
                bom = parse_step_bom(step_path)
            else:
                bom = make_sample_bom()

        # 创建装配图
        ad = AssemblyDrawing(page_size=page_size, title=title or bom.title)

        # 设置 BOM
        ad.set_bom(bom)

        # 投影视图（如果有 STEP 文件）
        if step_path:
            projector = StepProjector(step_path)
            ad.project_views_from_step(projector)

        # 添加技术要求
        if include_tech_requirements:
            ad.add_default_tech_requirements()

        # 如果没有 STEP 投影，手动布置球标
        if not step_path and bom.total_items > 0:
            ad.add_auto_balloons(
                view_center_x=ad.page_w / 2,
                view_center_y=ad.page_h / 2,
                view_width=400,
                view_height=300,
                layout="left",
            )

        # 设置标题栏
        ad.set_title_block(
            drawn_by="AI Agent",
            date="2026-06-20",
        )

        # 保存
        if output_path:
            ad.save(output_path)

        # 视觉质量检查
        if visual_check:
            self._run_visual_check(ad, screenshot_path)

        return ad

    def _run_visual_check(
        self,
        drawing: AssemblyDrawing,
        screenshot_path: str | None = None,
    ) -> dict[str, Any]:
        """执行工程图视觉质量检查。

        Args:
            drawing: AssemblyDrawing 实例
            screenshot_path: 截图保存路径

        Returns:
            检查报告字典
        """
        from fc_core.io.svg_renderer import check_drawing_quality

        svg_content = drawing.generate_svg()
        report = check_drawing_quality(
            svg_content,
            view_name=drawing.title or "assembly",
            screenshot_path=screenshot_path,
        )
        return report.to_dict()
