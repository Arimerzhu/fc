---
name: fc
description: FreeCAD CLI Agent 技能索引。加载对应 skill 文件以获取详细命令参考。
---

# fc — Agent Native FreeCAD CLI 技能索引

> **加载策略**: 每次任务必读 CORE + FUNDAMENTALS，其他按任务类型加载。

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

## 完整命令参考

- 机器可读 schema: `docs/TOOL_SCHEMA.json` (185 命令)
- Function calling: `docs/FUNCTION_SCHEMAS.json` (185 函数定义)
- 五阶段模板: `docs/EXECUTION_FLOW_TEMPLATE.md`
- 上下文注入协议: `docs/CONTEXT_INJECTION_PROTOCOL.md`
- 错误规则: `docs/ERROR_RULES.md`
- AI Agent 指南: `docs/AI_AGENT_GUIDE.md`
