# fc — Agent Native FreeCAD CLI

> 让 AI Agent 能像程序员操作 Linux 一样操作 CAD。

## 概述

**fc** 是一个全面的 FreeCAD CLI 工具，暴露了 185+ 个命令，覆盖所有 FreeCAD 工作台。专为 AI Agent 设计，支持结构化 JSON 输出。

### 核心特性

- 🎯 **AI First** — 所有命令输出结构化 JSON，AI Agent 可直接消费
- 🔧 **17 命令组** — Document, Part, Sketch, Body, Export, Import, Session, Execute, Mesh, Draft, Surface, TechDraw, Spreadsheet, Material, Assembly, FEM, CAM
- 🤖 **Agent Runtime** — 内置 Planner/Executor/Corrector，支持自然语言→CAD 建模
- 🔌 **MCP Native** — 6 个 MCP 工具模块，兼容 Claude Desktop、Cursor 等
- 🛡️ **安全加固** — 路径遍历防护、名称验证、导入/导出验证
- 📦 **双后端** — Headless (FreeCADCmd) 和 RPC (FreeCAD GUI)

### 快速示例

```bash
# 创建一个盒子
fc part add box --name Box --param Length=100 --param Width=50 --param Height=20 --json

# 创建圆柱
fc part add cylinder --name Cyl --param Radius=10 --param Height=30 --json

# 布尔运算（切割）
fc part boolean cut --base Box --tool Cyl --name Result --json

# 导出 STEP
fc export step --output model.step --json
```

### AI Agent 使用

```bash
# 自然语言 → CAD 建模
fc agent "创建一个 100x50x20mm 的底板，中心有一个直径 10mm 的通孔，导出 STEP"
```

## 架构

```
CLI Layer              ← Click commands, 17 command groups, 185+ commands
  ↓
Agent Runtime Layer    ← Planning, execution, self-correction, BOM
  ↓
Tool Registry Layer    ← MCP tools (6 tool modules, ~50 tools)
  ↓
FreeCAD Capability Layer ← fc-core: backend, geometry, engineering, io
  ↓
FreeCAD Kernel         ← FreeCADCmd / FreeCAD GUI
```

## 测试覆盖

| 包 | 测试数 | 覆盖率 |
|----|--------|--------|
| fc-core | 413 | >85% |
| fc-cli | 540 | >90% |
| fc-mcp | 268 | >85% |
| fc-runtime | 287 | >80% |
| **合计** | **1,529** | **>85%** |

## 许可证

MIT License
