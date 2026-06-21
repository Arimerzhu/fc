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

# collect top 100 shape-bearing
shapes = []
for o in doc.Objects:
    try:
        s = o.Shape
        if s is not None and (len(s.Solids) > 0 or len(s.Faces) > 0):
            shapes.append(s.copy())
            if len(shapes) >= 120:
                break
    except Exception:
        pass
print(f"shapes: {len(shapes)}", flush=True)

# fuse
try:
    fused = shapes[0]
    for i, s in enumerate(shapes[1:], 1):
        fused = fused.fuse(s)
        if i % 20 == 0:
            print(f"  fuse {i}/{len(shapes)-1}", flush=True)
except Exception as e:
    print(f"fuse failed {e}, try compound", flush=True)
    fused = Part.makeCompound(shapes)
obj = doc.addObject("Part::Feature", "compound")
obj.Shape = fused
doc.recompute()
bb = obj.Shape.BoundBox
print(f"size: {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f}", flush=True)

# page
page = doc.addObject("TechDraw::DrawPage", "Page")
tpl = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
tpl.Template = "C:/Program Files/FreeCAD 1.1/data/Mod/TechDraw/Templates/A0_Landscape_blank.svg"
page.Template = tpl
doc.recompute()
print("page OK", flush=True)

v = doc.addObject("TechDraw::DrawViewPart", "View_Front")
v.Source = [obj]
v.Direction = FreeCAD.Vector(0,0,1)
v.X = 40.0; v.Y = 180.0; v.Scale = 1.5
page.addView(v)
doc.recompute()
print("Front view added", flush=True)

vt = doc.addObject("TechDraw::DrawViewPart", "View_Top")
vt.Source = [obj]; vt.Direction = FreeCAD.Vector(0,-1,0)
vt.X = 40.0; vt.Y = 60.0; vt.Scale = 1.5
page.addView(vt); doc.recompute()
print("Top view added", flush=True)

vl = doc.addObject("TechDraw::DrawViewPart", "View_Left")
vl.Source = [obj]; vl.Direction = FreeCAD.Vector(-1,0,0)
vl.X = 200.0; vl.Y = 180.0; vl.Scale = 1.5
page.addView(vl); doc.recompute()
print("Left view added", flush=True)

vi = doc.addObject("TechDraw::DrawViewPart", "View_ISO")
vi.Source = [obj]; vi.Direction = FreeCAD.Vector(1,-1,1)
vi.X = 420.0; vi.Y = 100.0; vi.Scale = 2.0
page.addView(vi); doc.recompute()
print("Isometric view added", flush=True)

out = os.path.join(BASE, "jinzhi_assembly.FCStd")
doc.saveAs(out)
print(f"saved FCStd -> {out}", flush=True)

# SVG
out_svg = os.path.join(BASE, "jinzhi_assembly.svg")
try:
    data = page.exportSVG()
    with open(out_svg, "wb") as f:
        f.write(data)
    print(f"SVG -> {out_svg}", flush=True)
except Exception as e:
    print(f"SVG failed: {e}", flush=True)

# DXF per view
for vv in [v, vt, vl, vi]:
    p = os.path.join(BASE, f"view_{vv.Name}.dxf")
    try:
        TechDraw.writeDXFFile(vv, p)
        print(f"DXF({vv.Label}) -> {p}", flush=True)
    except Exception as e:
        print(f"DXF failed: {e}", flush=True)
        try:
            TechDraw.exportPagesAsDXF([page], p)
            print(f"page DXF -> {p}", flush=True)
        except Exception as e2:
            print(f"page DXF also failed: {e2}", flush=True)

pdxf = os.path.join(BASE, "jinzhi_assembly_A0.dxf")
try:
    TechDraw.exportPagesAsDXF([page], pdxf)
    print(f"full page DXF -> {pdxf}", flush=True)
except Exception as e:
    print(f"page DXF failed: {e}", flush=True)

FreeCAD.closeDocument(doc.Name)
print(f"DONE in {time.time()-t0:.1f}s", flush=True)
