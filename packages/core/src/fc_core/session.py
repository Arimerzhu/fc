"""FreeCAD 持久化会话管理器。

管理 FreeCAD GUI 子进程的生命周期，每个会话独立端口和进程。
会话元数据持久化到 ${project_dir}/.fc_sessions/ 或 ${FC_SESSION_DIR}。

典型用法::

    mgr = SessionManager(project_dir="/path/to/project")
    info = mgr.start("reducer", mode="gui")  # 启动 FreeCAD GUI + RPC 服务器
    backend = mgr.get_backend("reducer")      # 返回 RPCBackend
    mgr.stop("reducer")                        # 关闭会话
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """会话元数据。"""

    name: str
    pid: int
    port: int
    mode: str  # 'gui' 或 'headless'
    started_at: float
    project_path: str
    freecad_path: str
    temp_script_path: str | None = None  # 如果脚本被复制到 ASCII 路径，记录此路径以便清理

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionInfo":
        return cls(
            name=data["name"],
            pid=int(data["pid"]),
            port=int(data["port"]),
            mode=data.get("mode", "gui"),
            started_at=float(data.get("started_at", 0)),
            project_path=data.get("project_path", ""),
            freecad_path=data.get("freecad_path", ""),
        )


# 会话名只允许字母、数字、下划线、连字符，防止路径遍历
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


class SessionManager:
    """FreeCAD 持久化会话管理器。

    管理多个 FreeCAD 子进程会话，每个会话有独立端口和元数据文件。
    会话目录优先使用环境变量 FC_SESSION_DIR，否则用 ${project_dir}/.fc_sessions/。
    """

    DEFAULT_PORT = 9875
    DEFAULT_MODE = "gui"

    def __init__(self, project_dir: str | None = None):
        self._project_dir = project_dir or os.getcwd()

    # ── 目录与文件管理 ──

    def _get_session_dir(self) -> str:
        """获取会话目录。

        优先环境变量 FC_SESSION_DIR，否则用 ${project_dir}/.fc_sessions/。
        """
        env_dir = os.environ.get("FC_SESSION_DIR")
        if env_dir:
            return env_dir
        return os.path.join(self._project_dir, ".fc_sessions")

    def _get_session_file(self, name: str) -> str:
        """获取会话元数据文件路径。"""
        if not _SAFE_NAME_RE.match(name):
            raise ValueError(
                f"无效的会话名: {name}（只允许字母、数字、下划线、连字符）"
            )
        return os.path.join(self._get_session_dir(), f"{name}.json")

    def _save_session(self, info: SessionInfo) -> None:
        """保存会话元数据到磁盘。"""
        session_dir = self._get_session_dir()
        os.makedirs(session_dir, exist_ok=True)
        session_file = self._get_session_file(info.name)
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(info.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"会话元数据已保存: {session_file}")

    def _load_session(self, name: str) -> SessionInfo | None:
        """从磁盘加载会话元数据。文件不存在或损坏返回 None。"""
        try:
            session_file = self._get_session_file(name)
        except ValueError:
            return None
        if not os.path.isfile(session_file):
            return None
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return SessionInfo.from_dict(data)
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.warning(f"加载会话 {name} 失败: {e}")
            return None

    def _delete_session(self, name: str) -> None:
        """删除会话元数据文件。"""
        try:
            session_file = self._get_session_file(name)
        except ValueError:
            return
        if os.path.isfile(session_file):
            os.unlink(session_file)
            logger.info(f"会话元数据已删除: {session_file}")

    # ── 查询接口 ──

    def list(self) -> list[SessionInfo]:
        """列出所有活动会话。"""
        session_dir = self._get_session_dir()
        if not os.path.isdir(session_dir):
            return []
        sessions: list[SessionInfo] = []
        for fname in os.listdir(session_dir):
            if fname.endswith(".json"):
                name = fname[:-5]  # 去掉 .json 后缀
                info = self._load_session(name)
                if info is not None:
                    sessions.append(info)
        return sessions

    def status(self, name: str) -> SessionInfo | None:
        """查询指定会话状态。不存在返回 None。"""
        return self._load_session(name)

    # ── 生命周期管理 ──

    def start(
        self,
        name: str,
        mode: str = "gui",
        port: int | None = None,
        project: str | None = None,
    ) -> SessionInfo:
        """启动 FreeCAD 会话。

        启动 FreeCAD GUI 子进程并加载 RPC 服务器脚本，等待服务器就绪后保存会话元数据。

        Args:
            name: 会话名（唯一标识，只允许字母/数字/下划线/连字符）
            mode: 'gui' 或 'headless'（当前只支持 'gui'）
            port: RPC 端口，None 则从 9875 自动分配
            project: 项目文件路径（可选）

        Returns:
            SessionInfo 会话元数据

        Raises:
            ValueError: 会话名无效或会话已存在
            FileNotFoundError: FreeCAD 未安装
            TimeoutError: RPC 服务器启动超时
        """
        # 验证会话名
        if not _SAFE_NAME_RE.match(name):
            raise ValueError(
                f"无效的会话名: {name}（只允许字母、数字、下划线、连字符）"
            )

        # 检查会话是否已存在
        existing = self._load_session(name)
        if existing is not None:
            raise ValueError(f"会话已存在: {name}（先 stop 再 start）")

        # 查找 FreeCAD 可执行文件
        from fc_core.backend import find_freecad

        gui_required = mode == "gui"
        freecad_path = find_freecad(gui_required=gui_required)

        # 分配端口
        from fc_core.scripts.fc_rpc_server import find_free_port

        host = "localhost"
        if port is None:
            port = find_free_port(host, start=self.DEFAULT_PORT)

        # 获取 RPC 服务器脚本路径
        from fc_core.scripts import fc_rpc_server as rpc_module

        script_path = rpc_module.__file__
        if script_path is None:
            raise FileNotFoundError("无法定位 fc_rpc_server.py 脚本")

        # 如果脚本路径包含非 ASCII 字符（如中文路径），FreeCADCmd 会解析失败
        # 将脚本复制到临时 ASCII 路径
        _temp_script: str | None = None
        try:
            script_path.encode("ascii")
        except UnicodeEncodeError:
            import tempfile
            _temp_script = os.path.join(
                tempfile.gettempdir(), f"fc_rpc_server_{name}_{port}.py"
            )
            logger.info(f"复制脚本到 ASCII 路径: {_temp_script}")
            import shutil
            shutil.copy(script_path, _temp_script)
            script_path = _temp_script

        # 构造启动命令
        # FreeCAD 会通过环境变量传递配置给 RPC 服务器脚本
        cmd = [freecad_path, script_path]

        # 设置环境变量（FreeCAD 会将这些传递给 Python 子进程）
        env = dict(os.environ)
        env["FC_RPC_HOST"] = host
        env["FC_RPC_PORT"] = str(port)
        env["FC_RPC_SESSION"] = name

        logger.info(f"启动 FreeCAD 会话: {' '.join(cmd)}")
        logger.info(f"  FC_RPC_HOST={host}, FC_RPC_PORT={port}, FC_RPC_SESSION={name}")

        # 启动子进程（非阻塞）
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,  # 传递 RPC 配置环境变量
            # Windows: 不创建新控制台窗口
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
        )

        # 等待 RPC 服务器就绪
        if not self._wait_for_server(host, port, timeout=30.0):
            # 服务器未就绪，清理子进程
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                pass
            raise TimeoutError(
                f"RPC 服务器在 30s 内未就绪 (host={host}, port={port})"
            )

        # 创建并保存会话信息
        info = SessionInfo(
            name=name,
            pid=proc.pid,
            port=port,
            mode=mode,
            started_at=time.time(),
            project_path=project or "",
            freecad_path=freecad_path,
            temp_script_path=_temp_script,
        )
        self._save_session(info)
        logger.info(f"会话 '{name}' 已启动 (pid={info.pid}, port={info.port})")
        return info

    def stop(self, name: str) -> bool:
        """停止 FreeCAD 会话。

        优先通过 RPC 调用 shutdown 优雅关闭，失败则强制终止进程。

        Args:
            name: 会话名

        Returns:
            True 表示会话已停止（包括不存在的情况）
        """
        info = self._load_session(name)
        if info is None:
            logger.warning(f"会话不存在: {name}")
            return True  # 不存在视为已停止

        # 1. 尝试 RPC shutdown（优雅关闭）
        try:
            import xmlrpc.client

            proxy = xmlrpc.client.ServerProxy(
                f"http://localhost:{info.port}",
                allow_none=True,
            )
            proxy.shutdown()
            time.sleep(1.0)  # 等待服务器关闭
            logger.info(f"会话 '{name}' 通过 RPC shutdown 关闭")
        except Exception as e:
            logger.warning(f"RPC shutdown 失败，强制终止: {e}")
            # 2. 强制终止进程
            self._terminate_process(info.pid)

        # 清理会话文件
        self._delete_session(name)

        # 清理临时脚本
        if info.temp_script_path and os.path.isfile(info.temp_script_path):
            try:
                os.remove(info.temp_script_path)
                logger.info(f"临时脚本已清理: {info.temp_script_path}")
            except OSError:
                pass

        logger.info(f"会话 '{name}' 已停止")
        return True

    def get_backend(self, name: str):
        """获取连接到指定会话的 RPCBackend。

        Args:
            name: 会话名

        Returns:
            RPCBackend 实例（未自动 connect，由调用者决定）

        Raises:
            ValueError: 会话不存在
        """
        info = self._load_session(name)
        if info is None:
            raise ValueError(f"会话不存在: {name}")

        from fc_core.backend import RPCBackend

        return RPCBackend(host="localhost", port=info.port)

    # ── 内部辅助方法 ──

    def _wait_for_server(
        self, host: str, port: int, timeout: float = 30.0
    ) -> bool:
        """轮询 ping 直到 RPC 服务器就绪。

        Args:
            host: 服务器地址
            port: 服务器端口
            timeout: 超时秒数

        Returns:
            True 表示服务器已就绪，False 表示超时
        """
        import xmlrpc.client

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                proxy = xmlrpc.client.ServerProxy(
                    f"http://{host}:{port}",
                    allow_none=True,
                )
                if proxy.ping():
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def _terminate_process(self, pid: int) -> None:
        """强制终止进程（跨平台）。"""
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True,
                    timeout=10,
                )
            else:
                import signal

                os.kill(pid, signal.SIGTERM)
        except Exception as e:
            logger.warning(f"终止进程 {pid} 失败: {e}")
