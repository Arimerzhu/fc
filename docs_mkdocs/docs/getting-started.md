# 快速入门

## 5 分钟上手 fc

### 1. 安装

```bash
pip install fc
```

确保已安装 [FreeCAD 1.1+](https://www.freecad.org/downloads.php)。

### 2. 创建第一个模型

```bash
# 创建文档和盒子
fc document new --name MyPart --json
fc part add box --name Box --param Length=100 --param Width=50 --param Height=20 --json
fc export step --output my_part.step --json
```

### 3. 使用 AI Agent

```bash
# 自然语言 → CAD
fc agent "创建一个 100x50x20mm 的底板，中心有直径 10mm 的通孔"
```

### 4. 常用命令速查

| 意图 | 命令 |
|------|------|
| 创建盒子 | `fc part add box --name Box --param Length=10 --param Width=10 --param Height=10 --json` |
| 创建圆柱 | `fc part add cylinder --name Cyl --param Radius=5 --param Height=20 --json` |
| 布尔切割 | `fc part boolean cut --base Box --tool Cyl --name Result --json` |
| 导出 STEP | `fc export step --output model.step --json` |
| 导出 STL | `fc export stl --output model.stl --tolerance 0.05 --json` |
| 撤销 | `fc session undo --json` |
| 创建快照 | `fc session snapshot v1 --description "初始设计" --json` |

## 下一步

- [安装指南](installation.md) — 详细安装步骤
- [命令参考](commands/index.md) — 完整命令文档
- [AI Agent 集成](agent/SKILL.md) — AI 使用指南
- [示例库](examples/01_simple_box_with_hole.md) — 从简单到复杂的示例
