---
name: fc
description: FreeCAD CLI Agent 技能索引。加载对应 skill 文件以获取详细命令参考。
---

# fc — Agent Native FreeCAD CLI 技能索引

> **加载策略**: 每次任务必读 CORE + FUNDAMENTALS，其他按任务类型加载。
>
> **总入口原则**: `fc` 技能是通用 FreeCAD CLI 入口，覆盖建模、出图、导入导出。SolidWorks 转换和 GUI 注入属于专项任务，需要时再加载对应专项 skill，避免每次画图都加载不必要的内容。

## 加载流程图

```
每次任务必读:
  ✅ CORE.md          — 五阶段执行流、全局规则、错误处理
  ✅ FUNDAMENTALS.md  — document/session/execute

按任务类型加载（选 1-2 个）:
  📦 创建几何体         → MODELING.md              — part/sketch/body
  ⚙️  工程分析/装配      → ENGINEERING.md           — assembly/fem/cam/material
  📐 出工程图           → DRAFTING.md              — techdraw/draft/spreadsheet
  💾 导入导出           → DATA_EXCHANGE.md         — export/import/mesh/surface

专项技能（需要时再加载，不混入日常画图流程）:
  🔧 SolidWorks 转换    → fc-solidworks/SKILL.md   — sldprt/sldasm ↔ FCStd
  🎨 GUI 数据注入       → fc-gui-injection/SKILL.md — 注入 GuiDocument.xml

学习参考（按需）:
  📚 EXAMPLES.md      — 5 个完整示例 + 模式库
```

## Skill 文件一览

| Skill | 行数 | 覆盖命令组 | 什么时候加载 |
|-------|------|-----------|------------|
| CORE | 182 | 全局规则、五阶段流、错误处理 | **每次必读** |
| FUNDAMENTALS | 133 | document, session, execute | **每次必读** |
| MODELING | 244 | part, sketch, body | 创建几何体时 |
| ENGINEERING | 145 | assembly, fem, cam, material | 工程分析/装配时 |
| DRAFTING | 135 | techdraw, draft, spreadsheet | 出图/标注时 |
| DATA_EXCHANGE | 138 | export, import, mesh, surface | 数据转换时 |
| fc-solidworks | - | sldprt/sldasm → STEP → FCStd | SolidWorks 批量转换时 |
| fc-gui-injection | - | GuiDocument.xml 注入 | headless 生成文件缺 GUI 时 |
| EXAMPLES | 118 | 5 个示例 + 模式库 | 学习风格时 |

## 快速意图查询

| 我想... | 加载 |
|---------|------|
| 开始一个新任务 | CORE + FUNDAMENTALS |
| 创建盒子/圆柱/简单几何体 | MODELING |
| 用草图建模（sketch → pad） | MODELING |
| 装配多个零件 | ENGINEERING |
| 做有限元分析 | ENGINEERING |
| 生成工程图/PDF | DRAFTING |
| 导出 STEP/STL/3MF | DATA_EXCHANGE |
| 修复/转换网格 | DATA_EXCHANGE |
| SolidWorks 批量转 FreeCAD | fc-solidworks |
| FCStd 缺少颜色/GUI 数据 | fc-gui-injection |
| 学习完整示例 | EXAMPLES |

## 核心规则速查

1. 始终使用 `--json`
2. 唯一命名：`{类型}_{序号}`
3. 只引用已创建的元素
4. 多步工作流用 `--project`
5. 每批 ≤10 命令
6. 先 `document new` 再建模
7. 五阶段执行流不可跳过

## fc agent — Agent 流水线（0.9.0 新增）

当用户需要"一句话出图"或"自动完成全流程"时，使用 `fc agent` 命令：

```bash
# 一句话出图：需求→设计→建模→审查→出图→标注 全流程
fc agent pipeline "一个长100mm宽50mm高25mm的盒子，Q235钢"

# 标准零件库查询
fc agent library list                # 列出所有内置标准件
fc agent library get shaft           # 查看 shaft 定义
fc agent library run "M6x16螺栓" --output bolt.fcstd

# Schema 握手验证（检查Agent间IO兼容性）
fc agent handshake --requirement '{"part_type":"BOX","dimensions":{"length":100}}'

# 诊断已有流水线结果
fc agent explain pipeline_trace.json
```

### Agent 流水线架构

```
用户输入 → AgentGraph（LangGraph 风格控制图）
  ├─ requirement  → 需求解析 Agent
  ├─ design       → 设计规划 Agent
  ├─ modeling     → CAD 建模 Agent
  ├─ review       → 几何审查 Agent（条件回滚到 design/modeling）
  ├─ drafting     → 出图 Agent
  └─ annotation   → 标注合规 Agent（条件回滚到 drafting）
```

## 完整命令参考

- 机器可读 schema: `docs/TOOL_SCHEMA.json` (185 命令)
- Function calling: `docs/FUNCTION_SCHEMAS.json` (185 函数定义)
- 五阶段模板: `docs/EXECUTION_FLOW_TEMPLATE.md`
- 上下文注入协议: `docs/CONTEXT_INJECTION_PROTOCOL.md`
- 错误规则: `docs/ERROR_RULES.md`
- AI Agent 指南: `docs/AI_AGENT_GUIDE.md`
