"""Agent command — `fc agent` entry point (P2.5).

子命令:
  fc agent pipeline "描述一个盒子 100x50x25mm"
  fc agent library list
  fc agent library get bolt_m6_16
  fc agent library search gear
  fc agent handshake --file result.json --schema requirement
  fc agent explain --file result.json
  fc agent "描述一个盒子 100x50x25mm"    ← 旧用法（保持向后兼容）
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import click

logger = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
@click.pass_context
def agent_command(ctx: click.Context, verbose: bool) -> None:
    """Agent Native CAD — 多Agent 协同驱动 FreeCAD。"""
    if verbose:
        logging.basicConfig(level=logging.DEBUG,
                            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ════════════════════════════════════════════════════════════
#  agent pipeline  — 自然语言 → 图纸（Orchestrator）
# ════════════════════════════════════════════════════════════

@agent_command.command("pipeline")
@click.argument("prompt")
@click.option("--output-dir", "-o", type=click.Path(), default=None,
              help="Output directory for generated files.")
@click.option("--dry-run", is_flag=True,
              help="只解析需求并计划，不调用 FreeCAD。")
@click.option("--max-retries", default=2, type=int,
              help="Maximum retry attempts.")
@click.option("--max-duration", default=600, type=int,
              help="Total pipeline timeout in seconds.")
@click.option("--explain/--no-explain", default=True,
              help="Print human-readable diagnosis.")
@click.option("--output-json", "out_json", type=click.Path(), default=None,
              help="Save PipelineResult JSON to this file.")
@click.pass_context
def pipeline_command(ctx: click.Context, prompt: str, output_dir: str | None,
                      dry_run: bool, max_retries: int, max_duration: int,
                      explain: bool, out_json: str | None) -> None:
    """运行完整的 Orchestrator 流水线。

    \b
    Examples:
      fc agent pipeline "设计一个盒子 100x50x25mm"
      fc agent pipeline "圆柱 r=10 h=50" --dry-run
    """
    from fc_runtime.orchestrator import Orchestrator

    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "fc_output")
    os.makedirs(output_dir, exist_ok=True)

    orch = Orchestrator(max_retries=max_retries,
                        max_duration_sec=max_duration,
                        verbose=ctx.parent and ctx.parent.params.get("verbose", False))

    print(f"\n{'='*60}")
    print(f"  fc agent pipeline — Autonomous CAD Design")
    print(f"{'='*60}")
    print(f"\n  Design request: {prompt}")
    if dry_run:
        print(f"  Mode: DRY RUN (no FreeCAD execution)")
    print()

    result = orch.run(prompt, part_name="Part", dry_run=dry_run)

    # 输出诊断
    if explain:
        print(orch.explain(result))
        print()

    # 保存 JSON
    if out_json:
        out_json = os.path.abspath(out_json)
        os.makedirs(os.path.dirname(out_json), exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            f.write(result.to_json())
        print(f"  Pipeline JSON → {out_json}")

    # 退出码
    if result.stage.value == "failed":
        sys.exit(1)


# ════════════════════════════════════════════════════════════
#  agent library — 标准件库
# ════════════════════════════════════════════════════════════

@agent_command.group("library")
def library_group() -> None:
    """标准件库操作。"""


@library_group.command("list")
def library_list() -> None:
    """列出所有标准件。"""
    from fc_runtime.standard_library import get_library
    names = get_library().list_all()
    print(f"  Standard parts ({len(names)}):")
    for n in names:
        print(f"    - {n}")


@library_group.command("search")
@click.argument("keyword")
def library_search(keyword: str) -> None:
    """按关键词搜索标准件。"""
    from fc_runtime.standard_library import get_library
    parts = get_library().search(keyword)
    if not parts:
        print(f"  No parts match '{keyword}'")
        return
    print(f"  Results ({len(parts)}):")
    for p in parts:
        print(f"    - {p.short_name:20s}  [{p.part_type.value}]  {p.code}")
        print(f"      {p.description}")


@library_group.command("get")
@click.argument("short_name")
@click.option("--json", "use_json", is_flag=True,
              help="输出 RequirementDocument JSON。")
def library_get(short_name: str, use_json: bool) -> None:
    """获取一个标准件的需求描述。"""
    from fc_runtime.standard_library import get_library
    part = get_library().get(short_name)
    if part is None:
        click.echo(f"Unknown standard part: {short_name}", err=True)
        sys.exit(1)

    if use_json:
        req = part.to_requirement()
        print(json.dumps(req.model_dump(mode="json"),
                         indent=2, ensure_ascii=False))
    else:
        print(f"  Standard part: {part.short_name}")
        print(f"  Code: {part.code}")
        print(f"  Type: {part.part_type.value}")
        print(f"  Dimensions: {part.dimensions}")
        print(f"  Material: {part.material}")
        print(f"  Tolerance: {part.tolerance.value}")
        print(f"  Description: {part.description}")


@library_group.command("run")
@click.argument("short_name")
@click.option("--output-dir", "-o", type=click.Path(), default=None,
              help="Output directory.")
@click.option("--max-retries", default=2, type=int,
              help="Maximum retry attempts.")
@click.option("--max-duration", default=600, type=int,
              help="Timeout in seconds.")
@click.option("--dry-run", is_flag=True,
              help="只解析需求并计划，不调用 FreeCAD。")
def library_run(short_name: str, output_dir: str | None, max_retries: int,
                 max_duration: int, dry_run: bool) -> None:
    """直接用一个标准件跑完整流水线。

    \b
    Examples:
      fc agent library run bolt_m6_16
      fc agent library run bearing_6203 --dry-run
    """
    from fc_runtime.orchestrator import run_standard_part

    try:
        result = run_standard_part(short_name)
        print(f"  Pipeline status → {result.stage.value}")
        print(f"  Elapsed → {result.elapsed_sec:.2f}s")
        if result.errors:
            print(f"  Errors ({len(result.errors)}):")
            for lvl, msg in result.errors:
                print(f"    [{lvl.value}] {msg}")
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)


# ════════════════════════════════════════════════════════════
#  agent handshake — Schema 握手验证
# ════════════════════════════════════════════════════════════

@agent_command.command("handshake")
@click.argument("schema", nargs=1, required=True,
                type=click.Choice(["requirement", "plan", "cad_output",
                                    "drawing", "geometry_review", "annotation",
                                    "pipeline"]))
@click.option("--file", "-f", "in_file", type=click.Path(exists=True),
              default=None,
              help="包含 JSON 的输入文件。如果不指定，从 stdin 读。")
@click.option("--json-string", "-s", "in_str", type=str, default=None,
              help="直接传入 JSON 字符串。")
def handshake_command(schema: str, in_file: str | None,
                       in_str: str | None) -> None:
    """校验一个 JSON 是否符合指定 Schema。

    \b
    Examples:
      fc agent handshake requirement --file req.json
      cat plan.json | fc agent handshake plan
    """
    from fc_runtime.agent_schemas import (
        AnnotationReviewReport, CADModelingOutput, DrawingOutput,
        GeometryReviewReport, ModelingPlan, RequirementDocument,
    )
    from fc_runtime.agent_handshake import AgentHandshake, pipeline_handshake_report

    if in_str:
        data = in_str
    elif in_file:
        with open(in_file, "r", encoding="utf-8") as f:
            data = f.read()
    else:
        data = sys.stdin.read()

    mapping = {
        "requirement": RequirementDocument,
        "plan": ModelingPlan,
        "cad_output": CADModelingOutput,
        "drawing": DrawingOutput,
        "geometry_review": GeometryReviewReport,
        "annotation": AnnotationReviewReport,
    }

    if schema == "pipeline":
        # 对 Pipeline JSON 做全量握手
        from fc_runtime.orchestrator import PipelineResult, PipelineStage
        try:
            obj = json.loads(data)
            # 直接用 dict 构造简化 PipelineResult — 只做 handshake
            class _Fake:
                pass
            fake = _Fake()
            # 尝试按 schema 逐项解析
            reports = {}
            for key, model in mapping.items():
                json_key = key if key != "plan" else key
                payload = obj.get(json_key)
                if payload is None:
                    continue
                r = AgentHandshake.verify_output(model, payload)
                reports[json_key] = r.as_dict()
            result = {
                "all_valid": all(r["valid"] for r in reports.values()),
                "schema_count": len(reports),
                "reports": reports,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            if not result["all_valid"]:
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON: {e}"}, indent=2))
            sys.exit(1)
        return

    model_cls = mapping[schema]
    r = AgentHandshake.verify_output_json(model_cls, data)
    print(json.dumps(r.as_dict(), indent=2, ensure_ascii=False))
    if not r.valid:
        sys.exit(1)


# ════════════════════════════════════════════════════════════
#  agent explain — 解析 Pipeline JSON 输出诊断
# ════════════════════════════════════════════════════════════

@agent_command.command("explain")
@click.option("--file", "-f", "in_file", type=click.Path(exists=True),
              default=None,
              help="PipelineResult JSON 文件。")
@click.option("--json-string", "-s", "in_str", type=str, default=None,
              help="直接传入 Pipeline JSON。")
def explain_command(in_file: str | None, in_str: str | None) -> None:
    """解析 Pipeline JSON 并输出人类可读的诊断报告。"""
    from fc_runtime.orchestrator import Orchestrator, PipelineResult, PipelineStage

    if in_str:
        data = json.loads(in_str)
    elif in_file:
        with open(in_file, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
    else:
        data = json.loads(sys.stdin.read())

    # 构造一个简化的 PipelineResult 用于诊断
    r = PipelineResult(stage=PipelineStage(data["stage"]),
                        errors=[(type("L", (), {"value": lvl}), msg)
                                for lvl, msg in data.get("errors", [])],
                        elapsed_sec=data.get("elapsed_sec", 0.0))

    # 尝试填充需求/计划等字段，给 Orchestrator.explain() 有更多信息
    try:
        from fc_runtime.agent_schemas import (
            RequirementDocument, ModelingPlan, CADModelingOutput,
            DrawingOutput, GeometryReviewReport, AnnotationReviewReport,
        )
        if "requirement" in data:
            r.requirement = RequirementDocument.model_validate(data["requirement"])
        if "plan" in data:
            r.plan = ModelingPlan.model_validate(data["plan"])
        if "model_output" in data:
            r.model_output = CADModelingOutput.model_validate(data["model_output"])
        if "geometry_review" in data:
            r.geometry_review = GeometryReviewReport.model_validate(data["geometry_review"])
        if "drawing_output" in data:
            r.drawing_output = DrawingOutput.model_validate(data["drawing_output"])
        if "annotation_review" in data:
            r.annotation_review = AnnotationReviewReport.model_validate(data["annotation_review"])
    except Exception:
        pass

    print(Orchestrator().explain(r))


# ════════════════════════════════════════════════════════════
#  agent <prompt> — 旧用法的默认入口（保持向后兼容）
# ════════════════════════════════════════════════════════════

@agent_command.command("run")
@click.argument("prompt")
@click.option("--output-dir", "-o", type=click.Path(), default=None,
              help="Output directory for generated files.")
@click.option("--dry-run", is_flag=True,
              help="Show the plan without executing.")
@click.option("--export", "-e", multiple=True,
              help="Export formats: step, stl, pdf, fcstd, etc.")
@click.option("--max-retries", default=3, type=int,
              help="Maximum retry attempts for failed tasks.")
@click.option("--timeout", default=120, type=int,
              help="Timeout per task in seconds.")
@click.option("--backend", type=click.Choice(["headless", "rpc"]), default="headless",
              help="Backend to use.")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output.")
def run_command(prompt: str, output_dir: str | None, dry_run: bool,
                 export: tuple, max_retries: int, timeout: int, backend: str,
                 verbose: bool) -> None:
    """旧的 Planner/Executor 管线 —— 保留以保持向后兼容。

    推荐使用 `fc agent pipeline`。
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "fc_output")
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    print(f"\n{'='*60}")
    print(f"  fc agent run — Planner/Executor pipeline (legacy)")
    print(f"{'='*60}")
    print(f"\n  Design request: {prompt}")
    print()

    from fc_runtime.planner import Planner
    planner = Planner()

    with click.progressbar(length=1, label="  Planning") as bar:
        plan = planner.plan(prompt)
        bar.update(1)

    print(f"\n  Plan: {len(plan.tasks)} tasks")
    for task in plan.tasks:
        status_icon = {"pending": "[ ]", "running": "[*]", "success": "[OK]",
                        "failed": "[FAIL]"}
        icon = status_icon.get(task.status.value, "o")
        print(f"    {icon} [{task.id}] {task.description}")
    print()

    print(f"\n{'='*60}")
    print(f"  Five-Phase Execution Plan")
    print(f"{'='*60}")
    print(plan.to_five_phase_report())

    if dry_run:
        click.echo("\n  Plan details (dry run):")
        click.echo(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False, default=str))
        return

    from fc_runtime.executor import Executor
    from fc_runtime.corrector import Corrector

    corrector = Corrector(max_retries=max_retries)

    fc_exec = sys.argv[0]
    if fc_exec and os.path.isabs(fc_exec) and os.path.exists(fc_exec):
        pass
    else:
        scripts_dir = os.path.dirname(sys.executable)
        venv_fc = os.path.join(scripts_dir, "fc.exe")
        fc_exec = venv_fc if os.path.exists(venv_fc) else "fc"

    executor = Executor(fc_path=fc_exec, timeout=timeout,
                        working_dir=output_dir, backend=backend)

    print(f"  Executing plan...\n")
    start_time = time.time()

    old_cwd = os.getcwd()
    os.chdir(output_dir)
    try:
        results = executor.execute_plan(plan, corrector=corrector)
    finally:
        os.chdir(old_cwd)

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"  Execution Report")
    print(f"{'='*60}")

    success_count = sum(1 for r in results if r.success)
    fail_count = sum(1 for r in results if not r.success)

    print(f"\n  Tasks: {len(results)} total, {success_count} succeeded, {fail_count} failed")
    print(f"  Time: {elapsed:.1f}s")

    if fail_count > 0:
        print(f"\n  Failed tasks:")
        for task in plan.tasks:
            if task.status.value == "failed":
                print(f"    [FAIL] [{task.id}] {task.description}")
                if task.error:
                    print(f"      Error: {task.error}")

    from fc_runtime.bom import BOMGenerator
    bom_gen = BOMGenerator(timeout=timeout)
    try:
        bom = bom_gen.from_plan(plan, working_dir=output_dir)
        bom.project_name = prompt[:60]

        if bom.items:
            print(f"\n{bom.to_table()}")

            bom_files = bom_gen.export_bom(bom, output_dir=output_dir,
                                            formats=["json", "csv", "md"])
            if bom_files:
                print(f"\n  BOM exported:")
                for f in bom_files:
                    print(f"    > {f}")
        else:
            print(f"\n  No parts detected for BOM generation.")
    except Exception as e:
        logger.warning(f"BOM generation failed: {e}")
        print(f"\n  BOM generation skipped: {e}")

    print(f"\n{'='*60}")
    if plan.status.value == "success":
        print(f"  [OK] Design complete!")
    elif plan.status.value == "failed":
        print(f"  [FAIL] Design incomplete — some tasks failed")
    else:
        print(f"  Status: {plan.status.value}")
    print(f"  Output directory: {output_dir}")
    print(f"{'='*60}\n")

    report_path = os.path.join(output_dir, "plan_report.json")
    try:
        report_data = plan.to_dict()
        report_data["five_phase_report"] = plan.to_five_phase_report()
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"  Plan report: {report_path}")
    except Exception as e:
        logger.warning(f"Could not write plan report: {e}")

    if plan.status.value == "failed":
        sys.exit(1)


if __name__ == "__main__":
    agent_command()
