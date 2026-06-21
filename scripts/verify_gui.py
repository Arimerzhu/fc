"""验证注入后的 FCStd 文件完整性"""
import sys
sys.path.insert(0, r"C:\Program Files\FreeCAD 1.1\bin")
sys.path.insert(0, r"C:\Program Files\FreeCAD 1.1\lib")

import FreeCAD
import zipfile

fcstd_path = r"d:\桌面文件\PaperFeeder.FCStd"

# 1. 验证 ZIP 完整性
print("=" * 50)
print("1. ZIP 完整性检查")
print("=" * 50)
with zipfile.ZipFile(fcstd_path, 'r') as z:
    bad = z.testzip()
    if bad is None:
        print("[OK] ZIP 完整性正常")
    else:
        print(f"[FAIL] 损坏文件: {bad}")
    names = z.namelist()
    print(f"文件数: {len(names)}")
    print(f"包含 GuiDocument.xml: {'GuiDocument.xml' in names}")

# 2. 用 FreeCAD 加载验证
print("\n" + "=" * 50)
print("2. FreeCAD 加载验证")
print("=" * 50)
doc = FreeCAD.openDocument(fcstd_path)
print(f"文档名: {doc.Name}")
print(f"对象数: {len(doc.Objects)}")
print("\n对象列表:")
for i, obj in enumerate(doc.Objects, 1):
    print(f"  {i:2d}. {obj.Name:20s} ({obj.TypeId})")

# 3. 检查 GuiDocument.xml 内容
print("\n" + "=" * 50)
print("3. GuiDocument.xml 内容检查")
print("=" * 50)
with zipfile.ZipFile(fcstd_path, 'r') as z:
    with z.open("GuiDocument.xml") as f:
        content = f.read().decode('utf-8')

# 统计 ViewProvider 节点数
vp_count = content.count("<ViewProvider name=")
print(f"ViewProvider 节点数: {vp_count}")

# 检查关键属性
print(f"包含 ShapeColor: {'ShapeColor' in content}")
print(f"包含 Transparency: {'Transparency' in content}")
print(f"包含 Visibility: {'Visibility' in content}")
print(f"包含 DisplayMode: {'DisplayMode' in content}")

# 显示一个示例 ViewProvider
import re
match = re.search(r'<ViewProvider name="Cam".*?</ViewProvider>', content, re.DOTALL)
if match:
    print("\nCam 对象的 ViewProvider (示例):")
    print(match.group(0))

FreeCAD.closeDocument(doc.Name)
print("\n[OK] 验证完成")
