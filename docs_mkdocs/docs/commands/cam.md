---
name: fc-cam
description: FreeCAD CAM 制造命令 — 任务/刀具/刀路/后处理/仿真/设置表/检查/验证。用于数控加工编程。
---

# fc-cam — FreeCAD CAM 制造 CLI 命令

## 命令组概览（10 个命令）

| 命令 | 说明 |
|------|------|
| `cam job` | 创建 CAM 任务 |
| `cam tool` | 定义刀具 |
| `cam toolpath` | 生成刀路 |
| `cam postprocess` | 后处理为 G 代码 |
| `cam simulate` | 仿真刀路 |
| `cam list` | 列出 CAM 对象 |
| `cam show` | 显示任务详情 |
| `cam setup-sheet` | 创建设置表 |
| `cam inspect` | 检查刀路 |
| `cam verify` | 验证刀路 |

## 典型工作流

### 工作流 1：基本铣削
```bash
fc document new --name Part
fc part add box --name Stock -P Length=100 -P Width=80 -P Height=20
fc cam job --name MyJob --model Stock
fc cam tool --name EndMill6 --type endmill --diameter 6 --length 25 --speed 12000 --feed 1000
fc cam toolpath --job MyJob --type profile --depth 5 --step-down 2
fc cam simulate --job MyJob
fc cam postprocess --job MyJob --output part.nc
```

### 工作流 2：钻孔
```bash
fc cam tool --name Drill5 --type drill --diameter 5 --length 30
fc cam toolpath --job MyJob --type drill --depth 20 --step-down 5
fc cam verify --job MyJob --check-gouge
```

## 注意事项

- 所有命令支持 `--json` 输出
- `cam toolpath` 支持 profile/pocket/drill/engrave/adaptive/helix/slot/3d_pocket
- `cam tool` 支持 endmill/ballmill/chamfer/drill/reamer/tap
- `cam postprocess` 输出 G 代码文件
- `cam verify` 可检查 gouge 和 collision
