import os, sys, time
try:
    import FreeCAD, Import, Part, TechDraw
    print("ok imports", flush=True)
except Exception as e:
    print(f"fail: {e}", flush=True); sys.exit(1)

BASE = os.path.dirname(os.path.abspath(__file__))
STEP = os.path.join(BASE, "jinzhi_jigou_sim.step")
print(f"BASE={BASE}", flush=True)
print(f"STEP exists: {os.path.exists(STEP)}", flush=True)

t0 = time.time()
doc = FreeCAD.newDocument("d")
Import.insert(STEP, doc.Name)
doc.recompute()
print(f"objects: {len(doc.Objects)}", flush=True)

# collect top N shape-bearing by bbox size (largest first)
shape_list = []  # (area_approx, obj)
for o in doc.Objects:
    try:
        s = o.Shape
        if s is None or s.isNull():
            continue
        # must have some geometry
        if not hasattr(s, "Faces") or len(s.Faces) == 0:
            continue
        bb = s.BoundBox
        if bb.XLength < 0.01 or bb.YLength < 0.01 or bb.ZLength < 0.01:
            continue
        if bb.XLength > 1e6 or bb.YLength > 1e6 or bb.ZLength > 1e6:
            continue
        vol_est = bb.XLength * bb.YLength * bb.ZLength
        shape_list.append((vol_est, o))
    except Exception:
        continue

# sort descending by volume estimate
shape_list.sort(key=lambda x: -x[0])
print(f"candidates: {len(shape_list)}", flush=True)

# take top N largest (to avoid performance issues)
N = min(len(shape_list), 80)
print(f"taking top {N} for projection", flush=True)
print(f"top 5 volumes:", flush=True)
for i in range(min(5, N)):
    vol, o = shape_list[i]
    bb = o.Shape.BoundBox
    print(f"  [{i}] {getattr(o,'Label','?')[:40]} size={bb.XLength:.1f}x{bb.YLength:.1f}x{bb.ZLength:.1f}", flush=True)

# fuse top N shapes - use progressive fusion
top_shapes = [o.Shape.copy() for _, o in shape_list[:N]]
print(f"begin fuse of {len(top_shapes)} shapes", flush=True)
try:
    fused = top_shapes[0]
    for i, s in enumerate(top_shapes[1:], 1):
        fused = fused.fuse(s)
        if i % 10 == 0 or i == len(top_shapes) - 1:
            print(f"  fuse progress: {i}/{len(top_shapes)-1}", flush=True)
except Exception as e:
    print(f"fuse failed ({e}); try compound", flush=True)
    try:
        fused = Part.makeCompound(top_shapes)
    except Exception as e2:
        print(f"compound also failed ({e2}); using just top shape", flush=True)
        fused = top_shapes[0]

obj = doc.addObject("Part::Feature", "assembly_compound")
obj.Shape = fused
doc.recompute()
try:
    bb = obj.Shape.BoundBox
    print(f"assembly size: {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f}", flush=True)
except Exception as e:
    print(f"bbox failed: {e}", flush=True)

# TechDraw page
page = doc.addObject("TechDraw::DrawPage", "Page")
tpl = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
tpl.Template = "C:/Program Files/FreeCAD 1.1/data/Mod/TechDraw/Templates/A0_Landscape_blank.svg"
page.Template = tpl
doc.recompute()
print("page OK", flush=True)

views_spec = [
    ("View_Front", FreeCAD.Vector(0, 0, 1), 40.0, 180.0, 1.2, "主视图"),
    ("View_Top",   FreeCAD.Vector(0, -1, 0), 40.0, 60.0, 1.2, "俯视图"),
    ("View_Left",  FreeCAD.Vector(-1, 0, 0), 200.0, 180.0, 1.2, "左视图"),
    ("View_ISO",   FreeCAD.Vector(1, -1, 1), 420.0, 100.0, 1.5, "轴测图"),
]

view_objects = []
for name, direction, x, y, scale, label in views_spec:
    try:
        v = doc.addObject("TechDraw::DrawViewPart", name)
        v.Source = [obj]
        v.Direction = direction
        v.X = x; v.Y = y; v.Scale = scale
        v.Label = label
        page.addView(v)
        doc.recompute()
        view_objects.append(v)
        print(f"added view: {label}", flush=True)
    except Exception as e:
        print(f"view {label} failed: {e}", flush=True)

# save FCStd
out = os.path.join(BASE, "jinzhi_assembly.FCStd")
doc.saveAs(out)
print(f"saved FCStd -> {out}", flush=True)

# export SVG
out_svg = os.path.join(BASE, "jinzhi_assembly.svg")
try:
    data = page.exportSVG()
    with open(out_svg, "wb") as f:
        f.write(data)
    print(f"SVG -> {out_svg}", flush=True)
except Exception as e:
    print(f"SVG failed: {e}", flush=True)

# export DXF per view
for vv in view_objects:
    p = os.path.join(BASE, f"{vv.Name}.dxf")
    try:
        TechDraw.writeDXFFile(vv, p)
        print(f"DXF({vv.Label}) -> {p}", flush=True)
    except Exception as e:
        print(f"writeDXFFile failed ({vv.Name}): {e}", flush=True)
        try:
            TechDraw.exportPagesAsDXF([page], p)
            print(f"page DXF -> {p}", flush=True)
        except Exception as e2:
            print(f"page DXF also failed: {e2}", flush=True)

# full page DXF
pdxf = os.path.join(BASE, "jinzhi_assembly_A0.dxf")
try:
    TechDraw.exportPagesAsDXF([page], pdxf)
    print(f"full page DXF -> {pdxf}", flush=True)
except Exception as e:
    print(f"page DXF failed: {e}", flush=True)

# write BOM
bom_txt = os.path.join(BASE, "jinzhi_assembly_bom.txt")
try:
    lines = []
    lines.append("进纸机构装配 - 物料清单 (BOM)")
    lines.append("=" * 70)
    if bb is not None:
        lines.append(f"装配外廓: 宽 {bb.XLength:.1f} mm x 深 {bb.YLength:.1f} mm x 高 {bb.ZLength:.1f} mm")
    lines.append(f"总零件对象数(几何有效): {len(shape_list)}")
    lines.append(f"出图时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"{'序号':<6}{'代号/名称':<45}{'尺寸 (宽x深x高 mm)':<35}")
    lines.append("-" * 100)
    # include up to 80 items, by volume desc
    for i, (vol, o) in enumerate(shape_list[:80], 1):
        sbb = o.Shape.BoundBox
        label = getattr(o, "Label", f"part{i}")
        # strip unicode control chars that might appear
        lines.append(f"{i:<6}{label[:44]:<45}{sbb.XLength:<11.1f} x {sbb.YLength:<11.1f} x {sbb.ZLength:<11.1f}")
    if len(shape_list) > 80:
        lines.append(f"... 省略其余 {len(shape_list)-80} 个零件")
    with open(bom_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"BOM -> {bom_txt}", flush=True)
except Exception as e:
    print(f"BOM failed: {e}", flush=True)

FreeCAD.closeDocument(doc.Name)
print(f"DONE in {time.time()-t0:.1f}s", flush=True)
