---
name: fc-mesh
description: FreeCAD 网格操作命令 — 导入/导出/分析/修复/细化/简化/布尔/截面/列表/信息/创建/评估/翻转法线/平滑。
---

# fc-mesh — FreeCAD 网格操作 CLI 命令

## 命令组概览（14 个命令）

| 命令 | 说明 |
|------|------|
| `mesh import` | 导入网格文件 |
| `mesh export` | 导出网格文件 |
| `mesh analyze` | 分析网格 |
| `mesh repair` | 修复网格 |
| `mesh refine` | 细化网格 |
| `mesh decimate` | 简化网格 |
| `mesh boolean` | 网格布尔操作 |
| `mesh section` | 网格截面 |
| `mesh list` | 列出网格对象 |
| `mesh info` | 网格详细信息 |
| `mesh create` | 创建基本网格 |
| `mesh evaluate` | 评估网格质量 |
| `mesh flip-normals` | 翻转法线 |
| `mesh smooth` | 平滑网格 |

## 典型工作流

### 工作流 1：STL 修复流程
```bash
fc document new --name MeshWork
fc mesh import --path part.stl
fc mesh analyze MyMesh
fc mesh repair MyMesh
fc mesh smooth MyMesh --iterations 5
fc mesh export MyMesh --output fixed.stl
```

### 工作流 2：创建基本网格
```bash
fc mesh create cube --name CubeMesh --size 20
fc mesh evaluate CubeMesh
fc mesh export CubeMesh --output cube.stl
```

## 注意事项

- 所有命令支持 `--json` 输出
- `mesh create` 支持 cube/sphere/cylinder 类型
- `mesh smooth` 的 `--iterations` 控制平滑次数，`--factor` 控制强度
- `mesh boolean` 支持 union/difference/intersection 操作
