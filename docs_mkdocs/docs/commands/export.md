---
name: fc-export
description: FreeCAD 导出命令 — 支持 STEP/IGES/STL/OBJ/BREP/DXF/SVG/PDF/GLTF/3MF/FCSTD/OFF/PLY/AMF 格式。用于将模型导出为各种 CAD/网格格式。
---

# fc-export — FreeCAD 导出 CLI 命令

## 命令组概览（14 个命令）

| 命令 | 说明 |
|------|------|
| `export step` | 导出 STEP |
| `export stl` | 导出 STL |
| `export obj` | 导出 OBJ |
| `export brep` | 导出 BREP |
| `export dxf` | 导出 DXF |
| `export svg` | 导出 SVG |
| `export pdf` | 导出 PDF |
| `export gltf` | 导出 GLTF |
| `export 3mf` | 导出 3MF |
| `export fcstd` | 导出 FCSTD |
| `export iges` | 导出 IGES |
| `export off` | 导出 OFF |
| `export ply` | 导出 PLY |
| `export presets` | 列出预设 |

## 导出格式速查

| 格式 | 扩展名 | 用途 |
|------|--------|------|
| STEP | .step/.stp | CAD 交换 (ISO 10303) |
| IGES | .iges/.igs | CAD 交换 (旧标准) |
| STL | .stl | 3D 打印 |
| OBJ | .obj | 通用 3D |
| BREP | .brep | OpenCASCADE |
| DXF | .dxf | AutoCAD 2D |
| SVG | .svg | 矢量图形 |
| PDF | .pdf | 文档 |
| GLTF | .gltf | Web 3D |
| 3MF | .3mf | 3D 打印 (微软) |

## 典型工作流

```bash
# CAD 模型交付
fc export step --output model.step
fc export iges --output model.iges

# 3D 打印
fc export stl --output model.stl

# 2D 工程图
fc export dxf --output drawing.dxf
fc export pdf --output drawing.pdf
```

## 注意事项

- 所有命令支持 `--json` 输出
- `export step/iges` 的 `--objects` 可指定要导出的对象
- `export stl` 默认二进制格式
- 使用 `export presets` 查看所有导出预设
