"""分析 STEP 文件结构 - 直接使用 FreeCAD Python."""

import FreeCAD
import Import

STEP_PATH = r"d:\桌面文件\fc\工程图输出\进纸机构模拟.STEP"
OUTPUT_TXT = r"d:\桌面文件\fc\工程图输出\进纸机构_结构分析.txt"

doc = FreeCAD.newDocument("analyze")
Import.insert(STEP_PATH, doc.Name)
doc.recompute()

parts = []
for obj in doc.Objects:
    label = obj.Label
    name = obj.Name
    tname = getattr(obj, "TypeId", type(obj).__name__)
    try:
        bb = obj.BoundBox
        bbox = f"{bb.XMin:.1f},{bb.YMin:.1f},{bb.ZMin:.1f} / {bb.XMax:.1f},{bb.YMax:.1f},{bb.ZMax:.1f} (W={bb.XLength:.1f},D={bb.YLength:.1f},H={bb.ZLength:.1f})"
    except Exception:
        bbox = "N/A"
    try:
        shape = obj.Shape
        info = f"Solids={len(shape.Solids)},Faces={len(shape.Faces)},Edges={len(shape.Edges)},V={len(shape.Vertices)}"
    except Exception:
        info = "no shape"
    parts.append((name, label, tname, bbox, info))

try:
    bb = doc.BoundBox
    root_bbox = (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax, bb.XLength, bb.YLength, bb.ZLength)
except Exception as e:
    root_bbox = f"error: {e}"

lines = []
lines.append("进纸机构模拟.STEP  -  结构分析报告")
lines.append("=" * 100)
lines.append(f"文件: {STEP_PATH}")
lines.append(f"对象总数: {len(parts)}")
if isinstance(root_bbox, tuple):
    lines.append(f"整体包围盒: X[{root_bbox[0]:.1f},{root_bbox[3]:.1f}] Y[{root_bbox[1]:.1f},{root_bbox[4]:.1f}] Z[{root_bbox[2]:.1f},{root_bbox[5]:.1f}]")
    lines.append(f"整体尺寸: 宽(W)={root_bbox[6]:.1f} 深(D)={root_bbox[7]:.1f} 高(H)={root_bbox[8]:.1f} mm")
else:
    lines.append(f"包围盒: {root_bbox}")
lines.append("")
lines.append(f"{'序号':<6}{'Name':<30}{'Label':<40}{'Type':<25}")
lines.append(f"{'':<101}尺寸 / 包围盒")
lines.append(f"{'':<101}几何信息")
lines.append("-" * 160)
for i, (name, label, tname, bbox, info) in enumerate(parts, 1):
    lines.append(f"{i:<6}{name[:28]:<30}{label[:38]:<40}{tname[:23]:<25}")
    lines.append(f"{'':<101}{bbox}")
    lines.append(f"{'':<101}{info}")
    lines.append("")

with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"OK: {OUTPUT_TXT}")
print(f"对象数: {len(parts)}")
