"""
fc_batch_import_step.py - FreeCAD 批量导入 STEP 并注入 GUI 数据

用法:
    "C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" "d:\桌面文件\fc_batch_import_step.py"

功能:
    1. 递归扫描 STEP 文件
    2. 按原目录结构分组导入 FreeCAD
    3. 为不同零件类型分配颜色
    4. 注入 ViewObject 数据（显示模式、颜色、透明度）
    5. 每个装配/子目录保存为一个 FCStd
"""
import os
import sys
import zipfile
from pathlib import Path

# FreeCAD 路径
sys.path.insert(0, r"C:\Program Files\FreeCAD 1.1\bin")
sys.path.insert(0, r"C:\Program Files\FreeCAD 1.1\lib")

import FreeCAD
import FreeCADGui
import Import

# 配置
STEP_ROOT = Path(r"D:\桌面文件\模切机收纸机构\STEP_Output")
FCSTD_ROOT = Path(r"D:\桌面文件\模切机收纸机构\FCStd_Output")

# 颜色配置
COLORS = {
    "frame":    (0.75, 0.75, 0.75),  # 灰色 - 机架/箱体
    "shaft":    (0.20, 0.40, 0.80),  # 蓝色 - 轴/轴承
    "gear":     (0.80, 0.60, 0.20),  # 铜色 - 齿轮
    "arm":      (0.20, 0.70, 0.30),  # 绿色 - 摆杆/连杆
    "plate":    (0.90, 0.50, 0.20),  # 橙色 - 板/盖板
    "paper":    (0.95, 0.90, 0.80),  # 米白 - 纸板/工件
    "default":  (0.60, 0.60, 0.60),  # 默认灰
}


def classify_part(name):
    """根据文件名粗略分类零件类型"""
    n = name.lower()
    if any(k in n for k in ["齿轮", "gear", "大齿轮", "小齿轮"]):
        return "gear"
    if any(k in n for k in ["轴", "shaft", "轴承", "bearing", "键", "销"]):
        return "shaft"
    if any(k in n for k in ["摆杆", "连杆", "摆臂", "arm", "rod", "link"]):
        return "arm"
    if any(k in n for k in ["板", "plate", "盖板", "cover", "端盖", "垫片"]):
        return "plate"
    if any(k in n for k in ["纸板", "paper", "箱座", "箱盖", "机架"]):
        return "frame"
    return "default"


def inject_gui(doc):
    """为文档中所有有 Shape 的对象注入 GUI 数据"""
    for obj in doc.Objects:
        if not hasattr(obj, "Shape"):
            continue

        cls = classify_part(obj.Label)
        color = COLORS.get(cls, COLORS["default"])

        # App 级别的 Visibility
        if hasattr(obj, "Visibility"):
            obj.Visibility = True

        # GUI 级别属性（仅在 FreeCADGui 可用时）
        if FreeCADGui.ActiveDocument and hasattr(obj, "ViewObject") and obj.ViewObject:
            vobj = obj.ViewObject
            if hasattr(vobj, "DisplayMode"):
                vobj.DisplayMode = "Shaded"
            if hasattr(vobj, "ShapeColor"):
                vobj.ShapeColor = color
            if hasattr(vobj, "Transparency"):
                vobj.Transparency = 0
            if hasattr(vobj, "LineWidth"):
                vobj.LineWidth = 1.0


def create_groups(doc, root_path, current_path):
    """根据目录结构创建分组"""
    try:
        rel = current_path.relative_to(root_path)
        parts = [p for p in rel.parts if p != "STEP_Output"]

        if not parts:
            return

        # FreeCAD 的 App::DocumentObjectGroup
        parent = None
        for part in parts:
            group_name = part.replace(" ", "_")[:50]
            existing = doc.getObject(group_name)
            if existing is None:
                group = doc.addObject("App::DocumentObjectGroup", group_name)
                group.Label = part
                if parent:
                    parent.addObject(group)
                parent = group
            else:
                parent = existing

        if parent:
            for obj in doc.Objects:
                if obj.TypeId != "App::DocumentObjectGroup" and obj not in parent.Group:
                    parent.addObject(obj)
    except Exception as e:
        print(f"  分组失败: {e}")


def process_step_file(step_path):
    """处理单个 STEP 文件，保存为 FCStd"""
    rel_path = step_path.relative_to(STEP_ROOT)
    fcstd_path = FCSTD_ROOT / rel_path.with_suffix(".FCStd")
    fcstd_path.parent.mkdir(parents=True, exist_ok=True)

    doc_name = step_path.stem.replace(" ", "_")[:50]
    doc = FreeCAD.newDocument(doc_name)

    print(f"导入: {rel_path}")
    Import.insert(str(step_path), doc.Name)

    # 如果导入后没有对象，可能是空的
    if not doc.Objects:
        print(f"  警告: 没有导入任何对象")
        FreeCAD.closeDocument(doc.Name)
        return False

    # 注入 GUI
    inject_gui(doc)

    # 按目录分组
    create_groups(doc, STEP_ROOT, step_path.parent)

    doc.recompute()
    doc.saveAs(str(fcstd_path))
    FreeCAD.closeDocument(doc.Name)

    print(f"  已保存: {fcstd_path.relative_to(FCSTD_ROOT)}")
    return True


def main():
    FCSTD_ROOT.mkdir(parents=True, exist_ok=True)

    step_files = sorted(STEP_ROOT.rglob("*.step")) + sorted(STEP_ROOT.rglob("*.stp"))
    print(f"找到 {len(step_files)} 个 STEP 文件")

    success = 0
    failed = 0

    for step_file in step_files:
        try:
            if process_step_file(step_file):
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [失败] {step_file}: {e}")
            failed += 1

    print(f"\n完成: 成功 {success}, 失败 {failed}, 总计 {len(step_files)}")


if __name__ == "__main__":
    main()
