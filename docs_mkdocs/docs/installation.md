# 安装指南

## 前置要求

- **Python 3.12+**
- **FreeCAD 1.1+** ([下载](https://www.freecad.org/downloads.php))

## 安装 fc

### 方式一：pip 安装（推荐）

```bash
pip install fc
```

### 方式二：源码安装

```bash
git clone https://github.com/zoo/fc.git
cd fc
uv sync --all-packages
```

## 配置 FreeCAD 路径

如果 FreeCAD 不在系统 PATH 中，需要指定路径：

```bash
# 临时设置
fc --freecad-path "C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe" document new --name Test --json

# 或设置环境变量
set FREECAD_PATH=C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe
```

## 验证安装

```bash
# 测试核心功能
fc document new --name Test --json
fc part add box --name Box --param Length=10 --param Width=10 --param Height=10 --json
fc document save --output test.FCStd --json
```

## 平台特定说明

### Windows

```powershell
# 使用 winget 安装 FreeCAD
winget install FreeCAD.FreeCAD

# 或使用 Chocolatey
choco install freecad
```

### macOS

```bash
brew install --cask freecad
```

### Linux (Ubuntu/Debian)

```bash
sudo apt install freecad
```

## 下一步

- [快速入门](getting-started.md) — 5 分钟上手
- [命令参考](commands/index.md) — 完整命令文档
- [AI Agent 集成](agent/SKILL.md) — AI 使用指南
