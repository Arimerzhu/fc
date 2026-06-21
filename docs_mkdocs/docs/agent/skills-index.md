# Skill 体系

fc 提供 7 个分类 skill 文件，覆盖全部 17 个命令组。

## 加载策略

```
每次任务必读:
  ✅ CORE.md          — 五阶段执行流、全局规则、错误处理
  ✅ FUNDAMENTALS.md  — document/session/execute

按任务类型加载（选 1-2 个）:
  📦 创建几何体    → MODELING.md      — part/sketch/body
  ⚙️  工程分析/装配 → ENGINEERING.md   — assembly/fem/cam/material
  📐 出工程图      → DRAFTING.md      — techdraw/draft/spreadsheet
  💾 导入导出      → DATA_EXCHANGE.md — export/import/mesh/surface

学习参考（按需）:
  📚 EXAMPLES.md      — 5 个完整示例 + 模式库
```

## Skill 文件

| Skill | 覆盖命令组 | 行数 | 什么时候加载 |
|-------|-----------|------|------------|
| CORE | 全局规则、五阶段流、错误处理 | 182 | **每次必读** |
| FUNDAMENTALS | document, session, execute | 133 | **每次必读** |
| MODELING | part, sketch, body | 244 | 创建几何体时 |
| ENGINEERING | assembly, fem, cam, material | 145 | 工程分析/装配时 |
| DRAFTING | techdraw, draft, spreadsheet | 135 | 出图/标注时 |
| DATA_EXCHANGE | export, import, mesh, surface | 138 | 数据转换时 |
| EXAMPLES | 5 个示例 + 模式库 | 118 | 学习风格时 |

## 命令组覆盖

| 命令组 | 所属 Skill |
|--------|-----------|
| document | FUNDAMENTALS |
| session | FUNDAMENTALS |
| execute | FUNDAMENTALS |
| part | MODELING |
| sketch | MODELING |
| body | MODELING |
| assembly | ENGINEERING |
| fem | ENGINEERING |
| cam | ENGINEERING |
| material | ENGINEERING |
| techdraw | DRAFTING |
| draft | DRAFTING |
| spreadsheet | DRAFTING |
| export | DATA_EXCHANGE |
| import | DATA_EXCHANGE |
| mesh | DATA_EXCHANGE |
| surface | DATA_EXCHANGE |

## 完整命令参考

- 机器可读 schema: [TOOL_SCHEMA.json](../TOOL_SCHEMA.json) (185 命令)
- Function calling: [FUNCTION_SCHEMAS.json](../FUNCTION_SCHEMAS.json) (185 函数定义)
- 五阶段模板: [EXECUTION_FLOW_TEMPLATE.md](../EXECUTION_FLOW_TEMPLATE.md)
- 上下文注入协议: [CONTEXT_INJECTION_PROTOCOL.md](../CONTEXT_INJECTION_PROTOCOL.md)
- 错误规则: [ERROR_RULES.md](../ERROR_RULES.md)
- AI Agent 指南: [AI_AGENT_GUIDE.md](ai-guide.md)
