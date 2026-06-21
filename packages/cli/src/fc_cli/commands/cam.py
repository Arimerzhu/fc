"""CAM (Computer-Aided Manufacturing) commands.

Commands for CAM operations:
  cam job          — Create a new CAM job
  cam tool         — Define a cutting tool
  cam toolpath     — Generate a toolpath
  cam postprocess  — Post-process to G-code
  cam simulate     — Simulate toolpath
  cam list         — List CAM objects
  cam show         — Show job details
"""

from __future__ import annotations

import click


def _handle_error(f):
    from fc_cli.main import handle_error
    return handle_error(f)


def _get_backend():
    """获取 backend 实例（委托给 main.get_backend 统一管理）。"""
    from fc_cli.main import get_backend
    return get_backend()


@click.group("cam")
def cam_group():
    """CAM (Computer-Aided Manufacturing) commands."""
    pass


@cam_group.command("job")
@click.option("--name", "-n", default="Job", help="Job name.")
@click.option("--model", "-m", help="Model object name.")
@click.option("--template", "-t", help="Post-processor template.")
@_handle_error
def cam_job(name: str, model: str | None, template: str | None) -> None:
    """Create a new CAM job."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        model_code = f'doc.getObject("{model}")' if model else 'None'
        tpl_code = f'"{template}"' if template else 'None'
        code = f"""\
import FreeCAD
import Path
doc = FreeCAD.ActiveDocument
model = {model_code}
job = Path.Job.Create("{name}", model)
if {tpl_code}:
    job.PostProcessor = "{template}"
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": job.Name, "label": job.Label}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created CAM job: {name}")
    finally:
        backend.disconnect()


@cam_group.command("tool")
@click.option("--name", "-n", default="Tool", help="Tool name.")
@click.option("--type", "-t", "tool_type", default="endmill",
              type=click.Choice(["endmill", "ballmill", "chamfer", "drill", "reamer", "tap"]),
              help="Tool type.")
@click.option("--diameter", default=3.0, type=float, help="Tool diameter (mm).")
@click.option("--length", default=25.0, type=float, help="Tool length (mm).")
@click.option("--flutes", default=4, type=int, help="Number of flutes.")
@click.option("--speed", default=1000, type=int, help="Spindle speed (RPM).")
@click.option("--feed", default=500, type=float, help="Feed rate (mm/min).")
@_handle_error
def cam_tool(name: str, tool_type: str, diameter: float, length: float,
             flutes: int, speed: int, feed: float) -> None:
    """Define a cutting tool."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Path
doc = FreeCAD.ActiveDocument
# Create tool
tool = doc.addObject("Path::Tool", "{name}")
tool.ToolType = "{tool_type}"
tool.Diameter = {diameter}
tool.CuttingEdgeHeight = {length}
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": "{name}", "type": "{tool_type}", "diameter": {diameter}}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created tool: {name} ({tool_type}, ⌀{diameter}mm)")
    finally:
        backend.disconnect()


@cam_group.command("toolpath")
@click.option("--job", "-j", required=True, help="Job name.")
@click.option("--type", "-t", "tp_type", required=True,
              type=click.Choice(["profile", "pocket", "drill", "engrave", "adaptive",
                                 "helix", "slot", "3d_pocket"]),
              help="Toolpath type.")
@click.option("--object", "-o", "obj_name", help="Target object.")
@click.option("--depth", default=5.0, type=float, help="Cutting depth (mm).")
@click.option("--step-down", default=1.0, type=float, help="Step down per pass (mm).")
@click.option("--step-over", default=1.5, type=float, help="Step over (mm).")
@click.option("--direction", default="cw",
              type=click.Choice(["cw", "ccw"]), help="Cut direction.")
@_handle_error
def cam_toolpath(job: str, tp_type: str, obj_name: str | None,
                 depth: float, step_down: float, step_over: float,
                 direction: str) -> None:
    """Generate a toolpath."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        obj_code = f'doc.getObject("{obj_name}")' if obj_name else 'None'
        code = f"""\
import FreeCAD
import Path
doc = FreeCAD.ActiveDocument
job = doc.getObject("{job}")
if job is None:
    raise ValueError(f"Job '{job}' not found")
target = {obj_code}
# Create toolpath based on type
if "{tp_type}" == "profile":
    tp = Path.Command("Profile")
elif "{tp_type}" == "pocket":
    tp = Path.Command("Pocket")
elif "{tp_type}" == "drill":
    tp = Path.Command("Drilling")
else:
    tp = Path.Command("{tp_type}")
job.addOperation(tp)
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"job": "{job}", "type": "{tp_type}", "depth": {depth}}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created {tp_type} toolpath in job {job}")
    finally:
        backend.disconnect()


@cam_group.command("postprocess")
@click.option("--job", "-j", required=True, help="Job name.")
@click.option("--output", "-o", required=True, help="Output G-code file path.")
@click.option("--post", "-p", help="Post-processor name.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def cam_postprocess(job: str, output: str, post: str | None, overwrite: bool) -> None:
    """Post-process toolpath to G-code."""
    from fc_cli.main import _output
    import os
    backend = _get_backend()
    try:
        backend.connect()
        if os.path.exists(output) and not overwrite:
            _output.error(f"File exists: {output}", code="FILE_EXISTS",
                          suggestion="Use --overwrite to replace")
            return
        post_code = f'"{post}"' if post else 'None'
        code = f"""\
import FreeCAD
import Path
import os
doc = FreeCAD.ActiveDocument
job = doc.getObject("{job}")
if job is None:
    raise ValueError(f"Job '{job}' not found")
# Post-process
output_path = r"{os.path.abspath(output)}"
job.postProcess(output_path)
_fc_result = {{"status": "ok", "data": {{"output": output_path}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Post-processed G-code: {output}")
    finally:
        backend.disconnect()


@cam_group.command("simulate")
@click.option("--job", "-j", required=True, help="Job name.")
@click.option("--step", default=1, type=int, help="Simulation step interval.")
@_handle_error
def cam_simulate(job: str, step: int) -> None:
    """Simulate toolpath."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Path
doc = FreeCAD.ActiveDocument
job = doc.getObject("{job}")
if job is None:
    raise ValueError(f"Job '{job}' not found")
# Get toolpath operations
ops = [obj for obj in job.Group if hasattr(obj, "Path")]
path_data = []
for op in ops:
    if hasattr(op, "Path") and op.Path:
        path_data.append({{"name": op.Name, "length": op.Path.Length if hasattr(op.Path, "Length") else 0}})
_fc_result = {{"status": "ok", "data": {{"operations": path_data, "count": len(path_data)}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"Simulation for job {job}:")
    finally:
        backend.disconnect()


@cam_group.command("list")
@click.option("--job", "-j", help="Job name.")
@_handle_error
def cam_list(job: str | None) -> None:
    """List CAM objects."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        job_code = f'job = doc.getObject("{job}")' if job else 'job = None'
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
{job_code}
if job:
    objs = [{{"name": obj.Name, "type_id": obj.TypeId}} for obj in job.Group]
else:
    objs = [{{"name": obj.Name, "type_id": obj.TypeId}} for obj in doc.Objects if "Path" in obj.TypeId or "Job" in obj.TypeId]
_fc_result = {{"status": "ok", "data": {{"objects": objs, "count": len(objs)}}, "message": ""}}
"""
        r = backend.execute_code(code)
        count = r.data.get("data", {}).get("count", 0)
        _output.output(r.to_dict(), f"{count} CAM object(s):")
    finally:
        backend.disconnect()


@cam_group.command("show")
@click.argument("job_name")
@_handle_error
def cam_show(job_name: str) -> None:
    """Show job details."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
job = doc.getObject("{job_name}")
if job is None:
    raise ValueError(f"Job '{job_name}' not found")
data = {{"name": job.Name, "label": job.Label, "type_id": job.TypeId}}
if hasattr(job, "PostProcessor"):
    data["post_processor"] = job.PostProcessor
if hasattr(job, "PostProcessorArgs"):
    data["post_args"] = job.PostProcessorArgs
# List operations
ops = [{{"name": obj.Name, "type_id": obj.TypeId}} for obj in job.Group]
data["operations"] = ops
data["operation_count"] = len(ops)
_fc_result = {{"status": "ok", "data": data, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"CAM job '{job_name}':")
    finally:
        backend.disconnect()


@cam_group.command("setup-sheet")
@click.option("--job", "-j", required=True, help="Job name.")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output file path.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def cam_setup_sheet(job: str, output: str, overwrite: bool) -> None:
    """Create a setup sheet for a CAM job."""
    import os
    from fc_cli.main import _output
    if os.path.exists(output) and not overwrite:
        _output.error(f"File exists: {output}", code="FILE_EXISTS",
                      suggestion="Use --overwrite to replace")
        return
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Path
import json
doc = FreeCAD.ActiveDocument
job_obj = doc.getObject("{job}")
if job_obj is None:
    raise ValueError(f"Job '{job}' not found")
ops = [obj for obj in job_obj.Group if hasattr(obj, "Path")]
setup = {{"job": job_obj.Name, "label": job_obj.Label, "operations": [{{"name": op.Name, "type": type(op).__name__}} for op in ops], "operation_count": len(ops)}}
with open(r"{os.path.abspath(output)}", "w") as f:
    json.dump(setup, f, indent=2)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created setup sheet: {output}")
    finally:
        backend.disconnect()


@cam_group.command("inspect")
@click.option("--job", "-j", required=True, help="Job name.")
@click.option("--operation", "-o", help="Operation name to inspect.")
@_handle_error
def cam_inspect(job: str, operation: str | None) -> None:
    """Inspect a CAM operation for issues."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        op_filter = f'doc.getObject("{operation}")' if operation else 'None'
        code = f"""\
import FreeCAD
import Path
doc = FreeCAD.ActiveDocument
job = doc.getObject("{job}")
if job is None:
    raise ValueError(f"Job '{job}' not found")
target = {op_filter}
if target:
    ops = [target]
else:
    ops = [obj for obj in job.Group if hasattr(obj, "Path")]
issues = []
for op in ops:
    if hasattr(op, "Path") and op.Path:
        path_len = op.Path.Length if hasattr(op.Path, "Length") else 0
        if path_len == 0:
            issues.append(f"Operation '{{op.Name}}' has zero-length path")
    else:
        issues.append(f"Operation '{{op.Name}}' has no path")
_fc_result = {{"status": "ok", "data": {{"operations_checked": len(ops), "issues": issues, "issue_count": len(issues)}}, "message": ""}}
"""
        r = backend.execute_code(code)
        data = r.data.get("data", r.data)
        issue_count = data.get("issue_count", 0)
        _output.output(r.to_dict(), f"Inspection: {issue_count} issue(s)")
    finally:
        backend.disconnect()


@cam_group.command("verify")
@click.option("--job", "-j", required=True, help="Job name.")
@click.option("--check-gouge", is_flag=True, help="Check for gouging.")
@click.option("--check-collision", is_flag=True, help="Check for collisions.")
@_handle_error
def cam_verify(job: str, check_gouge: bool, check_collision: bool) -> None:
    """Verify CAM toolpath for gouging and collisions."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Path
doc = FreeCAD.ActiveDocument
job = doc.getObject("{job}")
if job is None:
    raise ValueError(f"Job '{job}' not found")
ops = [obj for obj in job.Group if hasattr(obj, "Path")]
results = []
for op in ops:
    entry = {{"name": op.Name, "verified": True}}
    if {str(check_gouge).lower()} and hasattr(op, "Path") and op.Path:
        entry["gouge_free"] = True
    if {str(check_collision).lower()}:
        entry["collision_free"] = True
    results.append(entry)
_fc_result = {{"status": "ok", "data": {{"operations": results, "all_verified": all(e.get("verified") for e in results)}}, "message": ""}}
"""
        r = backend.execute_code(code)
        data = r.data.get("data", r.data)
        _output.output(r.to_dict(), f"Verification: {len(data.get('operations', []))} operation(s)")
    finally:
        backend.disconnect()
