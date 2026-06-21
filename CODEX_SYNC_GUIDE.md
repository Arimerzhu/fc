# Codex 同步指南

本项目已通过 `pip install` 安装 `fc-mcp`（v0.1.0），`fc-mcp` 命令已加入 PATH。

## 现状（自动完成部分）

- ✅ 项目级 Codex 配置已创建：`d:\桌面文件\fc\.codex\config.toml`
- ✅ 项目级 MCP 配置已创建：`d:\桌面文件\fc\.codex\mcp-configs\mcp-servers.json`
- ✅ `fc-mcp --help` 可正常调用

## 需要手动完成（沙盒权限限制）

Codex 全局配置 `c:\Users\Lenovo\.codex\config.toml` 需手动更新：

### 1. 添加 fc-mcp MCP 服务器

在 `c:\Users\Lenovo\.codex\config.toml` 末尾（`[desktop.open-in-target-preferences]` 之前）追加：

```toml
[mcp_servers.fc-mcp]
enabled = true
command = "fc-mcp"
args = []
startup_timeout_sec = 60
description = "Agent Native FreeCAD CLI MCP Server (fc v0.1.0) — document, part, sketch, assembly, techdraw, export, draft svg, session management"
```

### 2. 启用 fc 项目为 trust_level = "trusted"

在 `c:\Users\Lenovo\.codex\config.toml` 中追加：

```toml
[projects.'d:\桌面文件\fc']
trust_level = "trusted"

[projects.'D:\桌面文件\fc']
trust_level = "trusted"
```

### 3. 同步技能到 `~/.codex/skills/fc/`

在 PowerShell 中执行（直接复制本项目 `docs/skills/` 到 Codex 全局技能目录）：

```powershell
$dest = "c:\Users\Lenovo\.codex\skills\fc"
New-Item -ItemType Directory -Path $dest -Force
Copy-Item -Path "d:\桌面文件\fc\docs\skills\*.md" -Destination $dest -Recurse -Force
```

或者使用 `codex` CLI 的技能安装命令：

```bash
codex skills install "d:\桌面文件\fc\docs\skills\fc"
```

### 4. 验证

启动 Codex：

```bash
# 重启 Codex 让 MCP 重新加载
codex --version
# 启动后通过 /mcp 命令查看 fc-mcp 是否已加载
```

或在 Codex 中执行：

```bash
fc --version
fc draft svg --help
```

## 已存在 freecad MCP 服务器说明

`c:\Users\Lenovo\.codex\config.toml` 已有 `[mcp_servers.freecad]` 配置（指向 `E:\Project\freecad-mcp` 的 `freecad_mcp.server_cli_anything`）。

如需使用本项目的 `fc-mcp` 替代，请先注释或删除原 freecad 配置，或重命名为 `freecad-cli`：

```toml
# [mcp_servers.freecad]    # 注释旧的 freecad-mcp
# enabled = true
# command = "..."
# ...

[mcp_servers.fc-mcp]        # 本项目的 fc-mcp
enabled = true
command = "fc-mcp"
args = []
```
