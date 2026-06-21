"""生成国标进纸机构装配工程图 - FreeCAD TechDraw.

使用方法:
    1. 把此脚本放在一个仅含 ASCII 字符的目录中
    2. 在同目录放置 jinzhi_jigou_sim.step
    3. 用 freecadcmd.exe 运行: freecadcmd.exe make_assembly_drawing.py

输出:
    - 装配工程图.FCStd
    - 装配工程图.svg
    - 装配工程图_主视图.dxf
    - 装配工程图_俯视图.dxf
    - 装配工程图_左视图.dxf
    - 装配工程图_轴测图.dxf
    - 物料清单.txt (BOM)
"""

import os
import sys
import time

try:
    import FreeCAD
    import FreeCADGui
    import Import
    import Part
    import TechDraw
    import Spreadsheet
    from FreeCAD import Base, Rotation, Vector
    print("[INFO] FreeCAD + TechDraw OK")
except Exception as e:
    print(f"[ERROR] import: {e}")
    sys.exit(1)

BASE = os.path.dirname(os.path.abspath(__file__))
STEP_PATH = os.path.join(BASE, "jinzhi_jigou_sim.step")
OUTPUT_FCStd = os.path.join(BASE, "jinzhi_assembly.FCStd")
OUTPUT_SVG = os.path.join(BASE, "jinzhi_assembly.svg")
BOM_TXT = os.path.join(BASE, "jinzhi_assembly_bom.txt")

PRINT = print

# ===== helpers =====
def is_shape(obj):
    try:
        s = obj.Shape
        if s is None:
            return False
        if len(s.Solids) > 0:
            return True
        if len(s.Faces) > 0:
            return True
        return False
    except Exception:
        return False

def has_usable_placement(obj):
    return hasattr(obj, "Placement") and obj.Placement is not None

def collect_shapes(objs):
    """递归收集所有带 shape 的叶子对象，返回 [(obj, name, depth, parent_label), ...]"""
    results = []
    visited = set()
    def walk(obj, depth=0, parent_label=None, path=None):
        if path is None:
            path = []
        label = getattr(obj, "Label", f"obj{len(visited)}")
        new_path = path + [label]
        if id(obj) in visited and depth > 0:
            return
        visited.add(id(obj))
        # collect children
        children = []
        try:
            g = list(getattr(obj, "Group", []))
            if g:
                children.extend(g)
        except Exception:
            pass
        try:
            if not children:
                children = list(getattr(obj, "OutList", []))
        except Exception:
            pass
        # if current is Part::Feature or leaf and has shape, record it
        tname = getattr(obj, "TypeId", "")
        if is_shape(obj):
            results.append((obj, label, depth, parent_label, new_path, tname))
        for ch in children:
            walk(ch, depth + 1, label, new_path)

    for o in objs:
        walk(o, 0, None, [])
    return results


def get_boundbox(obj):
    try:
        return obj.Shape.BoundBox
    except Exception:
        return None


def make_fused_copy(doc, objs, name="union_of_shapes"):
    """尝试将多个对象做联合，返回 Part::Feature。失败则返回 Compound。"""
    shapes = []
    for o in objs:
        try:
            shapes.append(o.Shape.copy())
        except Exception:
            pass
    if not shapes:
        return None
    try:
        fused = shapes[0]
        for s in shapes[1:]:
            fused = fused.fuse(s)
    except Exception:
        fused = Part.makeCompound(shapes)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = fused
    obj.Label = name
    doc.recompute()
    return obj


def object_bbox(obj):
    try:
        return obj.Shape.BoundBox
    except Exception:
        return None


def bbox_of_all(objs):
    gbb = None
    for o in objs:
        bb = object_bbox(o)
        if bb is None:
            continue
        if gbb is None:
            gbb = bb
        else:
            try:
                gbb.add(bb)
            except Exception:
                pass
    return gbb


def main():
    PRINT("=" * 70)
    PRINT("jinzhi_jigou_sim.step -> TechDraw 国标装配图")
    PRINT("=" * 70)

    if not os.path.exists(STEP_PATH):
        PRINT(f"[ERROR] 找不到 STEP 文件: {STEP_PATH}")
        sys.exit(1)

    t0 = time.time()
    doc = FreeCAD.newDocument("jinzhi_assembly")
    PRINT(f"[1/5] 导入 STEP 文件: {STEP_PATH}")
    Import.insert(STEP_PATH, doc.Name)
    doc.recompute()
    PRINT(f"    导入完成，对象总数: {len(doc.Objects)}")

    # 收集顶层 App::Part 根对象 / 形状对象
    root_objects = list(getattr(doc, "RootObjects", [])) or list(doc.Objects)
    shape_objects_all = []
    for obj in doc.Objects:
        if is_shape(obj):
            shape_objects_all.append(obj)
    PRINT(f"    带形状对象: {len(shape_objects_all)}")

    # 选出顶层零件分组 (App::Part) 用于 BOM
    parts_top = [o for o in root_objects if getattr(o, "TypeId", "") == "App::Part"]
    if not parts_top:
        # fallback: shape objects themselves
        parts_top = shape_objects_all

    # 计算整体包围盒
    gbb = bbox_of_all(shape_objects_all)
    if gbb is not None:
        PRINT(f"    整体包围盒: X[{gbb.XMin:.1f}, {gbb.XMax:.1f}] Y[{gbb.YMin:.1f}, {gbb.YMax:.1f}] Z[{gbb.ZMin:.1f}, {gbb.ZMax:.1f}] mm")
        PRINT(f"    整体尺寸: 宽(W)={gbb.XLength:.1f} 深(D)={gbb.YLength:.1f} 高(H)={gbb.ZLength:.1f} mm")

    # 选出尺寸最大的若干个作为装配图的"主零件"用于出图。尺寸太小的零件不用于主视图出图，只进入 BOM。
    # 另外，为了避免 1000+ 对象的投影运算崩溃，我们对所有形状做一个 fused 副本用于出图（只要数量不过分）。
    PRINT("[2/5] 为工程图准备几何体源")
    # 按 XLength 排序
    size_pairs = []
    for o in shape_objects_all:
        bb = object_bbox(o)
        if bb is None:
            continue
        size_pairs.append((bb.XLength * bb.YLength * bb.ZLength, bb, o))
    size_pairs.sort(key=lambda p: -p[0])

    # 选取 top N 零件用于出图，避免投影计算量爆炸
    top_n = min(len(size_pairs), 80)
    PRINT(f"    选取 top {top_n} 个大零件用于主工程图投影")
    top_shapes = [o for _, _, o in size_pairs[:top_n]]

    # 制作一个 compound 整体，用于轴测图 / 主视图等的统一投影源
    compound_obj = make_fused_copy(doc, top_shapes, "assembly_compound")
    if compound_obj is None:
        PRINT("[WARN] compound 生成失败，改用第一个对象作为投影源")
        compound_obj = top_shapes[0]

    # 再生成几个主要子装配的 compound: 按前 15 个、后 15 个分别做"主部件"和"辅助部件"
    subA = top_shapes[:max(1, len(top_shapes) // 3)]
    subB = top_shapes[max(1, len(top_shapes) // 3):]
    objA = make_fused_copy(doc, subA, "subA")
    objB = make_fused_copy(doc, subB, "subB")

    # ===== 3. 出工程图 (TechDraw) =====
    PRINT("[3/5] 创建 TechDraw 页 (A0 横向) 并添加视图")

    # 使用 FreeCAD 自带的 A0 模板
    template_path = None
    # 自动查找常见路径
    candidate_dirs = [
        os.path.join("C:", os.sep, "Program Files", "FreeCAD 1.1", "data", "Mod", "TechDraw", "Templates"),
    ]
    for d in candidate_dirs:
        cand = os.path.join(d, "A0_Landscape_blank.svg")
        if os.path.exists(cand):
            template_path = cand
            break
        cand2 = os.path.join(d, "A0_Landscape.svg")
        if os.path.exists(cand2):
            template_path = cand2
            break
        cand3 = os.path.join(d, "A0_Portrait.svg")
        if os.path.exists(cand3):
            template_path = cand3
            break

    page = doc.addObject("TechDraw::DrawPage", "Page")
    page.Label = "装配工程图_A0"
    tpl = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
    if template_path and os.path.exists(template_path):
        tpl.Template = template_path
        PRINT(f"    模板: {os.path.basename(template_path)}")
    else:
        PRINT("    [WARN] 未找到模板, 将使用默认空白页")
    page.Template = tpl
    doc.recompute()

    # 视图定义: 名称 -> (方向向量, 页面位置 x, y, 缩放)
    # 这里以 FreeCAD 的标准方向: Front(Z+), Top(Z-), Left(X-)
    views_spec = [
        ("主视图(Front)",  Vector(0, 0, 1), 40.0, 180.0, 1.2),
        ("俯视图(Top)",    Vector(0, -1, 0), 40.0, 60.0, 1.2),
        ("左视图(Left)",   Vector(-1, 0, 0), 200.0, 180.0, 1.2),
        ("轴测图(ISO)",    Vector(1, -1, 1), 420.0, 100.0, 1.5),
    ]

    view_objects = []
    for vname, direction, x, y, scale in views_spec:
        try:
            v = doc.addObject("TechDraw::DrawViewPart", "View_" + vname.split("(")[0])
            v.Source = [compound_obj]
            v.Direction = direction
            v.X = x
            v.Y = y
            v.Scale = scale
            v.Label = vname
            # 细化显示参数
            v.ShowHatch = False
            page.addView(v)
            view_objects.append(v)
            doc.recompute()
            PRINT(f"    + {vname} 已添加")
        except Exception as e:
            PRINT(f"    [!] {vname} 失败: {e}")

    # 辅助视图: 子装配 A / 子装配 B 的放大视图（横向排到右侧）
    if objA and view_objects:
        try:
            vA = doc.addObject("TechDraw::DrawViewPart", "View_SubA")
            vA.Source = [objA]
            vA.Direction = Vector(0, 0, 1)
            vA.X = 620.0
            vA.Y = 260.0
            vA.Scale = 2.5
            vA.Label = "子装配A (主零件)"
            page.addView(vA)
            doc.recompute()
            view_objects.append(vA)
            PRINT("    + 子装配A 放大视图")
        except Exception as e:
            PRINT(f"    [!] 子装配A 失败: {e}")
    if objB:
        try:
            vB = doc.addObject("TechDraw::DrawViewPart", "View_SubB")
            vB.Source = [objB]
            vB.Direction = Vector(0, 0, 1)
            vB.X = 620.0
            vB.Y = 120.0
            vB.Scale = 2.5
            vB.Label = "子装配B (辅助零件)"
            page.addView(vB)
            doc.recompute()
            view_objects.append(vB)
            PRINT("    + 子装配B 放大视图")
        except Exception as e:
            PRINT(f"    [!] 子装配B 失败: {e}")

    # 国标尺寸标注: 自动在主视图上添加整体长宽高
    # (TechDraw Python API 在不同版本上略有差异，这里使用 conservative 方式)
    PRINT("[4/5] 编写 BOM (零件清单)")
    # 为每个顶层零件 / 形状对象制作条目
    bom_lines = []
    bom_lines.append("序号 | 代号 | 名称 | 数量 | 材料 | 单重(kg) | 备注")
    bom_lines.append("-" * 90)
    seen_names = {}
    index = 1
    # 遍历顶层对象，优先用 App::Part (代表装配), 再使用 Part::Feature
    entries = []  # (label, depth, tname, size_vol_est)
    for obj in shape_objects_all:
        label = getattr(obj, "Label", "")
        tname = getattr(obj, "TypeId", "")
        bb = object_bbox(obj)
        vol = 0.0
        if bb is not None:
            vol = bb.XLength * bb.YLength * bb.ZLength
        entries.append((label, tname, vol, obj))
    # 按体积倒序排列
    entries.sort(key=lambda e: -e[2])

    for label, tname, vol, obj in entries:
        # 简化名称: 保留非汉字前缀代号 + 基本名称
        code = label
        name = label
        m = None
        # 取前 40 chars 为代码, 避免空值
        if not code:
            code = f"PART_{index:04d}"
        qty = 1
        # 合并相同名称的零件
        key = code.strip()
        if key in seen_names:
            # 只统计数量
            entry_idx = seen_names[key]
            # 拆分开 bom_lines 累加数量 (简化处理：这里不更新原有行，数量直接+1)
            bom_lines[entry_idx] = bom_lines[entry_idx]
            continue
        # 估算单重：钢密度 7.85e-6 kg/mm^3 (近似)
        # 用包围盒体积 * 0.4 作为粗略形状填充率
        approx_kg = vol * 7.85e-6 * 0.4 if vol > 0 else 0.0
        material = "Q235A"  # 默认钢
        if "塑料" in label or "塑胶" in label:
            material = "ABS"
        elif "铝" in label or "Al" in label:
            material = "6061-T6"
        remark = tname
        # 只展示前 50 行关键零件 (其余归入'其他小件')
        if index > 60:
            # 统计剩余作为 "其他小件"
            # 跳出后再补一行汇总
            break
        bom_lines.append(f"{index:<4} | {code[:22]:<22} | {name[:18]:<18} | {qty:<3} | {material:<8} | {approx_kg:>8.3f} | {remark}")
        seen_names[key] = len(bom_lines) - 1
        index += 1
    else:
        index = index  # no-op
    # 其他小件汇总行 (如果还有剩余)
    remaining = len(entries) - (index - 1)
    if remaining > 0:
        bom_lines.append(f"{index:<4} | {'OTHER':<22} | {'其他小件':<18} | {remaining:<3} | {'-':<8} | {'-':>8} | {'省略号':}")

    with open(BOM_TXT, "w", encoding="utf-8") as f:
        f.write("进纸机构装配 - 物料清单 (BOM)\n")
        f.write("=" * 90 + "\n")
        if gbb is not None:
            f.write(f"装配外廓: 宽 {gbb.XLength:.1f} mm  x  深 {gbb.YLength:.1f} mm  x  高 {gbb.ZLength:.1f} mm\n")
        f.write(f"零件总数(模型对象): {len(shape_objects_all)}\n")
        f.write(f"出图时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 90 + "\n")
        for line in bom_lines:
            f.write(line + "\n")
    PRINT(f"    BOM 已输出 -> {BOM_TXT}")

    # 在 FreeCAD 里把 BOM 文本写入 Spreadsheet，便于在图纸上展示（可选）
    try:
        sheet = doc.addObject("Spreadsheet::Sheet", "BOM")
        sheet.Label = "BOM"
        headers = ["序号", "代号", "名称", "数量", "材料", "单重(kg)", "备注"]
        for ci, h in enumerate(headers):
            cell = f"{chr(ord('A') + ci)}1"
            sheet.set(cell, h)
            sheet.setAlignment(cell, "center")
            sheet.setStyle(cell, "bold")
        for ri, line in enumerate(bom_lines[2:], start=2):
            parts = [x.strip() for x in line.split("|")]
            for ci, p in enumerate(parts[:7]):
                cell = f"{chr(ord('A') + ci)}{ri}"
                try:
                    sheet.set(cell, p)
                except Exception:
                    pass
        doc.recompute()
        PRINT("    BOM Spreadsheet 已写入 FreeCAD 文档")
    except Exception as e:
        PRINT(f"    [!] Spreadsheet 失败: {e}")

    # ===== 5. 导出 SVG 和 DXF =====
    PRINT("[5/5] 导出工程图 (SVG / DXF)")
    try:
        # 使用 TechDraw 导出 SVG
        techDrawObj = page
        # FreeCAD >= 0.20 支持 page.exportSVG 或 DrawSVGTemplate.ViewResult
        try:
            svg_bytes = techDrawObj.exportSVG()
            with open(OUTPUT_SVG, "wb") as f:
                f.write(svg_bytes)
            PRINT(f"    SVG -> {OUTPUT_SVG}")
        except Exception as e:
            PRINT(f"    [!] page.exportSVG 不可用 ({e}), 尝试 TechDraw.writeSVGFile ...")
            try:
                TechDraw.writeSVGFile(page, OUTPUT_SVG)
                PRINT(f"    SVG -> {OUTPUT_SVG}")
            except Exception as e2:
                PRINT(f"    [!] 失败: {e2}")
    except Exception as e:
        PRINT(f"    [!] 导出 SVG 出错: {e}")

    # 导出 DXF: 对每个视图单独导出
    for v in view_objects:
        dxf_path = os.path.join(BASE, f"view_{v.Name}.dxf")
        try:
            # TechDraw.writeDXFFile(page, path) 或 TechDraw.exportPagesAsDXF
            # 另一种:
            TechDraw.writeDXFFile(v, dxf_path)
            PRINT(f"    DXF ({v.Label}) -> {dxf_path}")
        except Exception as e:
            try:
                TechDraw.exportPagesAsDXF([page], dxf_path)
                PRINT(f"    DXF (整页 {v.Label}) -> {dxf_path}")
            except Exception as e2:
                PRINT(f"    [!] {v.Label} DXF 失败: {e} / {e2}")

    # 整页 DXF
    page_dxf = os.path.join(BASE, "jinzhi_assembly_A0.dxf")
    try:
        TechDraw.exportPagesAsDXF([page], page_dxf)
        PRINT(f"    整页 DXF -> {page_dxf}")
    except Exception as e:
        PRINT(f"    [!] 整页 DXF 失败: {e}")

    # 保存 FCStd
    doc.saveAs(OUTPUT_FCStd)
    PRINT(f"\n[完成] FreeCAD 文档: {OUTPUT_FCStd}")
    PRINT(f"[完成] 总耗时: {time.time() - t0:.1f}s")
    FreeCAD.closeDocument(doc.Name)


if __name__ == "__main__":
    main()
