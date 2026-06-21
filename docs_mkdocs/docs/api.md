# API 文档

## Python API

fc 的所有 CLI 命令都有对应的 Python API。

### 核心模块

```python
from fc_core.backend import HeadlessBackend, RPCBackend
from fc_core.types import ToolResponse, Vec3, Placement
from fc_runtime.planner import Planner
from fc_runtime.executor import Executor
from fc_runtime.corrector import Corrector
```

### Backend

```python
# Headless 后端（默认）
backend = HeadlessBackend(freecad_path="C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe")

# 创建文档
result = backend.create_document("MyPart")
print(result.data)  # {"name": "MyPart", "path": ""}

# 添加盒子
result = backend.add_box("Box", length=100, width=50, height=20)
print(result.data)  # {"name": "Box", "type": "Part::Box"}

# 导出
result = backend.export_step("model.step")
```

### Planner + Executor

```python
planner = Planner()
plan = planner.plan("创建一个 100x50x20mm 的底板，中心有直径 10mm 的通孔")

executor = Executor(dry_run=True)
results = executor.execute_plan(plan)
```

### Corrector

```python
corrector = Corrector()
# 自动分析错误并尝试修正
correction = corrector.correct(failed_task, task_result)
```

## 类型系统

| 类型 | 说明 |
|------|------|
| `ToolResponse` | 统一响应格式 (status, operation, data, error) |
| `Vec3` | 3D 向量 (x, y, z) |
| `Placement` | 位置+旋转 |
| `TaskType` | 任务类型枚举 |
| `TaskStatus` | 任务状态枚举 |

## 错误码

| 错误码 | 说明 |
|--------|------|
| `NOT_FOUND` | FreeCAD 或对象未找到 |
| `CREATE_FAILED` | 创建失败 |
| `EXPORT_FAILED` | 导出失败 |
| `IMPORT_FAILED` | 导入失败 |
| `BOOLEAN_FAILED` | 布尔运算失败 |
| `INVALID_NAME` | 无效名称 |
| `INVALID_TYPE` | 无效类型 |
| `TIMEOUT` | 超时 |

完整错误码表见 `docs/TOOL_SCHEMA.json`。
