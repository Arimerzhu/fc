---
name: fc-data-exchange
description: fc 数据技能 — export/import/mesh/surface 命令组。数据转换时加载。
---

# fc-data-exchange — 数据导入导出命令参考

## export（14 个命令）

将模型导出为各种 CAD/网格格式。

| 命令组 | 命令 | 说明 |
|--------|------|------|
| 通用 | `step` / `iges` / `brep` / `fcstd` | CAD 格式交换 |
| 3D 打印 | `stl` / `3mf` | 增材制造 |
| 网格 | `obj` / `ply` / `off` | 通用网格格式 |
| Web/渲染 | `gltf` | Web 3D |
| 2D/DXF | `dxf` / `svg` | AutoCAD / 矢量图 |
| 文档 | `pdf` | 工程图 PDF |
| 辅助 | `presets` | 列出导出预设 |

**格式速查表：**

| 格式 | 扩展名 | 类型 | 用途 |
|------|--------|------|------|
| STEP | .step/.stp | CAD | 跨系统交换（ISO 10303） |
| IGES | .iges/.igs | CAD | 旧系统兼容 |
| BREP | .brep | CAD | OpenCASCADE 原生 |
| FCSTD | .fcstd | CAD | FreeCAD 项目 |
| STL | .stl | 网格 | 3D 打印 |
| 3MF | .3mf | 网格 | 3D 打印（微软） |
| OBJ | .obj | 网格 | 通用 3D |
| PLY | .ply | 网格 | 点云数据 |
| OFF | .off | 网格 | 几何研究 |
| GLTF | .gltf | 网格 | Web 3D 渲染 |
| DXF | .dxf | 2D | AutoCAD 兼容 |
| SVG | .svg | 2D | 矢量图形 |
| PDF | .pdf | 文档 | 工程图交付 |

## import（11 个命令）

将外部文件导入当前文档。

| 命令 | 说明 | 模块 |
|------|------|------|
| `auto` | 自动检测格式 | - |
| `step` / `iges` / `brep` | CAD 格式 | Part |
| `stl` / `obj` / `ply` / `3mf` | 网格格式 | Mesh |
| `dxf` / `svg` | 2D 格式 | - |
| `info` | 查看文件元数据（不导入） | - |

## mesh（14 个命令）

网格的导入、导出、分析、修复与创建。

| 类别 | 命令 | 说明 |
|------|------|------|
| IO | `import` / `export` | 网格文件读写 |
| 分析 | `analyze` / `evaluate` / `info` | 网格质量检查 |
| 修复 | `repair` / `flip-normals` / `smooth` | 修复缺陷网格 |
| 优化 | `refine` / `decimate` | 细化 / 简化 |
| 操作 | `boolean` / `section` | 布尔 / 截面 |
| 创建 | `create` | 基本体（cube/sphere/cylinder） |
| 查询 | `list` | 列出网格对象 |

## surface（13 个命令）

高级曲面建模操作。

| 类别 | 命令 | 说明 |
|------|------|------|
| 生成 | `loft` / `sweep` / `fill` / `pipe` | 放样/扫描/填充/管道 |
| 变换 | `offset` / `thicken` / `flatten` / `sew` | 偏移/加厚/展平/缝合 |
| 拉伸 | `extrude` / `revolve` / `ruled` | 拉伸/旋转/直纹 |
| 分析 | `curvature` | 曲率分析 |
| 查询 | `list` | 列出曲面对象 |

## 典型工作流

### 工作流 1：CAD 模型交付
```bash
fc export step --output model.step --overwrite
fc export iges --output model.iges --overwrite
```

### 工作流 2：STL 修复流程
```bash
fc mesh import --path part.stl
fc mesh analyze MyMesh
fc mesh repair MyMesh
fc mesh smooth MyMesh --iterations 5
fc mesh export MyMesh --output fixed.stl
```

### 工作流 3：放样曲面
```bash
fc surface loft --profiles "Profile1;Profile2" --solid
fc export step --output loft_surf.step
```

## 数据管道（Data Pipeline）

```
导入 CAD → 修复网格 → 格式转换 → 导出
    |           |           |         |
    v           v           v         v
 import step  mesh repair  mesh      export stl
 import stl   mesh smooth  decimate  export step
 import obj   flip-normals refine    export 3mf
```

**典型管道示例：**
```bash
# 1. 导入外部 CAD
fc import step --path model.step

# 2. 转为网格并修复
fc mesh import --path model.stl
fc mesh repair MyMesh
fc mesh smooth MyMesh --iterations 3

# 3. 简化网格（如需）
fc mesh decimate MyMesh --ratio 0.5

# 4. 导出目标格式
fc export stl --output final.stl --overwrite
fc export 3mf --output final.3mf --overwrite
```

## 关键注意事项

- 所有命令支持 `--json` 输出
- `import auto` 根据扩展名自动选择导入方式
- `import info` 只读元数据，不实际导入
- `export stl` 默认二进制格式
- `mesh boolean` 支持 union/difference/intersection
- `surface loft` 需要至少 2 个轮廓
- `surface thicken` 的 `--direction` 可为 `both` 或 `single`
