# fc — Agent Native FreeCAD CLI

> 世界上最完整的 AI Agent 友好的 FreeCAD 命令行工具

`fc` 是一个为 AI Agent 原生设计的 FreeCAD 命令行工具，支持 258+ 命令，覆盖 FreeCAD 所有工作台。

## 特性

- 🤖 **Agent First**: 所有命令返回结构化 JSON，AI Agent 可直接解析
- 🔧 **CLI First**: 完整的命令行界面，支持 REPL、Shell 补全、配置管理
- 📡 **MCP Native**: 内置 MCP Server，与 Claude Desktop、Cursor 等无缝集成
- 🔌 **Plugin First**: 插件系统支持动态扩展
- 🤖 **Automation First**: `fc agent` 命令支持自然语言自动建模

## 快速开始

```bash
# 安装
pip install -e .

# 创建新文档
fc document new --name "MyPart"

# 添加长方体
fc part add box --name "Base" --param length=100 --param width=80 --param height=20

# 添加圆柱
fc part add cylinder --name "Hole" --param radius=5 --param height=20 --position 50,40,0

# 布尔运算（打孔）
fc part boolean cut --base Base --tool Hole

# 导出 STEP
fc export step --output model.step

# 导出 STL
fc export stl --output model.stl

# Agent 模式
fc agent "设计一个法兰盘，外径100mm，内径50mm，厚度10mm，均布6个直径10mm的螺栓孔"
```

## 命令概览

| 命令组 | 命令数 | 说明 |
|--------|--------|------|
| `document` | 6 | 文档管理（新建/打开/保存/信息） |
| `part` | 29 | 3D 基础实体（长方体/圆柱/球/锥/环）+ 布尔运算 + 变换 |
| `sketch` | 26 | 2D 草图（几何图形 + 约束 + 编辑） |
| `body` | 38 | PartDesign 特征（凸台/凹槽/倒角/孔/阵列） |
| `export` | 12 | 导出（STEP/IGES/STL/OBJ/DXF/SVG/PDF/glTF/3MF） |
| `import` | 7 | 导入（STEP/IGES/STL/OBJ/DXF/BREP） |
| `execute` | 2 | 执行 Python 代码/宏文件 |
| `session` | 4 | 会话管理（撤销/重做/状态） |

## 架构

```
packages/
├── core/        # 后端抽象 + FreeCAD API 封装
├── cli/         # 命令行框架 + 258+ 命令
├── mcp/         # MCP Server + Tool Registry
├── runtime/     # Agent Runtime + Planning + Self-Correction
└── test/        # 集成测试 + CAD 验证
```

## JSON 输出（AI Agent 模式）

所有命令支持 `--json` 输出：

```bash
fc --json part add box --name "Base" --param length=100 --param width=80 --param height=20
```

```json
{
  "status": "ok",
  "operation": "object_create",
  "data": {
    "name": "Base",
    "type_id": "Part::Box",
    "dimensions": {"length": 100, "width": 80, "height": 20},
    "volume": 160000.0
  },
  "message": "Created Part::Box: Base"
}
```

## MCP 配置

在 Claude Desktop 配置中添加：

```json
{
  "mcpServers": {
    "freecad": {
      "command": "fc-mcp",
      "args": ["--backend", "headless"]
    }
  }
}
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check .
ruff format .
```

## 许可证

MIT
