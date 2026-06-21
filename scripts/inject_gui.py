"""
inject_gui.py - 为 PaperFeeder.FCStd 注入 GUI 数据 (GuiDocument.xml)

原理:
  FCStd 是 ZIP 压缩包, headless 模式 (freecadcmd) 不生成 GuiDocument.xml。
  本脚本直接构造 GuiDocument.xml 并写入 ZIP, 使 FreeCAD GUI 打开时能显示
  颜色/可见性/透明度等 ViewProvider 属性。

对象分类 (28 个):
  - 机架 (灰色): BaseFrame, Pillar_1-4, TopBeam
  - 传动 (蓝轴/灰轴承座): Camshaft, Bearing_L_Cut, Bearing_R_Cut
  - 凸轮 (红色, 透明 20): Cam
  - 摆杆 (绿色, 透明 15): SwingArm_Final
  - 执行 (绿色/橙色): PivotShaft, CamRoller, ExtensionRod, TapperPlate
  - 工件 (米白, 透明 40): PaperBoard
  - 隐藏工具: Bearing_L/R, BearingLHole/RHole, CamBase, CamLobe, CamShaftHole,
              CamFuse, SwingArm, PivotHole, RollerPinHole, SwingArm_Cut1
"""
import zipfile
import shutil
import os

# 源文件 (headless 生成, 无 GUI 数据) 和目标文件
SRC_FCSTD = r"D:\Temp\PaperFeeder.FCStd"
DST_FCSTD = r"d:\桌面文件\PaperFeeder.FCStd"

# 颜色定义 (R, G, B) 0-255
COLORS = {
    "frame":   (191, 191, 191),  # 灰色 - 机架
    "shaft":   (51, 102, 204),   # 蓝色 - 凸轮轴
    "bearing": (191, 191, 191),  # 灰色 - 轴承座
    "cam":     (204, 51, 51),    # 红色 - 凸轮
    "arm":     (51, 178, 76),    # 绿色 - 摆杆
    "exec":    (51, 178, 76),    # 绿色 - 执行机构
    "tapper":  (204, 128, 51),   # 橙色 - 拍纸头
    "paper":   (245, 235, 220),  # 米白 - 纸板
    "tool":    (128, 128, 128),  # 深灰 - 辅助工具 (隐藏)
}


def color_to_freecad(r, g, b, a=0):
    """RGB 转 FreeCAD 颜色编码: (r<<24)|(g<<16)|(b<<8)|a"""
    return (r << 24) | (g << 16) | (b << 8) | a


# 对象配置: (名称, 颜色键, 可见性, 透明度0-100)
OBJECTS = [
    # 机架 (灰色, 可见)
    ("BaseFrame",      "frame",   True,  0),
    ("Pillar_1",       "frame",   True,  0),
    ("Pillar_2",       "frame",   True,  0),
    ("Pillar_3",       "frame",   True,  0),
    ("Pillar_4",       "frame",   True,  0),
    ("TopBeam",        "frame",   True,  0),
    # 传动系统
    ("Camshaft",       "shaft",   True,  0),
    ("Bearing_L",      "tool",    False, 0),  # 隐藏 - 被 _Cut 替代
    ("BearingLHole",   "tool",    False, 0),  # 隐藏 - 切割工具
    ("Bearing_L_Cut",  "bearing", True,  0),
    ("Bearing_R",      "tool",    False, 0),  # 隐藏 - 被 _Cut 替代
    ("BearingRHole",   "tool",    False, 0),  # 隐藏 - 切割工具
    ("Bearing_R_Cut",  "bearing", True,  0),
    # 凸轮 (红色, 可见, 透明度 20)
    ("CamBase",        "tool",    False, 0),  # 隐藏 - fuse 源
    ("CamLobe",        "tool",    False, 0),  # 隐藏 - fuse 源
    ("CamShaftHole",   "tool",    False, 0),  # 隐藏 - 切割工具
    ("CamFuse",        "tool",    False, 0),  # 隐藏 - fuse 中间结果
    ("Cam",            "cam",     True,  20),
    # 摆杆 (绿色, 可见, 透明度 15)
    ("SwingArm",       "tool",    False, 0),  # 隐藏 - 被 _Final 替代
    ("PivotHole",      "tool",    False, 0),  # 隐藏 - 切割工具
    ("RollerPinHole",  "tool",    False, 0),  # 隐藏 - 切割工具
    ("SwingArm_Cut1",  "tool",    False, 0),  # 隐藏 - 中间结果
    ("SwingArm_Final", "arm",     True,  15),
    # 执行机构
    ("PivotShaft",     "exec",    True,  0),
    ("CamRoller",      "exec",    True,  0),
    ("ExtensionRod",   "exec",    True,  0),
    ("TapperPlate",    "tapper",  True,  0),
    # 工件 (米白, 可见, 透明度 40)
    ("PaperBoard",     "paper",   True,  40),
]


def generate_gui_document():
    """生成 GuiDocument.xml 内容"""
    lines = []
    lines.append("<?xml version='1.0' encoding='utf-8'?>")
    lines.append("<!--")
    lines.append(" FreeCAD GuiDocument, see https://www.freecad.org for more information...")
    lines.append("-->")
    lines.append('<Document SchemaVersion="4" ProgramVersion="1.1R20260414 (Git shallow)" FileVersion="1">')

    # Camera (等轴测视图)
    lines.append("  <Camera>")
    lines.append('    <Camera Orthographic="0">')
    lines.append('      <PositionX value="500"/>')
    lines.append('      <PositionY value="-500"/>')
    lines.append('      <PositionZ value="400"/>')
    lines.append('      <DirectionX value="-0.57735"/>')
    lines.append('      <DirectionY value="0.57735"/>')
    lines.append('      <DirectionZ value="-0.57735"/>')
    lines.append('      <UpX value="0"/>')
    lines.append('      <UpY value="0"/>')
    lines.append('      <UpZ value="1"/>')
    lines.append('      <AspectRatio value="1"/>')
    lines.append('      <FieldOfView value="45"/>')
    lines.append('      <FocalDistance value="100"/>')
    lines.append("    </Camera>")
    lines.append("  </Camera>")

    # Properties (空)
    lines.append('  <Properties Count="0">')
    lines.append("  </Properties>")

    # ViewProviderData - 每个对象一个 ViewProvider 节点
    lines.append(f'  <ViewProviderData Count="{len(OBJECTS)}">')

    for obj_name, color_key, visibility, transparency in OBJECTS:
        r, g, b = COLORS[color_key]
        color_value = color_to_freecad(r, g, b)
        vis_str = "true" if visibility else "false"

        lines.append(f'    <ViewProvider name="{obj_name}" type="Gui::ViewProviderPart">')
        lines.append(f'      <Properties Count="5">')
        # Visibility
        lines.append(f'        <Property name="Visibility" type="App::PropertyBool">')
        lines.append(f'          <Bool value="{vis_str}"/>')
        lines.append(f'        </Property>')
        # DisplayMode (0=Shaded, 1=Wireframe, 2=Points)
        lines.append(f'        <Property name="DisplayMode" type="App::PropertyEnumeration">')
        lines.append(f'          <Integer value="0"/>')
        lines.append(f'        </Property>')
        # ShapeColor
        lines.append(f'        <Property name="ShapeColor" type="App::PropertyColor">')
        lines.append(f'          <PropertyColor value="{color_value}"/>')
        lines.append(f'        </Property>')
        # Transparency (0-100)
        lines.append(f'        <Property name="Transparency" type="App::PropertyPercent">')
        lines.append(f'          <Integer value="{transparency}"/>')
        lines.append(f'        </Property>')
        # LineWidth
        lines.append(f'        <Property name="LineWidth" type="App::PropertyFloat">')
        lines.append(f'          <Float value="1"/>')
        lines.append(f'        </Property>')
        lines.append(f'      </Properties>')
        lines.append(f'    </ViewProvider>')

    lines.append("  </ViewProviderData>")
    lines.append("</Document>")

    return "\n".join(lines) + "\n"


def inject_gui():
    """注入 GUI 数据到 FCStd (ZIP)"""
    gui_xml = generate_gui_document()

    print(f"生成的 GuiDocument.xml 大小: {len(gui_xml)} 字节")
    print(f"对象数量: {len(OBJECTS)}")
    print("-" * 50)

    src = SRC_FCSTD
    dst = DST_FCSTD
    tmp = dst + ".tmp"

    # 读取源 FCStd, 复制所有文件 + 添加 GuiDocument.xml
    with zipfile.ZipFile(src, 'r') as zin:
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
            # 复制所有现有文件 (跳过已有的 GuiDocument.xml)
            for item in zin.infolist():
                if item.filename == "GuiDocument.xml":
                    print(f"  跳过现有: {item.filename}")
                    continue
                data = zin.read(item.filename)
                zout.writestr(item, data)

            # 添加新的 GuiDocument.xml
            zout.writestr("GuiDocument.xml", gui_xml.encode('utf-8'))
            print(f"  添加: GuiDocument.xml")

    # 替换目标文件
    shutil.move(tmp, dst)
    print("-" * 50)
    print(f"已注入 GUI 数据到: {dst}")

    # 验证
    with zipfile.ZipFile(dst, 'r') as z:
        names = z.namelist()
        print(f"\nFCStd 包含 {len(names)} 个文件:")
        for n in names:
            print(f"  - {n}")
        if "GuiDocument.xml" in names:
            print("\n[OK] GuiDocument.xml 已成功注入")
            # 读取并显示前几行
            with z.open("GuiDocument.xml") as f:
                content = f.read().decode('utf-8')
                print("\nGuiDocument.xml 前 10 行:")
                for line in content.split('\n')[:10]:
                    print(f"  {line}")
        else:
            print("\n[FAIL] GuiDocument.xml 注入失败")


if __name__ == "__main__":
    inject_gui()
