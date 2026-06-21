# Task Plan: Phase 2 — 持久化会话模式

> 目标：FreeCAD GUI 子进程持久运行，多个 fc 命令共享同一文档状态，支持交互式查看和 TechDraw

## 目标声明

实现 `fc session start/stop/list` 命令，启动 FreeCAD GUI 子进程并内置 XML-RPC 服务器。
- 文档状态持久，不用每条命令带 `--project`
- FreeCAD GUI 可见，支持交互式查看
- TechDraw 命令可用（GUI 模式原生支持）
- 复用现有 RPCBackend 连接机制

## 关键设计决策

1. **会话目录**：`${project_dir}/.fc_sessions/`（不占用 C 盘），可通过 `FC_SESSION_DIR` 环境变量覆盖
2. **RPC 端口**：默认 9875（复用 RPCBackend 默认端口），多会话自动分配 9876, 9877...
3. **不破坏现有 session 命令**：现有 `session undo/redo/snapshot/status/history` 保持不变，新增 `session start/stop/list`
4. **RPC 服务器脚本**：作为独立 Python 文件，由 FreeCAD GUI 启动时加载，在后台线程运行
5. **会话隔离**：每个会话独立 FreeCAD 子进程 + 独立端口 + 独立会话元数据文件

## 阶段

### 阶段 2.1: 创建 SessionManager 核心类 [complete]
- [x] 创建 `packages/core/src/fc_core/session.py`
- [x] 实现 `SessionInfo` dataclass（name, pid, port, mode, started_at, project_path, freecad_path）
- [x] 实现 `SessionManager` 类骨架（start/stop/list/status/get_backend 方法签名）
- [x] 实现会话目录管理（`_get_session_dir`, `_get_session_file`）
- [x] 实现会话元数据持久化（`_save_session`, `_load_session`, `_delete_session`）
- [x] 单元测试 `packages/core/tests/test_session.py` — 30 tests passed
- [x] 导出到 `fc_core/__init__.py`
- [x] 验证不破坏现有测试：457 passed, 8 skipped（集成测试需真实 FreeCAD）

### 阶段 2.2: 实现 FreeCAD RPC 服务器脚本 [complete]
- [x] 创建 `packages/core/src/fc_core/scripts/fc_rpc_server.py`
- [x] 实现 `FCRPCServer` 类（基于 `xmlrpc.server.SimpleXMLRPCServer`）
- [x] 注册方法：ping, get_version, execute_code, create_document, open_document, save_document, get_objects, get_object, create_object, edit_object, delete_object, import_file, shutdown
- [x] 在 FreeCAD GUI 主线程外启动服务器线程（`threading.Thread(daemon=True)`）
- [x] 支持命令行参数：`--port`, `--host`, `--session-name`
- [x] 实现 `find_free_port` 辅助函数
- [x] 单元测试 `packages/core/tests/test_rpc_server.py` — 25 tests passed
- [x] 修复 stop() 线程清理 bug（is_alive() False 时未置 None）

### 阶段 2.3: 实现 SessionManager 启动/停止逻辑 [complete]
- [x] 实现 `start(name, mode='gui', port=None, project=None)`：
  - 查找 FreeCAD.exe（GUI 版本，复用 `find_freecad(gui=True)`）
  - 分配端口（如未指定，从 9875 递增找可用端口）
  - 构造启动命令：`freecad fc_rpc_server.py --port <port> --session-name <name>`
  - 启动子进程（`subprocess.Popen`，非阻塞）
  - 轮询 ping 直到 RPC 服务器就绪（超时 30s）
  - 保存会话信息到磁盘
- [x] 实现 `stop(name)`：
  - 读取会话信息
  - 优先通过 RPC 调用 `shutdown` 方法优雅关闭
  - 失败则 `subprocess.terminate()` 强制关闭
  - 清理会话文件
- [x] 实现 `list()` 和 `status(name)`
- [x] 实现 `get_backend(name)` → 返回连接到该会话的 RPCBackend
- [x] 单元测试（mock subprocess.Popen 和 ping 逻辑）— 43 tests passed

### 阶段 2.4: 集成到 CLI - fc session start/stop/list 命令 [complete]
- [x] 在 `session_cmd.py` 添加 `start`, `stop`, `list` 子命令
- [x] `fc session start --name X [--mode gui] [--port N] [--project Y]`
- [x] `fc session stop [--name X]`（默认停止 --session 指定的会话）
- [x] `fc session list` — 列出所有活动会话
- [x] 添加 `--session X` 全局选项到 main.py，使命令路由到指定会话的 RPCBackend
- [x] 统一 `get_backend()` 函数，修改所有 18 个命令模块的 `_get_backend()` 委托给它
- [x] 单元测试（17 个新测试：start 7 + stop 4 + list 3 + routing 3）
- [x] 验证不破坏现有测试：CLI 557 passed, Core 502 passed, 8 skipped

### 阶段 2.5: 集成到 fc_runtime Executor [complete]
- [x] Executor 添加 `session: str | None = None` 参数
- [x] execute_task/execute_direct 构建命令时注入 `--session X` 标志
- [x] session 优先级高于 backend 参数（同时指定时走 session 路由）
- [x] Planner.plan 接受 `session` 参数，记录到 `plan.context["session"]`
- [x] 单元测试（8 个新测试：参数/注入/优先级/direct/plan/context）
- [x] 验证不破坏现有功能：Runtime 295 passed

### 阶段 2.6: 端到端验证 [complete] ✅
- [x] 启动真实 FreeCAD GUI，会话成功（PID=15264, Port=9875）
- [x] RPC 服务器在 FreeCAD GUI 中正确运行
- [x] `ping()` 方法返回 True
- [x] `execute_code()` 执行 Python 代码成功（创建文档、创建几何体）
- [x] `get_objects()` 返回完整对象属性（TestBox, 50x30x20mm）
- [x] `fc --session e2e_test session list` CLI 路由成功
- [x] 会话停止后 FreeCAD GUI 正确关闭，端口释放
- [x] 修复中文路径问题（复制脚本到 ASCII 临时路径）
- [x] 修复 FreeCADCmd 不支持自定义参数问题（改用环境变量）

## 遇到的错误
| 错误 | 尝试次数 | 解决方案 |
|------|---------|---------|
| stop() 线程未清理 | 1 | is_alive() False 时也置 None |

## Phase 3: SVG 工程图自动标注 [in_progress]

### 目标
实现不依赖 FreeCAD TechDraw 的纯 Python 工程图 SVG 生成器，支持尺寸标注、形位公差、表面粗糙度、焊接符号和标题栏。

### 阶段 3.1: 核心 SVG 生成器 [complete]
- [x] 创建 `packages/core/src/fc_core/drawing.py`
- [x] 实现 `EngineeringDrawingSVG` 类：
  - 初始化：shape、scale、page_size
  - 三视图投影（front/top/side）
  - 基于 Part.Shape 的 BoundBox、顶点、边数据
- [x] 支持 A3/A4 图幅
- [x] 单元测试：投影正确性、比例、页面边界

### 阶段 3.2: 尺寸标注 [complete]
- [x] 线性尺寸（含引线、箭头、偏移）
- [x] 直径尺寸（φ 前缀，穿过圆心）
- [x] 半径尺寸（R 前缀，圆心到圆弧）
- [x] 角度尺寸（弧线 + 两条引线）
- [x] 标注线、箭头、文字
- [x] 单元测试

### 阶段 3.3: 工程符号 [complete]
- [x] 表面粗糙度符号（GB/T 131 基本图形 + Ra 值 + 加工方法）
- [x] 形位公差框格（三格：符号 / 公差值 / 基准，可选引线）
- [x] 焊接符号（参考线 + 箭头 + V/Y/角焊图形 + 双侧标记）
- [x] 单元测试

### 阶段 3.4: 标题栏与出图 [complete]
- [x] GB/T 标题栏（180mm×56mm 分格：单位/图样名称/设计/审核 + 材料/比例/重量/数量/图号/版本/日期）
- [x] 图框、边框
- [x] 保存 SVG
- [x] 单元测试

### 阶段 3.5: CLI 集成 [complete]
- [x] 添加 `fc draft svg` 命令（输入 .json/.FCStd/.step/.stp，输出 SVG）
- [x] 支持从 JSON 直接加载 ShapeData
- [x] 支持从 FCStd/STEP 通过 backend 提取 shape
- [x] 自动三视图布局 + 标题栏字段
- [x] CLI 支持参数：--scale, --page, --title, --material, --weight 等
- [x] 单元测试

### 阶段 3.6: 端到端验证 [complete]
- [x] JSON 输入生成 SVG 成功（test_shape.json → test_drawing.svg）
- [x] CLI 单元测试通过（3 个 svg 测试）
- [ ] FCStd/STEP 输入需真实 FreeCAD 环境（当前环境无 FreeCAD）
- [ ] DBY250 减速器工程图待真实 FreeCAD 环境验证

## 关键约束
- 不破坏现有 466 个测试（Phase 1 成果）
- 不占用 C 盘（会话目录用项目目录或环境变量）
- 遵循 Karpathy 编码规范
- 中文注释
- 复用现有 RPCBackend，不重复造轮子
- FreeCAD GUI 子进程必须非阻塞（Popen 而非 run）
