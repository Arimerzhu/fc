# 上下文注入协议 (Context Injection Protocol)

> TASK-035: 命令历史上下文注入机制

## 概述

上下文注入是 Executor 在分批执行任务后，自动生成元素摘要反馈给 Planner/AI 的机制。
解决 AI 的"上下文失忆"问题 — 记不住前面创建的元素名称/ID，导致后续引用失败。

## 协议流程

```
Planner 生成 Plan (N 个 tasks)
    ↓
Executor 分批执行 (每批 ≤ batch_size 个)
    ↓
每批执行完毕 → 生成 BatchContext
    ↓
BatchContext.to_injection_text() → 反馈给 AI
    ↓
AI 基于已创建元素列表继续生成后续命令
    ↓
重复直到所有任务完成
```

## 数据结构

### ElementSummary

单个创建元素的摘要：

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 元素名称 (如 "Box_001") |
| type | str | 元素类型 (如 "Box", "Cylinder") |
| task_id | str | 创建该元素的任务 ID |
| command | str | 使用的 CLI 命令 |
| params | dict | 创建参数 |
| position | str | 位置坐标 (如 "0,0,0") |
| dimensions | dict | 尺寸 (如 {"length": 100, "width": 50}) |

### BatchContext

一批执行结果的上下文：

| 字段 | 类型 | 说明 |
|------|------|------|
| batch_number | int | 批次编号 |
| elements | list[ElementSummary] | 本批创建的元素 |
| commands_executed | list[str] | 本批执行的命令 |
| success_count | int | 成功数 |
| fail_count | int | 失败数 |

## 输出格式

```markdown
## Batch 1 Execution Results

**Status**: 4 succeeded, 0 failed

**Created Elements:**
- Box_001 (Box), position=0,0,0, dimensions=100x50x20
- Cylinder_001 (Cylinder), position=50,25,20, dimensions=10x10x30

**Executed Commands:**
1. `fc --json document new --name MyPart`
2. `fc --json part add box --name Box_001 --param Length=100 --param Width=50 --param Height=20`
3. `fc --json part add cylinder --name Cylinder_001 --param Radius=10 --param Height=30`
4. `fc --json part boolean cut Box_001 Cylinder_001 --name Result_001`

## All Created Elements (Cumulative)
| Name | Type | Position |
|------|------|----------|
| Box_001 | Box | 0,0,0 |
| Cylinder_001 | Cylinder | 50,25,20 |
| Result_001 | Cut | 0,0,0 |
```

## 元素引用验证

AI 在生成后续命令前，必须通过 `Executor.validate_element_reference(name)` 验证元素是否已创建：

- ✅ `Box_001` — 已创建，可以引用
- ❌ `Box_002` — 未创建，禁止引用

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| batch_size | 10 | 每批最大命令数 |
| max_iterations | N × 3 | 最大迭代次数（含重试） |

## 集成点

- `Executor.__init__()` — 初始化上下文状态
- `Executor.execute_plan()` — 分批执行 + 自动注入
- `Executor.get_context_injection()` — 获取完整上下文文本
- `Executor.validate_element_reference()` — 验证元素引用
- `Executor.get_available_elements()` — 获取可用元素列表
