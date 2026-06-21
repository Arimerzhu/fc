# Findings: Phase 1 — 输出验证层

## 现有架构分析

### HeadlessBackend 工作方式
- 通过生成 Python 宏脚本 → 调用 FreeCADCmd 执行 → 解析输出
- export 方法在 `packages/core/src/fc_core/backend.py` 中
- 返回 `ToolResponse` 对象（success, error, data, warning）

### ToolResponse 结构
- `success: bool`
- `error: Optional[str]`
- `data: Optional[dict]`
- `warning: Optional[str]`

### 现有测试框架
- pytest + conftest.py
- Mock Backend 用于无 FreeCAD 环境
- 真实 FreeCAD 测试用 skip 标记

## DBY250 教训记录

### 教训 1: FreeCADCmd 保存的 FCStd 缺少 GUI 数据
- 现象：FCStd 文件 14KB，包含 15 个 .brp 文件，Document.xml 正确
- 但 FreeCAD GUI 打开为空
- 原因：缺少 GuiDocument.xml（ViewObject 数据、相机位置）
- 验证方法：用 FreeCADCmd 重新打开 FCStd，检查对象数和 BoundBox

### 教训 2: Part.export([裸Shape]) 无效
- `Part.export([all_shape])` 导出的 STEP 只有 1 个点
- `Part.export(doc_objs)` 导出正确（doc_objs 是文档对象列表）
- 验证方法：Part.read(step_path) 检查 Solids 数量

### 教训 3: TechDraw 在 Headless 模式功能残缺
- `TechDraw.DrawViewPart.Source` 赋值全部失败
- `TechDraw.exportPageAsSvg` 不存在
- `TechDraw.projectToSVG` 可用但只输出线条
- 验证方法：检测 API 是否存在
