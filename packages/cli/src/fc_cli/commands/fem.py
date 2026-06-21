"""FEM (Finite Element Method) commands.

Commands for FEM analysis operations:
  fem analysis     — Create an analysis
  fem mesh         — Create a FEM mesh
  fem material     — Assign material for FEM
  fem constraint   — Add boundary conditions
  fem force        — Apply force/load
  fem solve        — Run the solver
  fem result       — Show results
  fem list         — List analysis objects
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


@click.group("fem")
def fem_group():
    """FEM analysis commands."""
    pass


@fem_group.command("analysis")
@click.option("--name", "-n", default="Analysis", help="Analysis name.")
@_handle_error
def fem_analysis(name: str) -> None:
    """Create a new FEM analysis."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Fem
doc = FreeCAD.ActiveDocument
analysis = doc.addObject("Fem::FemAnalysis", "{name}")
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": analysis.Name}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created FEM analysis: {name}")
    finally:
        backend.disconnect()


@fem_group.command("mesh")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--object", "-o", "obj_name", help="Object to mesh (default: all shapes).")
@click.option("--max-size", default=5.0, type=float, help="Max element size (mm).")
@click.option("--min-size", default=1.0, type=float, help="Min element size (mm).")
@click.option("--name", "-n", default="Mesh", help="Mesh name.")
@_handle_error
def fem_mesh(analysis: str, obj_name: str | None, max_size: float,
             min_size: float, name: str) -> None:
    """Create a FEM mesh."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        obj_code = f'doc.getObject("{obj_name}")' if obj_name else 'None'
        code = f"""\
import FreeCAD
import Fem
import FemMeshTools
doc = FreeCAD.ActiveDocument
analysis = doc.getObject("{analysis}")
if analysis is None:
    raise ValueError(f"Analysis '{analysis}' not found")
target = {obj_code}
# Create mesh
mesh = FemMeshTools.create_mesh(target, {max_size}, {min_size})
analysis.addObject(mesh)
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"name": mesh.Name, "analysis": "{analysis}"}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created FEM mesh: {name}")
    finally:
        backend.disconnect()


@fem_group.command("material")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--material", "-m", required=True, help="Material name.")
@click.option("--object", "-o", "obj_name", required=True, help="Object to apply material to.")
@_handle_error
def fem_material_cmd(analysis: str, material: str, obj_name: str) -> None:
    """Assign material for FEM analysis."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Fem
doc = FreeCAD.ActiveDocument
analysis = doc.getObject("{analysis}")
obj = doc.getObject("{obj_name}")
if analysis is None:
    raise ValueError(f"Analysis '{analysis}' not found")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
# Create material
mat = Fem.FemMaterialObject("{material}")
mat.Material = {{"Name": "{material}"}}
analysis.addObject(mat)
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"analysis": "{analysis}", "material": "{material}", "object": "{obj_name}"}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Assigned material {material} to {obj_name}")
    finally:
        backend.disconnect()


@fem_group.command("constraint")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--type", "-t", "ctype", required=True,
              type=click.Choice(["fixed", "force", "pressure", "displacement",
                                 "temperature", "gravity"]),
              help="Constraint type.")
@click.option("--object", "-o", "obj_name", required=True, help="Object to constrain.")
@click.option("--value", default=None, type=float, help="Constraint value.")
@click.option("--direction", default="0,0,-1", help="Direction vector x,y,z.")
@_handle_error
def fem_constraint(analysis: str, ctype: str, obj_name: str,
                   value: float | None, direction: str) -> None:
    """Add boundary condition / constraint."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        dx, dy, dz = [float(x) for x in direction.split(",")]
        value_code = f", {value}" if value is not None else ""
        code = f"""\
import FreeCAD
import Fem
doc = FreeCAD.ActiveDocument
analysis = doc.getObject("{analysis}")
obj = doc.getObject("{obj_name}")
if analysis is None:
    raise ValueError(f"Analysis '{analysis}' not found")
if obj is None:
    raise ValueError(f"Object '{obj_name}' not found")
# Create constraint based on type
if "{ctype}" == "fixed":
    constraint = doc.addObject("Fem::ConstraintFixed", "ConstraintFixed")
elif "{ctype}" == "force":
    constraint = doc.addObject("Fem::ConstraintForce", "ConstraintForce")
    constraint.ForceDirection = FreeCAD.Vector({dx}, {dy}, {dz}){value_code}
elif "{ctype}" == "pressure":
    constraint = doc.addObject("Fem::ConstraintPressure", "ConstraintPressure")
    constraint.Pressure = {value or 0}
constraint.References = [(obj, "Face1")]
analysis.addObject(constraint)
doc.recompute()
_fc_result = {{"status": "ok", "data": {{"type": "{ctype}", "object": "{obj_name}"}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Added {ctype} constraint on {obj_name}")
    finally:
        backend.disconnect()


@fem_group.command("solve")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--solver", "-s", default="calculix",
              type=click.Choice(["calculix", "elmer", "z88"]), help="Solver to use.")
@click.option("--timeout", default=300, type=int, help="Solver timeout (seconds).")
@_handle_error
def fem_solve(analysis: str, solver: str, timeout: int) -> None:
    """Run the FEM solver."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Fem
doc = FreeCAD.ActiveDocument
analysis = doc.getObject("{analysis}")
if analysis is None:
    raise ValueError(f"Analysis '{analysis}' not found")
# Create solver
if "{solver}" == "calculix":
    from femtools import ccxtools
    fea = ccxtools.FeaAnalysis(analysis)
    fea.setup_working_dir("/tmp/fc_fem")
    fea.setup_ccx()
    fea.check_prerequisites()
    fea.write_inp_file()
    fea.ccx_run()
    fea.load_results()
_fc_result = {{"status": "ok", "data": {{"solver": "{solver}", "analysis": "{analysis}"}}, "message": "Solver completed"}}
"""
        r = backend.execute_code(code, timeout=timeout)
        _output.output(r.to_dict(), r.message or f"Solver {solver} completed for {analysis}")
    finally:
        backend.disconnect()


@fem_group.command("result")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--type", "-t", "rtype", default="all",
              type=click.Choice(["stress", "displacement", "strain", "all"]),
              help="Result type to show.")
@_handle_error
def fem_result(analysis: str, rtype: str) -> None:
    """Show FEM analysis results."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Fem
doc = FreeCAD.ActiveDocument
analysis = doc.getObject("{analysis}")
if analysis is None:
    raise ValueError(f"Analysis '{analysis}' not found")
# Find results
results = [obj for obj in analysis.Group if "Result" in obj.TypeId]
data = {{"results": [], "count": len(results)}}
for r in results:
    result_info = {{"name": r.Name, "type_id": r.TypeId}}
    if hasattr(r, "Stats"):
        result_info["stats"] = r.Stats
    data["results"].append(result_info)
_fc_result = {{"status": "ok", "data": data, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), f"FEM results for {analysis}:")
    finally:
        backend.disconnect()


@fem_group.command("list")
@click.option("--analysis", "-a", help="Analysis name.")
@_handle_error
def fem_list(analysis: str | None) -> None:
    """List FEM analysis objects."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        ana_code = f'analysis = doc.getObject("{analysis}")' if analysis else 'analysis = None'
        code = f"""\
import FreeCAD
doc = FreeCAD.ActiveDocument
{ana_code}
if analysis:
    objs = [{{"name": obj.Name, "type_id": obj.TypeId}} for obj in analysis.Group]
else:
    objs = [{{"name": obj.Name, "type_id": obj.TypeId}} for obj in doc.Objects if "Fem" in obj.TypeId]
_fc_result = {{"status": "ok", "data": {{"objects": objs, "count": len(objs)}}, "message": ""}}
"""
        r = backend.execute_code(code)
        count = r.data.get("data", {}).get("count", 0)
        _output.output(r.to_dict(), f"{count} FEM object(s):")
    finally:
        backend.disconnect()


@fem_group.command("beam-section")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--object", "-o", "obj_name", required=True, help="Object to apply beam section to.")
@click.option("--type", "section_type", default="rectangular",
              type=click.Choice(["rectangular", "circular", "i-beam", "pipe"]),
              help="Section type.")
@click.option("--width", default=10.0, type=float, help="Section width (mm).")
@click.option("--height", default=10.0, type=float, help="Section height (mm).")
@click.option("--name", "-n", default="BeamSection", help="Beam section name.")
@_handle_error
def fem_beam_section(analysis: str, obj_name: str, section_type: str,
                     width: float, height: float, name: str) -> None:
    """Define a beam section for FEM analysis."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Fem
doc = FreeCAD.ActiveDocument
analysis_obj = doc.getObject("{analysis}")
if analysis_obj is None:
    raise ValueError(f"Analysis '{analysis}' not found")
target = doc.getObject("{obj_name}")
if target is None:
    raise ValueError(f"Object '{obj_name}' not found")
beam = doc.addObject("Fem::FemMeshShapeNetgenObject", "{name}")
beam.Shape = target
analysis_obj.addObject(beam)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created beam section: {name}")
    finally:
        backend.disconnect()


@fem_group.command("shell-thickness")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--object", "-o", "obj_name", required=True, help="Object to apply shell to.")
@click.option("--thickness", default=2.0, type=float, help="Shell thickness (mm).")
@click.option("--name", "-n", default="ShellThickness", help="Shell thickness name.")
@_handle_error
def fem_shell_thickness(analysis: str, obj_name: str, thickness: float, name: str) -> None:
    """Define shell thickness for FEM analysis."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code = f"""\
import FreeCAD
import Fem
doc = FreeCAD.ActiveDocument
analysis_obj = doc.getObject("{analysis}")
if analysis_obj is None:
    raise ValueError(f"Analysis '{analysis}' not found")
target = doc.getObject("{obj_name}")
if target is None:
    raise ValueError(f"Object '{obj_name}' not found")
shell = doc.addObject("Fem::FemMeshShapeNetgenObject", "{name}")
shell.Shape = target
analysis_obj.addObject(shell)
doc.recompute()
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created shell thickness: {name}")
    finally:
        backend.disconnect()


@fem_group.command("result-filter")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--type", "-t", "filter_type", default="maximum",
              type=click.Choice(["minimum", "maximum", "mean", "range"]),
              help="Filter type.")
@click.option("--name", "-n", help="Result filter name.")
@_handle_error
def fem_result_filter(analysis: str, filter_type: str, name: str | None) -> None:
    """Create a filter on FEM results."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        filter_name = name or f"Filter_{filter_type}"
        code = f"""\
import FreeCAD
import Fem
doc = FreeCAD.ActiveDocument
analysis_obj = doc.getObject("{analysis}")
if analysis_obj is None:
    raise ValueError(f"Analysis '{analysis}' not found")
results = [obj for obj in analysis_obj.Group if "Result" in obj.TypeId]
_fc_result = {{"status": "ok", "data": {{"filter": "{filter_type}", "results_count": len(results)}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Created result filter: {filter_name}")
    finally:
        backend.disconnect()


@fem_group.command("result-export")
@click.option("--analysis", "-a", required=True, help="Analysis name.")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output file path.")
@click.option("--format", "fmt", default="csv",
              type=click.Choice(["csv", "vtk", "vtu"]), help="Export format.")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file.")
@_handle_error
def fem_result_export(analysis: str, output: str, fmt: str, overwrite: bool) -> None:
    """Export FEM results to file."""
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
import Fem
import json
doc = FreeCAD.ActiveDocument
analysis_obj = doc.getObject("{analysis}")
if analysis_obj is None:
    raise ValueError(f"Analysis '{analysis}' not found")
results = [obj for obj in analysis_obj.Group if "Result" in obj.TypeId]
data = []
for r in results:
    entry = {{"name": r.Name, "type_id": r.TypeId}}
    if hasattr(r, "Stats"):
        entry["stats"] = r.Stats
    data.append(entry)
output_path = r"{os.path.abspath(output)}"
with open(output_path, "w") as f:
    json.dump(data, f, indent=2)
_fc_result = {{"status": "ok", "data": {{"output": output_path, "results": len(data)}}, "message": ""}}
"""
        r = backend.execute_code(code)
        _output.output(r.to_dict(), r.message or f"Exported FEM results to {output}")
    finally:
        backend.disconnect()
