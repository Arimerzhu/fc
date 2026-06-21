# Visual Verification Protocol (VVP)

> Computer Use + AI 视觉闭环验证 FreeCAD 模型正确性
>
> 版本: 1.0 | 日期: 2026-06-20 | 作者: Chief Architect

## 1. 概述

### 1.1 问题

几何拓扑校验（GeometryValidator）只能验证数学属性（面数、体积、连通性），
无法判断"模型看起来对不对"。例如：

- 几何审查 PASS 但模型尺寸比例视觉上不协调
- 布尔运算结果正确但形状不符合预期
- 零件特征位置错误但拓扑结构完整

### 1.2 解决方案

通过 **Computer Use**（Windows UI 自动化）控制 FreeCAD GUI，
从多个标准视角截图，然后由 **AI 视觉能力** 判断模型正确性。

### 1.3 流水线位置

`
需求解析 -> 设计规划 -> CAD建模 -> 几何审查 -> 出图 -> 标注审查
                                                        |
                                              视觉验证 <- Computer Use
                                                        |
                                                      完成
`

## 2. 架构

### 2.1 模块结构

`
packages/runtime/src/fc_runtime/
  visual_verifier.py      <- 核心模块
  visual_verification.py  <- 集成层
verify_visual.py           <- 独立 CLI 脚本
`

### 2.2 数据流

`
PipelineResult -> VisualVerifier.generate_plan()
  -> VisualVerificationPlan -> Computer Use 执行
  -> [Screenshots] -> VisualVerifier.analyze()
  -> VisualVerificationResult (PASS/FAIL)
`

## 3. Computer Use 动作序列

### 3.1 标准动作类型

| 动作 | 说明 | FreeCAD 操作 |
|------|------|-------------|
| launch_app | 启动应用 | 启动 FreeCAD.exe |
| find_window | 定位窗口 | 按标题查找 |
| open_file | 打开文件 | Ctrl+O |
| set_view | 切换视图 | 数字键盘 |
| zoom_fit | 缩放适配 | V, F |
| capture_screenshot | 截图 | sky.get_window_state() |
| close_app | 关闭应用 | Alt+F4 |
| wait | 等待 | 延迟 ms |

### 3.2 视角快捷键

| 视角 | FreeCAD 名称 | 快捷键 |
|------|-------------|--------|
| isometric | Axonometric | Ctrl+Numpad0 |
| front | Front | Numpad1 |
| left | Left | Numpad3 |
| right | Right | Ctrl+Numpad3 |
| top | Top | Numpad7 |

## 4. 视觉检查项

### 4.1 自动化检查

| 检查项 | 条件 | 错误等级 |
|--------|------|----------|
| dimension_consistency | 几何审查 PASS + 需求尺寸 | DESIGN |
| geometry_pass_rate | 几何检查通过率 >= 80% | CODE |
| aspect_ratio | 宽高比与零件类型匹配 | DESIGN |
| bounding_box_reasonable | bbox 比率 0.7~1.3 | CODE |

### 4.2 AI 视觉检查

需要 AI 查看截图判断: 形状正确性、特征位置、比例感观

### 4.3 视角选择策略

| 零件类型 | 推荐视角 |
|----------|----------|
| plate, bracket, flange | isometric, top, front |
| shaft, cylinder | isometric, front, top |
| sphere, torus, gear | isometric, front |
| 其他 | isometric, front, top, right |

## 5. 使用方式

### 5.1 Orchestrator 自动执行

`python
from fc_runtime.orchestrator import Orchestrator
orch = Orchestrator()
result = orch.run("一个铁盒子 100x50x30mm")
print(result.visual_plan_json)    # CU 动作计划
print(result.visual_result_data)  # 验证结果
`

### 5.2 CLI 脚本

`ash
python verify_visual.py pipeline "铁盒子 100x50x30"
python verify_visual.py file model.FCStd
python verify_visual.py export model.FCStd -o plan.json
python verify_visual.py guide model.FCStd
`

### 5.3 Codex Computer Use

`
1. 运行流水线生成 FCStd
2. python verify_visual.py guide <fcstd> 获取 JS
3. 在 node_repl 中执行 JS 脚本
4. AI 查看截图判断正确性
`

## 6. 已知限制

1. 需要 FreeCAD GUI 运行
2. 截图需 AI 视觉能力判断
3. 快捷键可能被自定义覆盖
4. Mock 模式 bbox 为零会 FAIL

## 7. 未来扩展

- [ ] OpenCV 自动轮廓对比
- [ ] 360 度旋转截图
- [ ] 两版模型截图差异对比
- [ ] 带截图的 PDF 验证报告
- [ ] GUI 操作 -> CLI 命令逆向学习
