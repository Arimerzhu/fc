---
name: fc-solidworks
description: "SolidWorks 原生文件 (.sldprt/.sldasm) 批量导出 STEP 并导入 FreeCAD 保存为 FCStd 的工作流。Invoke when user needs to convert SolidWorks files to FreeCAD format, batch process .sldprt/.sldasm, or build SW↔FreeCAD automation."
---

# fc-solidworks — SolidWorks ↔ FreeCAD 批量转换

本 Skill 描述将 SolidWorks 原生文件（.sldprt / .sldasm）批量转换为 FreeCAD（.FCStd）的完整流程，使用 fc 项目自带的脚本。

## 核心事实

- **FreeCAD 不能直接读取 .sldprt / .sldasm**：SolidWorks 格式是封闭专有格式。
- **必须借助中间格式**：STEP (.step/.stp) 或 Parasolid (.x_t/.x_b)。
- **推荐 STEP AP214**：通用、保留几何、装配层级、颜色信息。
- **特征/参数/配合关系会丢失**：中间格式只传递几何和层级。

## 配套脚本

脚本位于 `fc/scripts/`：

- **SolidWorks 批量导出 STEP**：`fc/scripts/sw_batch_export_step.ps1`
- **FreeCAD 批量导入 STEP**：`fc/scripts/fc_batch_import_step.py`

## 完整工作流程

### 第一步：SolidWorks 批量导出 STEP

在安装了 SolidWorks 的电脑上运行：

```powershell
# 以管理员身份运行 PowerShell（首次需要设置执行策略）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 执行脚本
& "d:\桌面文件\fc\scripts\sw_batch_export_step.ps1" -SourceDir "D:\桌面文件\模切机收纸机构"
```

输出目录：`<SourceDir>\STEP_Output\`

脚本行为：
- 递归扫描源目录下所有 `.sldprt` 和 `.sldasm`
- 调用 SolidWorks COM API（`SldWorks.Application`）打开文件
- 导出为 `.step`，保持原目录结构
- 生成 `export_log.txt` 和 `export_errors.txt`

### 第二步：FreeCAD 批量导入并保存 FCStd

STEP 导出完成后运行：

```powershell
& "C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe" "d:\桌面文件\fc\scripts\fc_batch_import_step.py"
```

输出目录：`<SourceDir>\FCStd_Output\`

脚本行为：
- 递归扫描 `STEP_Output` 下的 `.step`/`.stp`
- 导入 FreeCAD 为独立文档
- 根据文件名关键词自动分配颜色（齿轮/轴/摆杆/板等）
- 按原目录结构创建 Group
- 保存为 `.FCStd`

## 颜色分类规则

| 类型 | 关键词 | 颜色 |
|------|--------|------|
| 齿轮 | 齿轮、gear | 铜色 (0.80, 0.60, 0.20) |
| 轴/轴承 | 轴、shaft、轴承、bearing、键、销 | 蓝色 (0.20, 0.40, 0.80) |
| 摆杆/连杆 | 摆杆、连杆、摆臂、arm、rod、link | 绿色 (0.20, 0.70, 0.30) |
| 板/盖板 | 板、plate、盖板、cover、端盖、垫片 | 橙色 (0.90, 0.50, 0.20) |
| 机架/箱体 | 纸板、paper、箱座、箱盖、机架 | 灰色 (0.75, 0.75, 0.75) |
| 默认 | 其他 | 灰色 (0.60, 0.60, 0.60) |

## 注意事项

1. **必须本机安装 SolidWorks**：第一步无法在没有 SolidWorks 的环境中运行。
2. **装配体配合关系会丢失**：STEP 只保留零件层级和几何。
3. **零件参数会丢失**：到 FreeCAD 后是 dumb solid。
4. **headless 模式下 GUI 数据不会自动注入**：需配合 `fc-gui-injection` skill 处理。
5. **中文路径**：脚本使用 PowerShell/FreeCAD 标准路径处理，已验证支持中文。

## 反向流程（FreeCAD → SolidWorks）

1. 在 FreeCAD 中完成建模和 GUI 注入
2. 使用 `fc export step` 或 FreeCAD GUI 导出为 STEP AP214 / Parasolid (.x_t)
3. 在 SolidWorks 中：文件 → 打开 → 选择 STEP/.x_t
4. SolidWorks 会将其作为输入特征导入

## 故障排查

### SolidWorks COM 连接失败
- 确认 SolidWorks 已安装
- 尝试先手动启动 SolidWorks，再运行脚本（脚本会优先连接已运行实例）
- 检查是否有杀毒软件阻止 COM 调用

### SaveAs 返回失败
- 可能是输出目录权限问题
- 可能是文件名过长或包含特殊字符
- 检查 `export_errors.txt`

### FreeCAD 导入后对象为空
- 检查 STEP 文件是否损坏
- 用 FreeCAD GUI 单独打开该 STEP 文件验证
