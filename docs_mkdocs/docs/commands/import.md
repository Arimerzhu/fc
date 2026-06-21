---
name: fc-import
description: FreeCAD 导入命令 — 支持 STEP/IGES/STL/OBJ/DXF/SVG/BREP/3MF/PLY/OFF/GLTF 格式。用于将各种 CAD/网格文件导入当前文档。
---

# fc-import — FreeCAD 导入 CLI 命令

## 命令组概览（11 个命令）

| 命令 | 说明 |
|------|------|
| `import auto` | 自动检测格式并导入 |
| `import step` | 导入 STEP |
| `import stl` | 导入 STL |
| `import obj` | 导入 OBJ |
| `import dxf` | 导入 DXF |
| `import brep` | 导入 BREP |
| `import iges` | 导入 IGES |
| `import svg` | 导入 SVG |
| `import 3mf` | 导入 3MF |
| `import ply` | 导入 PLY |
| `import info` | 查看文件信息 |

## 导入格式速查

| 格式 | 扩展名 | 类型 |
|------|--------|------|
| STEP | .step/.stp | CAD |
| IGES | .iges/.igs | CAD |
| STL | .stl | 网格 |
| OBJ | .obj | 网格 |
| DXF | .dxf | 2D CAD |
| SVG | .svg | 矢量 |
| BREP | .brep | CAD |
| 3MF | .3mf | 3D 打印 |
| PLY | .ply | 网格 |
| OFF | .off | 网格 |
| GLTF | .gltf | 3D (网格) |

## 典型工作流

```bash
# 导入 CAD 模型
fc import step --path model.step

# 导入网格
fc import stl --path mesh.stl

# 自动检测
fc import auto --path unknown_file.FCStd

# 查看文件信息（不导入）
fc import info --path model.step
```

## 注意事项

- 所有命令支持 `--json` 输出
- `import auto` 根据文件扩展名自动选择导入方式
- `import info` 只读取文件元数据，不实际导入
- 网格格式 (STL/OBJ/PLY/OFF/3MF/GLTF) 通过 Mesh 模块导入
- CAD 格式 (STEP/IGES/BREP) 通过 Part 模块导入
