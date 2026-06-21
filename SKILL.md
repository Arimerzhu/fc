# SKILL.md — fc (Agent Native FreeCAD CLI)

> AI Agent skill definition for fc. Read this file to understand how to
> use fc commands for CAD design tasks.
>
> **快速上手**: 先读 `docs/AI_AGENT_GUIDE.md`，按五阶段执行流操作。
>
> **Skill 体系**: 7 个分类 skill 文件覆盖全部 17 个命令组。加载策略见 `docs/skills/SKILL.md`。

## What is fc

fc is a comprehensive CLI tool for FreeCAD. It exposes 258+ commands across
all FreeCAD workbenches, designed for AI agent consumption with JSON output.
It supports dual backends: **headless** (FreeCADCmd subprocess, default) and
**RPC** (FreeCAD GUI via XML-RPC).

## Global Options

| Option | Description |
|--------|-------------|
| `--json` | Output in JSON format (recommended for agents) |
| `--backend headless\|rpc` | Backend: headless (FreeCADCmd) or rpc (FreeCAD GUI) |
| `--freecad-path PATH` | Path to FreeCAD executable |
| `--project PATH` | Project file for session persistence |
| `--host HOST` | RPC host (default: localhost) |
| `--port PORT` | RPC port (default: 9875) |

## Command Groups

### 1. document — Document lifecycle
| Command | Description | Key params |
|---------|-------------|------------|
| `document new` | Create new document | `--name NAME`, `--output PATH` |
| `document open PATH` | Open existing document | positional (file path) |
| `document save` | Save document | `--output PATH` (optional save-as) |
| `document info` | Show document info | -- |
| `document close` | Close current document | -- |
| `document list` | List open documents | -- |

### 2. part — Part primitives & operations
| Command | Description | Key params |
|---------|-------------|------------|
| `part add TYPE` | Create primitive (box, cylinder, sphere, cone, torus, wedge, helix, ellipsoid, spiral) | `--name`, `--param key=value` |
| `part remove NAME` | Remove a part | positional (name) |
| `part list` | List all parts | -- |
| `part get NAME` | Get part details | positional (name) |
| `part transform NAME` | Change position/rotation | `--position x,y,z`, `--rotation rx,ry,rz` |
| `part boolean OP` | Boolean operation: cut, fuse, common | `base`, `tool`, `--name` |
| `part copy NAME` | Copy a part | `--name COPY_NAME` |
| `part mirror NAME` | Mirror across a plane | `--plane XY|XZ|YZ`, `--name RESULT_NAME` |
| `part scale NAME FACTOR` | Scale by uniform or x,y,z factors | `--name RESULT_NAME` |
| `part fillet-3d NAME` | Fillet edges | `--radius`, `--edges all|1,2,3` |
| `part chamfer-3d NAME` | Chamfer edges | `--size`, `--edges all|1,2,3` |
| `part hole NAME` | Create a hole | `--diameter`, `--depth`, `--position x,y,z`, `--direction x,y,z` |
| `part info NAME` | Detailed part info | positional (name) |
| `part bounds NAME` | Get bounding box | positional (name) |

### 3. sketch — 2D sketching
| Command | Description | Key params |
|---------|-------------|------------|
| `sketch new` | Create new sketch | `--name`, `--plane XY|XZ|YZ`, `--offset` |
| `sketch add-line SKETCH` | Add a line segment | `--start x,y`, `--end x,y` |
| `sketch add-circle SKETCH` | Add a circle | `--center x,y`, `--radius` |
| `sketch add-rect SKETCH` | Add a rectangle | `--corner x,y`, `--width`, `--height` |
| `sketch add-arc SKETCH` | Add an arc | `--center x,y`, `--radius`, `--start-angle`, `--end-angle` |
| `sketch constrain SKETCH TYPE` | Add constraint | `--elements 0,1` (indices), `--value` |
| `sketch close SKETCH` | Finalize sketch | positional (sketch name) |
| `sketch list` | List all sketches | -- |
| `sketch get NAME` | Sketch details | positional (name) |
| `sketch validate NAME` | Validate sketch | positional (name) |
| `sketch solve-status NAME` | Constraint solve status | positional (name) |

**Constraint types:** `coincident`, `horizontal`, `vertical`, `parallel`,
`perpendicular`, `equal`, `fixed`, `distance`, `angle`, `radius`, `tangent`,
`symmetric`, `diameter`, `point_on_object`, `distance_x`, `distance_y`

### 4. body — PartDesign features
| Command | Description | Key params |
|---------|-------------|------------|
| `body new` | Create new body | `--name` |
| `body pad BODY SKETCH` | Extrude sketch as pad | `--length`, `--symmetric`, `--reversed` |
| `body pocket BODY SKETCH` | Cut extrusion (pocket) | `--length`, `--symmetric`, `--reversed` |
| `body fillet BODY` | Add fillet feature | `--radius`, `--edges` |
| `body chamfer BODY` | Add chamfer feature | `--size`, `--edges` |
| `body revolution BODY SKETCH` | Revolve sketch | `--angle`, `--axis X|Y|Z` |
| `body groove BODY SKETCH` | Groove (subtractive revolve) | `--angle`, `--axis X|Y|Z` |
| `body hole BODY SKETCH` | Hole feature from sketch | `--diameter`, `--depth`, `--type` |
| `body pattern-linear BODY FEAT` | Linear pattern | `--direction X|Y|Z`, `--count`, `--spacing` |
| `body pattern-polar BODY FEAT` | Polar (circular) pattern | `--axis X|Y|Z`, `--count`, `--angle` |
| `body pattern-mirror BODY FEAT` | Mirror pattern | `--plane XY|XZ|YZ` |
| `body shell BODY` | Shell (hollow) solid | `--thickness`, `--faces` |
| `body draft BODY` | Draft angle on faces | `--angle`, `--faces`, `--plane` |
| `body datum-plane BODY` | Reference plane | `--plane XY|XZ|YZ`, `--offset` |
| `body datum-point BODY` | Reference point | `--position x,y,z` |
| `body datum-line BODY` | Reference line | `--direction X|Y|Z`, `--position x,y,z` |
| `body set-tip BODY` | Set modeling tip position | `--feature NAME` |
| `body remove-feature BODY FEAT` | Remove a feature | positional |
| `body list` | List all bodies | -- |
| `body get NAME` | Body details | positional (name) |

### 5. export — File export
| Command | Description | Key params |
|---------|-------------|------------|
| `export step PATH` | Export STEP | `--overwrite` |
| `export stl PATH` | Export STL | `--tolerance`, `--overwrite` |
| `export obj PATH` | Export OBJ | `--overwrite` |
| `export brep PATH` | Export BREP | `--overwrite` |
| `export dxf PATH` | Export DXF | `--overwrite` |
| `export svg PATH` | Export SVG | `--overwrite` |
| `export pdf PATH` | Export PDF (via TechDraw) | `--overwrite` |
| `export gltf PATH` | Export glTF | `--overwrite` |
| `export 3mf PATH` | Export 3MF | `--overwrite` |
| `export fcstd PATH` | Save as .FCStd | `--overwrite` |
| `export presets` | List export format presets | -- |

### 6. import — File import
| Command | Description | Key params |
|---------|-------------|------------|
| `import auto PATH` | Auto-detect format and import | positional (file path) |
| `import step PATH` | Import STEP | positional |
| `import stl PATH` | Import STL mesh | positional |
| `import obj PATH` | Import OBJ mesh | positional |
| `import dxf PATH` | Import DXF | positional |
| `import brep PATH` | Import BREP | positional |
| `import info PATH` | File info without importing | positional |

### 7. session — Session management
| Command | Description | Key params |
|---------|-------------|------------|
| `session undo` | Undo operations | `--steps N` |
| `session redo` | Redo operations | `--steps N` |
| `session status` | Show session status | -- |
| `session history` | Show operation history | `--limit N` |
| `session snapshot NAME` | Save named snapshot | `--description TEXT` |
| `session restore NAME` | Restore snapshot | positional (name) |

### 8. execute — Raw Python execution
| Command | Description | Key params |
|---------|-------------|------------|
| `execute code CODE` | Execute Python code string | positional (code), `--timeout SEC` |
| `execute file PATH` | Execute .py macro file | positional (path), `--timeout SEC` |

### 9. mesh — Mesh operations
| Command | Description | Key params |
|---------|-------------|------------|
| `mesh import PATH` | Import mesh file | `--name OBJ_NAME` |
| `mesh export PATH` | Export mesh | `--format stl|obj|ply|off`, `--tolerance` |
| `mesh analyze` | Analyze mesh quality | `--name OBJ_NAME` |
| `mesh repair` | Repair mesh defects | `--fix-degenerates`, `--fix-duplicates`, `--fix-normals` |
| `mesh refine` | Refine mesh (subdivide) | `--iterations N` |
| `mesh decimate` | Reduce polygon count | `--reduction 0.0-1.0` |
| `mesh boolean OP` | Mesh boolean: cut/fuse/common | `base`, `tool`, `--name` |
| `mesh section` | Cross-section of mesh | `--plane XY|XZ|YZ`, `--offset` |
| `mesh list` | List all meshes | -- |
| `mesh info NAME` | Mesh details | positional (name) |

### 10. draft — Draft workbench
| Command | Description | Key params |
|---------|-------------|------------|
| `draft line` | Create a line | `--start x,y,z`, `--end x,y,z` |
| `draft wire` | Create polyline/wire | `--points x,y,z;x,y,z;...`, `--closed` |
| `draft circle` | Create a circle | `--center x,y,z`, `--radius` |
| `draft arc` | Create an arc | `--center x,y,z`, `--radius`, `--start-angle`, `--end-angle` |
| `draft rect` | Create a rectangle | `--corner x,y,z`, `--width`, `--height` |
| `draft polygon` | Create regular polygon | `--center x,y,z`, `--radius`, `--sides N` |
| `draft text TEXT` | Create text | `--position x,y,z`, `--size` |
| `draft dimension` | Create dimension | `--start x,y,z`, `--end x,y,z`, `--offset x,y,z` |
| `draft array NAME` | Polar/rectangular array | `--type polar|rectangular`, `--count`, `--rows`, `--cols` |
| `draft offset NAME` | Offset an object | `--distance` |
| `draft move NAME` | Move an object | `--vector x,y,z` |
| `draft rotate NAME` | Rotate an object | `--angle`, `--center x,y,z` |
| `draft scale NAME` | Scale an object | `--factor`, `--center x,y,z` |
| `draft trim NAME` | Trim/extend geometry | `--edge`, `--point x,y,z` |
| `draft list` | List all Draft objects | -- |

### 11. surface — Surface operations
| Command | Description | Key params |
|---------|-------------|------------|
| `surface loft` | Loft through profiles | `--profiles OBJ1;OBJ2;...`, `--solid`, `--ruled` |
| `surface sweep` | Sweep along path | `--profile OBJ`, `--path OBJ`, `--solid` |
| `surface fill` | Fill boundary with surface | `--edges OBJ.Edge1;OBJ.Edge2`, `--degree N` |
| `surface pipe` | Pipe along path | `--path OBJ`, `--radius` |
| `surface offset NAME` | Offset surface | `--distance` |
| `surface thicken NAME` | Thicken to solid | `--thickness`, `--direction both|single` |
| `surface flatten NAME` | Flatten to plane | `--tolerance` |
| `surface sew` | Sew surfaces | `--objects OBJ1;OBJ2;...`, `--tolerance` |
| `surface list` | List surface objects | -- |

### 12. techdraw — Technical drawings
| Command | Description | Key params |
|---------|-------------|------------|
| `techdraw page` | Create drawing page | `--format A4|A3|A2|A1|A0`, `--template PATH` |
| `techdraw view` | Add view to page | `--page PAGE`, `--source OBJ`, `--direction x,y,z`, `--scale` |
| `techdraw dimension` | Add dimension | `--view VIEW`, `--type distance|radius|diameter|angle` |
| `techdraw annotation` | Add text annotation | `--page PAGE`, `--text TEXT`, `--position x,y` |
| `techdraw symbol` | Add symbol to page | `--page PAGE`, `--symbol PATH`, `--position x,y` |
| `techdraw export PAGE` | Export page | `--output PATH`, `--format svg|pdf` |
| `techdraw list` | List all pages | -- |
| `techdraw get NAME` | Page details | positional (name) |

### 13. spreadsheet — Spreadsheet-driven design
| Command | Description | Key params |
|---------|-------------|------------|
| `spreadsheet create` | Create spreadsheet | `--name` |
| `spreadsheet set` | Set cell value | `--sheet NAME`, `--cell A1`, `--value` |
| `spreadsheet get` | Get cell value | `--sheet NAME`, `--cell A1` |
| `spreadsheet formula` | Set cell formula | `--sheet NAME`, `--cell A1`, `--formula` |
| `spreadsheet alias` | Set cell alias | `--sheet NAME`, `--cell A1`, `--alias` |
| `spreadsheet link` | Link cell to property | `--sheet NAME`, `--cell A1`, `--object OBJ`, `--property PROP` |
| `spreadsheet show` | Display contents | `--sheet NAME`, `--range A1:Z20` |
| `spreadsheet list` | List spreadsheets | -- |
| `spreadsheet clear` | Clear cells | `--sheet NAME`, `--cell A1` or `--range A1:C10` |
| `spreadsheet export` | Export to CSV | `--sheet NAME`, `--output PATH` |
| `spreadsheet import` | Import from CSV | `--sheet NAME`, `--input PATH` |

### 14. material — Material management
| Command | Description | Key params |
|---------|-------------|------------|
| `material list` | List materials | `--library NAME` |
| `material show NAME` | Material properties | positional (name) |
| `material assign` | Assign to object | `--object OBJ`, `--material MAT` |
| `material create` | Create custom material | `--name`, `--density`, `--youngs-modulus`, `--poisson-ratio`, `--color` |
| `material edit NAME` | Edit material properties | `--property KEY=VALUE` |
| `material remove NAME` | Remove material | positional (name) |
| `material library` | List material libraries | -- |
| `material export NAME` | Export material card | `--output PATH` |
| `material import PATH` | Import material card | `--name` |

### 15. assembly — Assembly operations
| Command | Description | Key params |
|---------|-------------|------------|
| `assembly create` | Create new assembly | `--name`, `--type a2plus|a4|asm3` |
| `assembly add` | Add part to assembly | `--assembly ASM`, `--object OBJ` |
| `assembly remove` | Remove part from assembly | `--assembly ASM`, `--object OBJ` |
| `assembly constraint` | Add constraint between parts | `--type coincident|parallel|distance|angle|axial|plane`, `--obj1 OBJ`, `--obj2 OBJ` |
| `assembly solve` | Solve constraints | `--assembly ASM` |
| `assembly explode` | Create exploded view | `--factor`, `--direction x|y|z` |
| `assembly animate` | Create animation | `--start`, `--end`, `--steps` |
| `assembly list` | List assembly parts | `--assembly ASM` |
| `assembly ground Ground a part | `--assembly ASM`, `--object OBJ` |
| `assembly show` | Show assembly tree | `--assembly ASM` |

### 16. fem — FEM analysis
| Command | Description | Key params |
|---------|-------------|------------|
| `fem analysis` | Create FEM analysis | `--name` |
| `fem mesh` | Create FEM mesh | `--analysis ANA`, `--object OBJ`, `--max-size`, `--min-size` |
| `fem material` | Assign FEM material | `--analysis ANA`, `--material MAT`, `--object OBJ` |
| `fem constraint` | Add boundary condition | `--analysis ANA`, `--type fixed|force|pressure|displacement|gravity`, `--object OBJ` |
| `fem solve` | Run solver | `--analysis ANA`, `--solver calculix|elmer|z88`, `--timeout SEC` |
| `fem result` | Show results | `--analysis ANA`, `--type stress|displacement|strain|all` |
| `fem list` | List FEM objects | `--analysis ANA` |

### 17. cam — CAM operations
| Command | Description | Key params |
|---------|-------------|------------|
| `cam job` | Create CAM job | `--name`, `--model OBJ`, `--template` |
| `cam tool` | Define cutting tool | `--type endmill|ballmill|drill|...`, `--diameter`, `--length`, `--speed`, `--feed` |
| `cam toolpath` | Generate toolpath | `--job JOB`, `--type profile|pocket|drill|adaptive|...`, `--depth`, `--step-down` |
| `cam postprocess` | Export G-code | `--job JOB`, `--output PATH`, `--post` |
| `cam simulate` | Simulate toolpath | `--job JOB`, `--step` |
| `cam list` | List CAM objects | `--job JOB` |
| `cam show JOB` | Job details | positional (job name) |

---

## Five-Phase Execution Flow

> **MUST follow for all design tasks.** See `docs/EXECUTION_FLOW_TEMPLATE.md` for the complete template.

Every design task MUST go through these 5 phases in order. **Skipping any phase is a failure.**

| Phase | Name | What to do |
|-------|------|-----------|
| 1 | Tool Selection | List all command groups and commands needed for the task |
| 2 | Task Decomposition | Break the task into atomic steps, one CLI command per step |
| 3 | Coordinate & Dependency | For each step: calculate coordinates, identify dependency elements, describe topology |
| 4 | Dependency Validation | Check all dependencies are valid (no dangling refs, no circular deps) |
| 5 | Command Output | Output CLI commands in order with comments |

**Core Rules:**
1. Only use commands from FreeCAD CLI — no unknown commands
2. All elements must have unique names: `{Type}_{Seq}` (e.g., `Box_001`, `Cylinder_001`)
3. Only reference elements already created in previous steps
4. Follow FreeCAD drawing order: base → primitives → boolean → constraints → export
5. Never merge multiple operations into one command
6. Max 10 commands per batch — feedback results before continuing
7. Always use `--json` output format
8. Use `--project` for multi-step session persistence

**Forbidden Rules:**
- ❌ No geometry below Z=0 (default work plane)
- ❌ No boolean operations on non-existent elements
- ❌ No circles without an attachment plane
- ❌ No skipping phases
- ❌ No more than 10 commands at once

---

## Intent-to-Command Mapping

| User Intent | Command(s) |
|-------------|-----------|
| "Create a box" | `fc part add box --name Box --param Length=20 --param Width=15 --param Height=10 --json` |
| "Create a cylinder" | `fc part add cylinder --name Cyl --param Radius=5 --param Height=20 --json` |
| "Create a sphere" | `fc part add sphere --name Sph --param Radius=8 --json` |
| "Create a cone" | `fc part add cone --name Con --param Radius1=10 --param Radius2=3 --param Height=15 --json` |
| "Boolean union (fuse)" | `fc part boolean fuse --base Box --tool Cyl --name Fused --json` |
| "Boolean cut (subtract)" | `fc part boolean cut --base Box --tool Cyl --name Cut --json` |
| "Boolean intersection" | `fc part boolean common --base Box --tool Cyl --name Common --json` |
| "Export to STEP" | `fc export step --output model.step --json` |
| "Export to STL" | `fc export stl --output model.stl --tolerance 0.05 --json` |
| "Save project" | `fc document save --output project.FCStd --json` |
| "Show document info" | `fc document info --json` |
| "Create a sketch on XY plane" | `fc sketch new --name MySketch --plane XY --json` |
| "Add a circle to sketch" | `fc sketch add-circle MySketch --center 0,0 --radius 10 --json` |
| "Pad a sketch" | `fc body pad Body001 Sketch001 --length 20 --json` |
| "Create a pocket" | `fc body pocket Body001 Sketch002 --length 5 --json` |
| "Add a fillet" | `fc part fillet-3d Box --radius 2 --json` |
| "Add a chamfer" | `fc part chamfer-3d Box --size 1.5 --json` |
| "Mirror a part" | `fc part mirror Box --plane XY --name BoxMirrored --json` |
| "Scale a part" | `fc part scale Box 1.5 --json` |
| "Create a hole" | `fc part hole Box --diameter 8 --depth 10 --json` |
| "Undo last operation" | `fc session undo --json` |
| "Create a snapshot" | `fc session snapshot v1.0 --description "Initial design" --json` |
| "Create a TechDraw page" | `fc techdraw page --name Page1 --format A3 --json` |
| "Add a view to page" | `fc techdraw view --page Page1 --source Box --direction 0,0,1 --scale 1.0 --json` |
| "Create a spreadsheet" | `fc spreadsheet create --name Params --json` |
| "Set a parameter" | `fc spreadsheet set --sheet Params --cell A1 --value 100 --json` |
| "Assign material" | `fc material assign --object Box --material Steel --json` |
| "Create FEM analysis" | `fc fem analysis --name StaticAnalysis --json` |
| "Create CAM job" | `fc cam job --name Job1 --json` |
| "Import a STEP file" | `fc import step --path model.step --json` |
| "Execute custom Python" | `fc execute code "print(FreeCAD.ActiveDocument.Name)" --json` |

---

## Multi-Step Workflows

### Workflow 1: Create a part and export
```bash
# Create document, add a box, export to STEP
fc document new --name MyPart --json
fc part add box --name Box --param Length=20 --param Width=15 --param Height=10 --json
fc export step --output model.step --json
fc document save --output model.FCStd --json
```

### Workflow 2: Boolean operations
```bash
# Create base box, add a cylinder hole, subtract, export
fc document new --name Assembly --json
fc part add box --name Base --param Length=30 --param Width=30 --param Height=10 --json
fc part add cylinder --name Hole --param Radius=5 --param Height=10 --json
fc part boolean cut --base Base --tool Hole --name DrilledBase --json
fc export step --output result.step --json
```

### Workflow 3: Sketch-based design with PartDesign
```bash
# Create document, sketch, pad, add fillet, export
fc document new --name PartDesign --json
fc body new --name Body --json
fc sketch new --name Profile --plane XY --json
fc sketch add-circle Profile --center 0,0 --radius 25 --json
fc sketch close Profile --json
fc body pad Body Profile --length 50 --json
fc part fillet-3d Body --radius 3 --json
fc export step --output shaft.step --json
```

### Workflow 4: Technical drawing
```bash
# Create part, then generate a technical drawing
fc document new --name DrawingDoc --json
fc part add box --name Part --param Length=40 --param Width=30 --param Height=20 --json
fc techdraw page --name Page1 --format A3 --json
fc techdraw view --page Page1 --source Part --direction 0,0,1 --scale 0.5 --json
fc techdraw export Page1 --output drawing.pdf --format pdf --json
```

### Workflow 5: Assembly with constraints
```bash
# Create assembly, add parts, constrain, export
fc document new --name Assembly --json
fc assembly create --name MainAssembly --json
fc part add box --name BasePlate --param Length=100 --param Width=100 --param Height=5 --json
fc part add cylinder --name Pillar --param Radius=10 --param Height=50 --json
fc assembly add --assembly MainAssembly --object BasePlate --json
fc assembly add --assembly MainAssembly --object Pillar --json
fc assembly constraint --type coincident --obj1 BasePlate --obj2 Pillar --json
fc export step --output assembly.step --json
```

### Workflow 6: Spreadsheet-driven parametric design
```bash
# Use spreadsheet to drive dimensions
fc document new --name Parametric --json
fc spreadsheet create --name Params --json
fc spreadsheet set --sheet Params --cell A1 --value 100 --json
fc spreadsheet set --sheet Params --cell A2 --value 50 --json
fc part add box --name Box1 --param Length=100 --param Width=50 --param Height=20 --json
fc export step --output parametric.step --json
```

---

## Error Handling

| Error Code | Meaning | Recovery |
|------------|---------|----------|
| `NOT_FOUND` | FreeCAD not found or object not found | Install FreeCAD or set `--freecad-path`; check object name spelling |
| `CREATE_FAILED` | Object/document creation failed | Check parameters, ensure document is open, verify type name |
| `OPEN_FAILED` | File open failed | Check file path exists and is valid .FCStd |
| `SAVE_FAILED` | File save failed | Check output path is writable, ensure document is open |
| `NO_PATH` | No file path specified for save | Provide `--output PATH` argument |
| `EXPORT_FAILED` | Export operation failed | Check output path, ensure objects exist in document |
| `IMPORT_FAILED` | Import operation failed | Check file path, verify format is supported |
| `FILE_EXISTS` | Output file already exists | Use `--overwrite` flag to replace |
| `FILE_NOT_FOUND` | Input file not found | Verify file path is correct |
| `INVALID_NAME` | Invalid name (path traversal or bad chars) | Use alphanumeric + hyphen + underscore only |
| `INVALID_TYPE` | Unknown part/primitive type | Use one of: box, cylinder, sphere, cone, torus, wedge, helix, ellipsoid, spiral |
| `INVALID_FORMAT` | Cannot detect export format | Use `--format svg` or `--format pdf` explicitly |
| `BOOLEAN_FAILED` | Boolean operation failed | Ensure both objects exist and have valid shapes |
| `FILLET_FAILED` | Fillet operation failed | Check radius is valid, object has edges |
| `CHAMFER_FAILED` | Chamfer operation failed | Check size is valid, object has edges |
| `MIRROR_FAILED` | Mirror operation failed | Check object exists and has Shape |
| `SCALE_FAILED` | Scale operation failed | Check factor is valid number |
| `PAD_FAILED` | Pad operation failed | Check body and sketch exist |
| `UNDO_FAILED` | Undo failed | May be nothing to undo |
| `REDO_FAILED` | Redo failed | May be nothing to redo |
| `SNAPSHOT_FAILED` | Snapshot creation failed | Ensure `--project` is set |
| `RESTORE_FAILED` | Snapshot restore failed | Check snapshot name exists |
| `NO_PROJECT` | Operation requires project file | Use `--project PATH` for session persistence |
| `EXEC_FAILED` | Python code execution failed | Check code syntax, verify FreeCAD API calls |
| `MISSING_ARGUMENT` | Required argument not provided | Add `--cell` or `--range` etc. |
| `CONNECTION_ERROR` | Cannot connect to FreeCAD | Start FreeCAD with RPC addon, check `--host` and `--port` |
| `TIMEOUT` | Operation timed out | Increase `--timeout` value or simplify operation |

---

## JSON Output Format

When using `--json`, all commands return structured JSON:

**Success response:**
```json
{
  "status": "ok",
  "operation": "part_add",
  "data": {
    "name": "Box",
    "type": "Part::Box"
  },
  "message": "Created box: Box"
}
```

**Error response:**
```json
{
  "status": "error",
  "operation": "object_create",
  "error": {
    "code": "CREATE_FAILED",
    "message": "Object creation failed: invalid parameters",
    "suggestion": "Check parameters, ensure document is open"
  }
}
```

**Document info response:**
```json
{
  "status": "ok",
  "operation": "document_info",
  "data": {
    "name": "MyPart",
    "label": "MyPart",
    "objects_count": 3,
    "file": "D:/project.FCStd"
  },
  "message": "Document info:"
}
```

---

## Tips for AI Agents

1. **Always use `--json`** for programmatic consumption. This ensures structured, parseable output.

2. **Check `status` field** before proceeding to the next step. If `status` is `"error"`, read the `error.code` and `error.suggestion` fields to determine recovery.

3. **Use `document info --json`** to verify state between operations, especially after creating or opening documents.

4. **For multi-step workflows**, consider using `--project PATH` to enable session persistence, undo/redo, and snapshots.

5. **Default dimensions**: If no `--param` values are provided, primitives use sensible defaults (e.g., box defaults to 10x10x10mm).

6. **Position format**: 3D positions use comma-separated `x,y,z` format (e.g., `10,20,30`). 2D positions use `x,y` format.

7. **Edge selection**: For fillet/chamfer, use `--edges all` for all edges, or comma-separated indices like `--edges 1,3,5`.

8. **Export overwrite**: Most export commands refuse to overwrite existing files unless `--overwrite` is specified.

9. **Headless backend limitations**: Each headless operation spawns a new FreeCADCmd process (~1-3s overhead). For complex multi-step workflows, consider using `--backend rpc` with a running FreeCAD GUI instance.

10. **Execute for advanced operations**: When no built-in command exists for a specific FreeCAD operation, use `execute code` to run arbitrary Python code in the FreeCAD environment.

11. **Snapshot before destructive operations**: Use `session snapshot NAME` before boolean operations or deletions to enable rollback.

12. **Units**: All dimensions are in millimeters (mm) unless otherwise specified.

13. **Five-phase execution**: Always structure design tasks as 5 phases (tool selection → decomposition → coordinates → validation → output). Skip any phase = failure.

14. **Max 10 commands per batch**: For complex tasks, split into batches of ≤10 commands. Feed execution results back before the next batch.

15. **Coordinate calculation**: Always explicitly calculate coordinates for relative positioning (e.g., "center X = 100/2 = 50"). Never guess.

16. **TOOL_SCHEMA.json**: Refer to `docs/TOOL_SCHEMA.json` for the complete machine-readable command schema, error codes, and GUI-to-CLI mappings.

17. **Few-shot examples**: Study `docs/examples/` for validated 5-phase execution examples before tackling new design patterns.

18. **Error auto-learning**: When CLI commands fail, error patterns are automatically tracked. After 3 occurrences of the same pattern, a forbidden rule is generated and persisted to `docs/ERROR_RULES.md`. Check this file periodically to avoid known error patterns. Rules can be exported/imported for cross-session persistence.

19. **Skill system**: 7 分类 skill 文件覆盖全部 17 个命令组。按需加载：创建几何体 → `docs/skills/MODELING.md`，装配/分析 → `docs/skills/ENGINEERING.md`，出图 → `docs/skills/DRAFTING.md`，导入导出 → `docs/skills/DATA_EXCHANGE.md`。加载策略见 `docs/skills/SKILL.md`。
