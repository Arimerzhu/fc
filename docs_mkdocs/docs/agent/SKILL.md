# AI Agent 集成

fc 专为 AI Agent 设计，提供完整的工具认知体系。

## 核心能力

### 1. 结构化工具清单

`TOOL_SCHEMA.json` — 17 命令组, 185 命令, 26 错误码, 31 GUI 映射。AI Agent 通过读取此文件自动发现所有命令。

### 2. 五阶段执行流

强制 AI 按流程执行：工具选型 → 任务拆解 → 坐标计算 → 依赖校验 → 命令输出。跳过任何一步都算失败。

详见 [五阶段执行流模板](execution-flow.md)。

### 3. 上下文注入

每批 ≤10 命令执行后，自动生成元素摘要反馈给 AI，解决"上下文失忆"问题。

详见 [上下文注入协议](context-injection.md)。

### 4. 错误闭环自动学习

同一错误模式 ≥3 次 → 自动生成禁止规则 → 下次自动规避。

详见 [错误规则](error-rules.md)。

### 5. Function Calling Schema

185 个 OpenAI function calling 定义，AI 通过结构化参数调用，消灭语法错误。

详见 [Function Calling](function-calling.md)。

## SKILL.md

完整的 AI Agent 技能定义文件，包含：

- 17 命令组完整参考
- 五阶段执行流规则
- 意图→命令映射表
- 错误处理表
- 18 条 AI 使用技巧

[查看完整 SKILL.md](../SKILL.md)

## 使用示例

```bash
# 自然语言 → CAD 建模
fc agent "创建一个 100x50x20mm 的底板，中心有直径 10mm 的通孔，导出 STEP"

# 复杂装配体
fc agent "设计一个二级圆柱齿轮减速器，包含箱体、齿轮轴、轴承、端盖"
```

## 示例库

| 示例 | 难度 | 步骤数 | 说明 |
|------|------|--------|------|
| [底板通孔](../examples/01_simple_box_with_hole.md) | 简单 | 6 | 基础盒子 + 通孔 |
| [安装支架](../examples/02_mounting_bracket.md) | 中等 | 13 | 带凸台倒角 |
| [装配体](../examples/03_simple_assembly.md) | 中等 | 21 | 底座+支柱 |
| [参数化设计](../examples/04_parametric_design.md) | 中等 | 17 | 电子表格驱动 |
| [完整工作流](../examples/05_full_workflow.md) | 复杂 | 22 | 从需求到工程图 |
