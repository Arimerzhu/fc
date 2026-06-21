# MCP 配置

fc 提供 MCP (Model Context Protocol) 服务器，兼容 Claude Desktop、Cursor、VS Code 等 AI 工具。

## 快速配置

### Claude Desktop

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "fc": {
      "command": "python",
      "args": ["-m", "fc_mcp"],
      "cwd": "/path/to/fc"
    }
  }
}
```

### Cursor

在 Cursor Settings → MCP 中添加：

```json
{
  "fc": {
    "command": "python",
    "args": ["-m", "fc_mcp"]
  }
}
```

### VS Code (Copilot)

在 `.vscode/settings.json` 中：

```json
{
  "mcp": {
    "servers": {
      "fc": {
        "command": "python",
        "args": ["-m", "fc_mcp"]
      }
    }
  }
}
```

## 工具模块

MCP 服务器提供 6 个工具模块，约 50 个工具：

| 模块 | 工具数 | 说明 |
|------|--------|------|
| document | 6 | 文档操作 |
| geometry | 12 | 几何体创建与操作 |
| sketch | 10 | 草图操作 |
| export | 8 | 文件导出 |
| execute | 2 | Python 执行 |
| query | 12 | 查询与信息 |

## 启动 MCP 服务器

```bash
# 直接启动
python -m fc_mcp

# 或指定主机/端口
python -m fc_mcp --host 0.0.0.0 --port 8080
```

## 工具调用示例

```json
{
  "name": "fc_part_add",
  "arguments": {
    "type": "box",
    "name": "MyBox",
    "params": {"Length": 100, "Width": 50, "Height": 20}
  }
}
```
