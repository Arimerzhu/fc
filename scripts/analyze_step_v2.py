# analyze_step_v2.py - inspect hierarchical structure
import os
import sys
import FreeCAD
import Import

BASE = os.path.dirname(os.path.abspath(__file__))
STEP_PATH = os.path.join(BASE, "jinzhi_jigou_sim.step")
OUTPUT_TXT = os.path.join(BASE, "jinzhi_jigou_analysis_v2.txt")

doc = FreeCAD.newDocument("analyze")
Import.insert(STEP_PATH, doc.Name)
doc.recompute()

# recursive walk to find actual Part objects (may be nested in Part/PartDesign Body)
def iter_objects(root, depth=0, lines=None):
    if lines is None:
        lines = []
    children = []
    if hasattr(root, "OutList"):
        children = root.OutList
    if hasattr(root, "Group"):
        children = list(root.Group) or children
    # print node
    label = getattr(root, "Label", "?")
    tname = getattr(root, "TypeId", type(root).__name__)
    bbox_str = "N/A"
    shape_str = "no shape"
    try:
        bb = root.Shape.BoundBox
        bbox_str = f"X[{bb.XMin:.1f},{bb.XMax:.1f}] Y[{bb.YMin:.1f},{bb.YMax:.1f}] Z[{bb.ZMin:.1f},{bb.ZMax:.1f}] W={bb.XLength:.1f} D={bb.YLength:.1f} H={bb.ZLength:.1f}"
        shape_str = f"Solids={len(root.Shape.Solids)}"
    except Exception:
        pass
    indent = "  " * depth
    lines.append(f"{indent}- {label}  ({tname})  {shape_str}")
    if bbox_str != "N/A":
        lines.append(f"{indent}    bbox: {bbox_str}")
    for ch in children:
        iter_objects(ch, depth + 1, lines)
    return lines

lines = []
lines.append(f"jinzhi_jigou_sim.step - object tree")
lines.append(f"total objects in doc.Objects: {len(doc.Objects)}")
lines.append(f"root objects (doc.RootObjects): {len(getattr(doc, 'RootObjects', []))}")
lines.append("")

# try doc.RootObjects first, fallback to all doc.Objects
roots = list(getattr(doc, "RootObjects", [])) or list(doc.Objects)
for root in roots:
    iter_objects(root, 0, lines)
    lines.append("")

with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"OK -> {OUTPUT_TXT}")
