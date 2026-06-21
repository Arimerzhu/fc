# 示例 4：参数化盒子设计

**难度**: 中等
**命令组**: document, spreadsheet, sketch, body, export
**步骤数**: 12

## 需求

使用参数化设计创建一个可调整尺寸的盒子：长=100，宽=50，高=30，壁厚=3，顶部开口。

## 阶段1: 工具选型

| 命令组 | 命令 | 用途 |
|--------|------|------|
| document | `document new` | 创建新文档 |
| spreadsheet | `spreadsheet create` | 创建参数表 |
| spreadsheet | `spreadsheet set` | 设置参数值 |
| spreadsheet | `spreadsheet alias` | 设置参数别名 |
| body | `body new` | 创建 Body |
| sketch | `sketch new` | 创建底面草图 |
| sketch | `sketch add-rect` | 绘制外轮廓 |
| sketch | `sketch close` | 关闭草图 |
| body | `body pad` | 拉伸主体 |
| body | `body shell` | 抽壳形成盒子 |
| export | `export step` | 导出 STEP |
| document | `document save` | 保存项目 |

## 阶段2: 任务拆解

1. 创建新文档 `ParamBoxDoc`
2. 创建参数表 `Params`
3. 定义参数：Length=100, Width=50, Height=30, Thickness=3
4. 创建 Body `BoxBody`
5. 创建底面草图 `BaseSketch`：矩形外轮廓，尺寸由参数驱动
6. 关闭草图
7. 拉伸主体 `MainPad`：高度 = Height（30mm）
8. 抽壳 `ShellResult`：厚度 = Thickness（3mm），移除顶面
9. 导出 STEP 文件
10. 保存项目

## 阶段3: 坐标与依赖计算

### 参数定义

| 参数名 | 单元格 | 值 | 别名 |
|--------|--------|------|------|
| Length | A1 | 100 | 盒长 |
| Width | A2 | 50 | 盒宽 |
| Height | A3 | 30 | 盒高 |
| Thickness | A4 | 3 | 壁厚 |

### 几何计算

- 底面矩形中心: `0, 0`
- 底面矩形范围: X[-50, 50], Y[-25, 25]（以中心为基准）
- 拉伸高度: 30mm（从 Z=0 到 Z=30）
- 抽壳厚度: 3mm
- 抽壳移除面: 顶面（面索引 0）
- 内腔尺寸: 长=94, 宽=44, 高=27（每边减去壁厚 3mm）

### 步骤依赖

| 步骤 | 操作 | 依赖 | 输出 |
|------|------|------|------|
| 1 | document new | 无 | `ParamBoxDoc` |
| 2 | spreadsheet create | 文档 | `Params` |
| 3 | spreadsheet set x4 | `Params` | 参数值 |
| 4 | spreadsheet alias x4 | 参数已设置 | 别名 |
| 5 | body new | 文档 | `BoxBody` |
| 6 | sketch new | Body | `BaseSketch` |
| 7 | sketch add-rect | `BaseSketch` | 矩形 |
| 8 | sketch close | `BaseSketch` | 草图关闭 |
| 9 | body pad | 草图 | `MainPad` |
| 10 | body shell | `MainPad` | `ShellResult` |
| 11 | export step | 完成 | 文件 |
| 12 | document save | 完成 | 项目 |

## 阶段4: 依赖校验

- 参数表创建后才能设置参数值
- Body 创建后才能创建草图
- 草图关闭后才能 pad
- Pad 完成后才能 shell
- 所有依赖关系正确

## 阶段5: 命令输出

```bash
# 1. 创建新文档
fc document new --name ParamBoxDoc --json

# 2. 创建参数表
fc spreadsheet create --name Params --json

# 3. 设置参数值
fc spreadsheet set --sheet Params --cell A1 --value 100 --json
fc spreadsheet set --sheet Params --cell A2 --value 50 --json
fc spreadsheet set --sheet Params --cell A3 --value 30 --json
fc spreadsheet set --sheet Params --cell A4 --value 3 --json

# 4. 设置参数别名（便于后续引用）
fc spreadsheet alias --sheet Params --cell A1 --alias Length --json
fc spreadsheet alias --sheet Params --cell A2 --alias Width --json
fc spreadsheet alias --sheet Params --cell A3 --alias Height --json
fc spreadsheet alias --sheet Params --cell A4 --alias Thickness --json

# 5. 创建 Body
fc body new --name BoxBody --json

# 6. 创建底面草图（矩形外轮廓）
fc sketch new --name BaseSketch --plane XY --json
fc sketch add-rect BaseSketch --corner -50,-25 --width 100 --height 50 --json

# 7. 关闭草图
fc sketch close BaseSketch --json

# 8. 拉伸主体（高度 30mm）
fc body pad BoxBody BaseSketch --length 30 --json

# 9. 抽壳（壁厚 3mm，移除顶面）
fc body shell BoxBody --thickness 3 --faces 0 --json

# 10. 导出 STEP 文件
fc export step --output parametric_box.step --overwrite --json

# 11. 保存项目文件
fc document save --output parametric_box.FCStd --json
```

## 完整命令序列

```bash
fc document new --name ParamBoxDoc --json
fc spreadsheet create --name Params --json
fc spreadsheet set --sheet Params --cell A1 --value 100 --json
fc spreadsheet set --sheet Params --cell A2 --value 50 --json
fc spreadsheet set --sheet Params --cell A3 --value 30 --json
fc spreadsheet set --sheet Params --cell A4 --value 3 --json
fc spreadsheet alias --sheet Params --cell A1 --alias Length --json
fc spreadsheet alias --sheet Params --cell A2 --alias Width --json
fc spreadsheet alias --sheet Params --cell A3 --alias Height --json
fc spreadsheet alias --sheet Params --cell A4 --alias Thickness --json
fc body new --name BoxBody --json
fc sketch new --name BaseSketch --plane XY --json
fc sketch add-rect BaseSketch --corner -50,-25 --width 100 --height 50 --json
fc sketch close BaseSketch --json
fc body pad BoxBody BaseSketch --length 30 --json
fc body shell BoxBody --thickness 3 --faces 0 --json
fc export step --output parametric_box.step --overwrite --json
fc document save --output parametric_box.FCStd --json
```

## 预期输出

```json
// 1. document new
{"status": "ok", "operation": "document_new", "data": {"name": "ParamBoxDoc"}, "message": "Document 'ParamBoxDoc' created"}

// 2. spreadsheet create
{"status": "ok", "operation": "spreadsheet_create", "data": {"name": "Params"}, "message": "Spreadsheet 'Params' created"}

// 3. spreadsheet set x4
{"status": "ok", "operation": "spreadsheet_set", "data": {"cell": "A1", "value": 100}, "message": "Cell A1 set to 100"}
{"status": "ok", "operation": "spreadsheet_set", "data": {"cell": "A2", "value": 50}, "message": "Cell A2 set to 50"}
{"status": "ok", "operation": "spreadsheet_set", "data": {"cell": "A3", "value": 30}, "message": "Cell A3 set to 30"}
{"status": "ok", "operation": "spreadsheet_set", "data": {"cell": "A4", "value": 3}, "message": "Cell A4 set to 3"}

// 4. spreadsheet alias x4
{"status": "ok", "operation": "spreadsheet_alias", "data": {"cell": "A1", "alias": "Length"}, "message": "Alias 'Length' set for A1"}
{"status": "ok", "operation": "spreadsheet_alias", "data": {"cell": "A2", "alias": "Width"}, "message": "Alias 'Width' set for A2"}
{"status": "ok", "operation": "spreadsheet_alias", "data": {"cell": "A3", "alias": "Height"}, "message": "Alias 'Height' set for A3"}
{"status": "ok", "operation": "spreadsheet_alias", "data": {"cell": "A4", "alias": "Thickness"}, "message": "Alias 'Thickness' set for A4"}

// 5. body new
{"status": "ok", "operation": "body_new", "data": {"name": "BoxBody"}, "message": "Body 'BoxBody' created"}

// 6-7. sketch
{"status": "ok", "operation": "sketch_new", "data": {"name": "BaseSketch"}, "message": "Sketch 'BaseSketch' created on XY plane"}
{"status": "ok", "operation": "sketch_add_rect", "data": {"indices": [0, 1, 2, 3]}, "message": "Rectangle added to 'BaseSketch'"}
{"status": "ok", "operation": "sketch_close", "data": {"status": "closed"}, "message": "Sketch 'BaseSketch' closed"}

// 8. body pad
{"status": "ok", "operation": "body_pad", "data": {"feature": "Pad"}, "message": "Pad created: length=30"}

// 9. body shell
{"status": "ok", "operation": "body_shell", "data": {"feature": "Shell"}, "message": "Shell created: thickness=3, removed faces: [0]"}

// 10. export step
{"status": "ok", "operation": "export_step", "data": {"file": "parametric_box.step", "size": 18923}, "message": "Exported to parametric_box.step"}

// 11. document save
{"status": "ok", "operation": "document_save", "data": {"path": "parametric_box.FCStd"}, "message": "Saved to parametric_box.FCStd"}
```

## 参数调整说明

修改盒子尺寸只需更新参数表中的值，然后重新生成：

```bash
# 打开已有项目
fc document open parametric_box.FCStd --json

# 修改参数
fc spreadsheet set --sheet Params --cell A1 --value 120 --json    # 长度改为 120
fc spreadsheet set --sheet Params --cell A2 --value 60 --json     # 宽度改为 60
fc spreadsheet set --sheet Params --cell A3 --value 40 --json     # 高度改为 40
fc spreadsheet set --sheet Params --cell A4 --value 4 --json      # 壁厚改为 4

# 重新导出
fc export step --output parametric_box_v2.step --overwrite --json
```
