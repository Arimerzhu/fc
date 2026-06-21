# analyze_step_v3.py - recursive walk to find actual shape objects
import os
import sys
import FreeCAD
import Import

BASE = os.path.dirname(os.path.abspath(__file__))
STEP_PATH = os.path.join(BASE, "jinzhi_jigou_sim.step")
OUTPUT_TXT = os.path.join(BASE, "jinzhi_jigou_analysis_v3.txt")
SUMMARY_TXT = os.path.join(BASE, "jinzhi_jigou_summary.txt")

doc = FreeCAD.newDocument("analyze")
Import.insert(STEP_PATH, doc.Name)
doc.recompute()

# collect all parts with shape
shape_parts = []  # list of (path, label, typeid, bbox_str, solids, faces)
no_shape_labels = []

def has_shape(obj):
    try:
        s = obj.Shape
        if s is None:
            return False
        return len(s.Solids) > 0 or len(s.Faces) > 0 or len(s.Vertexes) > 0
    except Exception:
        return False

def get_children(obj):
    # prefer Group for App::Part, otherwise OutList
    try:
        g = list(getattr(obj, "Group", []))
        if g:
            return g
    except Exception:
        pass
    try:
        return list(getattr(obj, "OutList", []))
    except Exception:
        return []

def walk(obj, path, depth=0, lines=None, flat=None):
    if lines is None:
        lines = []
    if flat is None:
        flat = []
    label = getattr(obj, "Label", "?")
    tname = getattr(obj, "TypeId", type(obj).__name__)
    cur_path = path + [label]
    indent = "  " * depth
    is_shape = has_shape(obj)
    bbox_str = ""
    extra = ""
    if is_shape:
        try:
            bb = obj.Shape.BoundBox
            bbox_str = f"X[{bb.XMin:.1f},{bb.XMax:.1f}] Y[{bb.YMin:.1f},{bb.YMax:.1f}] Z[{bb.ZMin:.1f},{bb.ZMax:.1f}]  W={bb.XLength:.1f} D={bb.YLength:.1f} H={bb.ZLength:.1f}"
        except Exception:
            bbox_str = ""
        try:
            extra = f"Solids={len(obj.Shape.Solids)} Faces={len(obj.Shape.Faces)} Edges={len(obj.Shape.Edges)}"
        except Exception:
            extra = ""

    line = f"{indent}- [{tname}] {label}"
    if is_shape:
        line += f"  *{extra}*  ({bbox_str})"
    lines.append(line)
    flat.append((depth, label, tname, is_shape, bbox_str, extra, cur_path))

    for ch in get_children(obj):
        walk(ch, cur_path, depth + 1, lines, flat)
    return lines, flat

all_lines = []
flat = []
roots = list(getattr(doc, "RootObjects", [])) or list(doc.Objects)
# limit to 60 top root objects for readability
count = 0
for root in roots:
    if count >= 200:
        break
    l, f = walk(root, [], 0, [], [])
    all_lines.extend(l)
    flat.extend(f)
    all_lines.append("")
    count += 1

# write detailed tree (truncate to reasonable)
with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
    f.write(f"jinzhi_jigou_sim.step - tree walk\n")
    f.write(f"doc.RootObjects: {len(roots)}, total doc.Objects: {len(doc.Objects)}\n")
    f.write(f"nodes visited: {len(flat)}\n\n")
    # write all, but cap to 8000 lines
    for line in all_lines[:8000]:
        f.write(line + "\n")

# summary: unique labels grouped by App::Part parent
summary_lines = []
summary_lines.append("SUMMARY: all objects with shape")
summary_lines.append("=" * 80)
for depth, label, tname, is_shape, bbox, extra, path in flat:
    if is_shape:
        path_str = " / ".join(path[:-1])
        summary_lines.append(f"[path={path_str}] {label} ({tname})  {extra}")
        summary_lines.append(f"    bbox: {bbox}")
        summary_lines.append("")

# overall bbox of union of shapes
gbb = None
for depth, label, tname, is_shape, bbox, extra, path in flat:
    if not is_shape:
        continue
    try:
        # skip if shape is inside an App::Part that already handles bbox - get directly
        # we need a doc object; search doc.Objects by label (first match)
        for obj in doc.Objects:
            if getattr(obj, "Label", None) == label and has_shape(obj):
                bb = obj.Shape.BoundBox
                if gbb is None:
                    gbb = bb
                else:
                    gbb.add(bb)
                break
    except Exception:
        pass

with open(SUMMARY_TXT, "w", encoding="utf-8") as f:
    f.write(f"total shape-bearing objects: {sum(1 for x in flat if x[3])}\n")
    if gbb is not None:
        f.write(f"overall bbox: X[{gbb.XMin:.1f},{gbb.XMax:.1f}] Y[{gbb.YMin:.1f},{gbb.YMax:.1f}] Z[{gbb.ZMin:.1f},{gbb.ZMax:.1f}]\n")
        f.write(f"overall size: W={gbb.XLength:.1f} D={gbb.YLength:.1f} H={gbb.ZLength:.1f} mm\n")
    f.write("\n")
    for line in summary_lines:
        f.write(line + "\n")

print(f"OK -> {OUTPUT_TXT} / {SUMMARY_TXT}")
