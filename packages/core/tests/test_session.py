"""SessionManager 单元测试。

覆盖：
- SessionInfo 序列化/反序列化
- 会话目录管理（默认路径、环境变量覆盖）
- 会话元数据持久化（保存/加载/删除）
- 查询接口（list/status）
- 路径遍历防护
"""

from __future__ import annotations

import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from fc_core.session import SessionInfo, SessionManager


# ── SessionInfo ──


class TestSessionInfo:
    """SessionInfo dataclass 测试。"""

    def test_creation(self):
        info = SessionInfo(
            name="test",
            pid=12345,
            port=9875,
            mode="gui",
            started_at=time.time(),
            project_path="/tmp/project",
            freecad_path="/usr/bin/freecad",
        )
        assert info.name == "test"
        assert info.pid == 12345
        assert info.port == 9875
        assert info.mode == "gui"

    def test_to_dict(self):
        info = SessionInfo(
            name="s1",
            pid=100,
            port=9876,
            mode="gui",
            started_at=1000.0,
            project_path="/p",
            freecad_path="/fc",
        )
        d = info.to_dict()
        assert d["name"] == "s1"
        assert d["pid"] == 100
        assert d["port"] == 9876
        assert d["mode"] == "gui"
        assert d["started_at"] == 1000.0
        assert d["project_path"] == "/p"
        assert d["freecad_path"] == "/fc"

    def test_from_dict(self):
        data = {
            "name": "s2",
            "pid": 200,
            "port": 9877,
            "mode": "headless",
            "started_at": 2000.0,
            "project_path": "/q",
            "freecad_path": "/fc2",
        }
        info = SessionInfo.from_dict(data)
        assert info.name == "s2"
        assert info.pid == 200
        assert info.port == 9877
        assert info.mode == "headless"

    def test_from_dict_missing_fields_uses_defaults(self):
        """from_dict 对缺失字段使用默认值。"""
        data = {"name": "s3", "pid": 300, "port": 9878}
        info = SessionInfo.from_dict(data)
        assert info.name == "s3"
        assert info.pid == 300
        assert info.port == 9878
        assert info.mode == "gui"  # 默认
        assert info.started_at == 0.0  # 默认
        assert info.project_path == ""  # 默认
        assert info.freecad_path == ""  # 默认

    def test_roundtrip(self):
        """to_dict → from_dict 往返一致。"""
        original = SessionInfo(
            name="roundtrip",
            pid=999,
            port=9880,
            mode="gui",
            started_at=12345.6,
            project_path="/path/to/proj",
            freecad_path="/path/to/fc",
        )
        d = original.to_dict()
        restored = SessionInfo.from_dict(d)
        assert restored == original


# ── SessionManager 目录管理 ──


class TestSessionDirManagement:
    """会话目录和文件路径管理。"""

    def test_default_session_dir(self, tmp_path):
        """默认会话目录是 ${project_dir}/.fc_sessions/。"""
        mgr = SessionManager(project_dir=str(tmp_path))
        assert mgr._get_session_dir() == str(tmp_path / ".fc_sessions")

    def test_env_var_overrides_session_dir(self, tmp_path, monkeypatch):
        """FC_SESSION_DIR 环境变量覆盖默认目录。"""
        custom_dir = str(tmp_path / "custom_sessions")
        monkeypatch.setenv("FC_SESSION_DIR", custom_dir)
        mgr = SessionManager(project_dir=str(tmp_path))
        assert mgr._get_session_dir() == custom_dir

    def test_session_file_path(self, tmp_path):
        """会话文件路径正确。"""
        mgr = SessionManager(project_dir=str(tmp_path))
        path = mgr._get_session_file("mysession")
        assert path == str(tmp_path / ".fc_sessions" / "mysession.json")

    def test_session_file_invalid_name_raises(self, tmp_path):
        """无效会话名（含路径分隔符等）抛出 ValueError。"""
        mgr = SessionManager(project_dir=str(tmp_path))
        with pytest.raises(ValueError, match="无效的会话名"):
            mgr._get_session_file("../escape")
        with pytest.raises(ValueError):
            mgr._get_session_file("name with spaces")
        with pytest.raises(ValueError):
            mgr._get_session_file("name/with/slash")

    def test_session_file_valid_names(self, tmp_path):
        """合法会话名：字母、数字、下划线、连字符。"""
        mgr = SessionManager(project_dir=str(tmp_path))
        for name in ["test", "my-session", "session_1", "ABC123", "a-b_c"]:
            path = mgr._get_session_file(name)
            assert path.endswith(f"{name}.json")


# ── SessionManager 元数据持久化 ──


class TestSessionPersistence:
    """会话元数据的保存、加载、删除。"""

    @pytest.fixture
    def manager(self, tmp_path):
        return SessionManager(project_dir=str(tmp_path))

    @pytest.fixture
    def sample_info(self):
        return SessionInfo(
            name="test_sess",
            pid=12345,
            port=9875,
            mode="gui",
            started_at=time.time(),
            project_path="/tmp/project",
            freecad_path="/usr/bin/freecad",
        )

    def test_save_and_load(self, manager, sample_info):
        """保存后能正确加载。"""
        manager._save_session(sample_info)
        loaded = manager._load_session("test_sess")
        assert loaded is not None
        assert loaded.name == sample_info.name
        assert loaded.pid == sample_info.pid
        assert loaded.port == sample_info.port
        assert loaded.mode == sample_info.mode

    def test_save_creates_directory(self, manager, sample_info):
        """保存时自动创建会话目录。"""
        session_dir = manager._get_session_dir()
        assert not os.path.isdir(session_dir)
        manager._save_session(sample_info)
        assert os.path.isdir(session_dir)

    def test_load_nonexistent_returns_none(self, manager):
        """加载不存在的会话返回 None。"""
        assert manager._load_session("nonexistent") is None

    def test_load_invalid_name_returns_none(self, manager):
        """无效会话名返回 None（不抛异常）。"""
        assert manager._load_session("../escape") is None
        assert manager._load_session("bad name") is None

    def test_load_corrupted_file_returns_none(self, manager, tmp_path):
        """损坏的 JSON 文件返回 None。"""
        session_dir = manager._get_session_dir()
        os.makedirs(session_dir, exist_ok=True)
        with open(os.path.join(session_dir, "corrupt.json"), "w") as f:
            f.write("{invalid json content")
        assert manager._load_session("corrupt") is None

    def test_delete_session(self, manager, sample_info):
        """删除会话元数据文件。"""
        manager._save_session(sample_info)
        session_file = manager._get_session_file("test_sess")
        assert os.path.isfile(session_file)
        manager._delete_session("test_sess")
        assert not os.path.isfile(session_file)

    def test_delete_nonexistent_no_error(self, manager):
        """删除不存在的会话不报错。"""
        manager._delete_session("nonexistent")  # 不应抛异常

    def test_delete_invalid_name_no_error(self, manager):
        """删除无效会话名不报错。"""
        manager._delete_session("../escape")  # 不应抛异常

    def test_save_overwrites_existing(self, manager, sample_info):
        """保存同名会话覆盖旧文件。"""
        manager._save_session(sample_info)
        updated = SessionInfo(
            name="test_sess",
            pid=99999,
            port=9875,
            mode="headless",
            started_at=time.time(),
            project_path="/new/path",
            freecad_path="/new/fc",
        )
        manager._save_session(updated)
        loaded = manager._load_session("test_sess")
        assert loaded is not None
        assert loaded.pid == 99999
        assert loaded.mode == "headless"


# ── SessionManager 查询接口 ──


class TestSessionQuery:
    """list 和 status 查询接口。"""

    @pytest.fixture
    def manager(self, tmp_path):
        return SessionManager(project_dir=str(tmp_path))

    def _make_info(self, name: str, pid: int = 1000, port: int = 9875) -> SessionInfo:
        return SessionInfo(
            name=name,
            pid=pid,
            port=port,
            mode="gui",
            started_at=time.time(),
            project_path="/tmp",
            freecad_path="/fc",
        )

    def test_list_empty(self, manager):
        """无会话时返回空列表。"""
        assert manager.list() == []

    def test_list_single(self, manager):
        """单个会话。"""
        manager._save_session(self._make_info("s1"))
        sessions = manager.list()
        assert len(sessions) == 1
        assert sessions[0].name == "s1"

    def test_list_multiple(self, manager):
        """多个会话。"""
        manager._save_session(self._make_info("s1", pid=1001, port=9875))
        manager._save_session(self._make_info("s2", pid=1002, port=9876))
        manager._save_session(self._make_info("s3", pid=1003, port=9877))
        sessions = manager.list()
        assert len(sessions) == 3
        names = {s.name for s in sessions}
        assert names == {"s1", "s2", "s3"}

    def test_list_ignores_non_json_files(self, manager):
        """list 忽略非 .json 文件。"""
        session_dir = manager._get_session_dir()
        os.makedirs(session_dir, exist_ok=True)
        # 写入非 JSON 文件
        with open(os.path.join(session_dir, "readme.txt"), "w") as f:
            f.write("not a session")
        manager._save_session(self._make_info("s1"))
        sessions = manager.list()
        assert len(sessions) == 1
        assert sessions[0].name == "s1"

    def test_list_ignores_corrupted(self, manager):
        """list 忽略损坏的会话文件。"""
        session_dir = manager._get_session_dir()
        os.makedirs(session_dir, exist_ok=True)
        with open(os.path.join(session_dir, "corrupt.json"), "w") as f:
            f.write("{bad")
        manager._save_session(self._make_info("good"))
        sessions = manager.list()
        assert len(sessions) == 1
        assert sessions[0].name == "good"

    def test_status_existing(self, manager):
        """status 返回存在的会话信息。"""
        manager._save_session(self._make_info("s1", pid=1234))
        info = manager.status("s1")
        assert info is not None
        assert info.name == "s1"
        assert info.pid == 1234

    def test_status_nonexistent(self, manager):
        """status 对不存在的会话返回 None。"""
        assert manager.status("nonexistent") is None

    def test_status_invalid_name(self, manager):
        """status 对无效会话名返回 None。"""
        assert manager.status("../escape") is None


# ── 生命周期管理（start/stop/get_backend）──


class TestSessionStart:
    """start() 方法测试。"""

    @pytest.fixture
    def manager(self, tmp_path):
        return SessionManager(project_dir=str(tmp_path))

    def test_start_invalid_name_raises(self, manager):
        """无效会话名抛出 ValueError。"""
        with pytest.raises(ValueError, match="无效的会话名"):
            manager.start("bad name!")

    def test_start_existing_session_raises(self, manager):
        """会话已存在时抛出 ValueError。"""
        # 先保存一个会话
        info = SessionInfo(
            name="existing",
            pid=12345,
            port=9875,
            mode="gui",
            started_at=time.time(),
            project_path="",
            freecad_path="/fc",
        )
        manager._save_session(info)

        with pytest.raises(ValueError, match="会话已存在"):
            manager.start("existing")

    @patch("fc_core.backend.find_freecad")
    @patch("fc_core.scripts.fc_rpc_server.find_free_port")
    @patch("subprocess.Popen")
    @patch.object(SessionManager, "_wait_for_server", return_value=True)
    def test_start_success(
        self,
        mock_wait,
        mock_popen,
        mock_find_port,
        mock_find_freecad,
        manager,
    ):
        """start 成功启动会话。"""
        mock_find_freecad.return_value = "/fake/freecad"
        mock_find_port.return_value = 9876
        mock_proc = MagicMock()
        mock_proc.pid = 54321
        mock_popen.return_value = mock_proc

        info = manager.start("test_session", mode="gui", project="/tmp/proj")

        assert info.name == "test_session"
        assert info.pid == 54321
        assert info.port == 9876
        assert info.mode == "gui"
        assert info.project_path == "/tmp/proj"
        assert info.freecad_path == "/fake/freecad"
        # 验证会话已保存
        loaded = manager._load_session("test_session")
        assert loaded is not None
        assert loaded.pid == 54321

    @patch("fc_core.backend.find_freecad")
    @patch("fc_core.scripts.fc_rpc_server.find_free_port")
    @patch("subprocess.Popen")
    @patch.object(SessionManager, "_wait_for_server", return_value=False)
    def test_start_timeout_raises(
        self,
        mock_wait,
        mock_popen,
        mock_find_port,
        mock_find_freecad,
        manager,
    ):
        """RPC 服务器未就绪时抛出 TimeoutError 并清理子进程。"""
        mock_find_freecad.return_value = "/fake/freecad"
        mock_find_port.return_value = 9876
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        with pytest.raises(TimeoutError, match="RPC 服务器"):
            manager.start("timeout_session")

        # 验证子进程被清理
        mock_proc.terminate.assert_called_once()
        # 验证会话未保存
        assert manager._load_session("timeout_session") is None

    @patch("fc_core.backend.find_freecad")
    @patch("fc_core.scripts.fc_rpc_server.find_free_port")
    @patch("subprocess.Popen")
    @patch.object(SessionManager, "_wait_for_server", return_value=True)
    def test_start_uses_specified_port(
        self,
        mock_wait,
        mock_popen,
        mock_find_port,
        mock_find_freecad,
        manager,
    ):
        """指定端口时不调用 find_free_port。"""
        mock_find_freecad.return_value = "/fake/freecad"
        mock_proc = MagicMock()
        mock_proc.pid = 11111
        mock_popen.return_value = mock_proc

        info = manager.start("port_test", port=9999)
        assert info.port == 9999
        mock_find_port.assert_not_called()


class TestSessionStop:
    """stop() 方法测试。"""

    @pytest.fixture
    def manager(self, tmp_path):
        return SessionManager(project_dir=str(tmp_path))

    def _make_info(self, name="test", pid=12345, port=9875):
        return SessionInfo(
            name=name,
            pid=pid,
            port=port,
            mode="gui",
            started_at=time.time(),
            project_path="",
            freecad_path="/fc",
        )

    def test_stop_nonexistent_returns_true(self, manager):
        """停止不存在的会话返回 True。"""
        assert manager.stop("nonexistent") is True

    @patch("xmlrpc.client.ServerProxy")
    def test_stop_via_rpc_shutdown(self, mock_proxy_class, manager):
        """通过 RPC shutdown 优雅关闭。"""
        info = self._make_info("stop_rpc")
        manager._save_session(info)

        mock_proxy = MagicMock()
        mock_proxy.ping.return_value = True
        mock_proxy.shutdown.return_value = True
        mock_proxy_class.return_value = mock_proxy

        result = manager.stop("stop_rpc")

        assert result is True
        mock_proxy.shutdown.assert_called_once()
        # 会话文件已删除
        assert manager._load_session("stop_rpc") is None

    @patch.object(SessionManager, "_terminate_process")
    @patch("xmlrpc.client.ServerProxy", side_effect=Exception("RPC failed"))
    def test_stop_force_terminate_on_rpc_failure(
        self,
        mock_proxy_class,
        mock_terminate,
        manager,
    ):
        """RPC 失败时强制终止进程。"""
        info = self._make_info("stop_force", pid=99999)
        manager._save_session(info)

        result = manager.stop("stop_force")

        assert result is True
        mock_terminate.assert_called_once_with(99999)
        assert manager._load_session("stop_force") is None


class TestSessionGetBackend:
    """get_backend() 方法测试。"""

    @pytest.fixture
    def manager(self, tmp_path):
        return SessionManager(project_dir=str(tmp_path))

    def test_get_backend_nonexistent_raises(self, manager):
        """会话不存在时抛出 ValueError。"""
        with pytest.raises(ValueError, match="会话不存在"):
            manager.get_backend("nonexistent")

    @patch("fc_core.backend.RPCBackend")
    def test_get_backend_returns_rpcbackend(self, mock_rpc_class, manager):
        """get_backend 返回连接到会话端口的 RPCBackend。"""
        info = SessionInfo(
            name="backend_test",
            pid=12345,
            port=9877,
            mode="gui",
            started_at=time.time(),
            project_path="",
            freecad_path="/fc",
        )
        manager._save_session(info)

        mock_backend = MagicMock()
        mock_rpc_class.return_value = mock_backend

        backend = manager.get_backend("backend_test")

        assert backend is mock_backend
        mock_rpc_class.assert_called_once_with(host="localhost", port=9877)


class TestWaitForServer:
    """_wait_for_server 方法测试。"""

    @pytest.fixture
    def manager(self, tmp_path):
        return SessionManager(project_dir=str(tmp_path))

    @patch("xmlrpc.client.ServerProxy")
    def test_wait_success(self, mock_proxy_class, manager):
        """服务器就绪时返回 True。"""
        mock_proxy = MagicMock()
        mock_proxy.ping.return_value = True
        mock_proxy_class.return_value = mock_proxy

        result = manager._wait_for_server("localhost", 9876, timeout=1.0)
        assert result is True

    @patch("xmlrpc.client.ServerProxy", side_effect=ConnectionError("refused"))
    def test_wait_timeout(self, mock_proxy_class, manager):
        """服务器未就绪时超时返回 False。"""
        result = manager._wait_for_server("localhost", 9876, timeout=0.6)
        assert result is False

    @patch("xmlrpc.client.ServerProxy")
    def test_wait_retries_until_ready(self, mock_proxy_class, manager):
        """前几次失败，后续成功。"""
        mock_proxy = MagicMock()
        mock_proxy.ping.side_effect = [
            ConnectionError("not ready"),
            ConnectionError("not ready"),
            True,
        ]
        mock_proxy_class.return_value = mock_proxy

        result = manager._wait_for_server("localhost", 9876, timeout=5.0)
        assert result is True
        assert mock_proxy.ping.call_count == 3


class TestTerminateProcess:
    """_terminate_process 方法测试。"""

    @pytest.fixture
    def manager(self, tmp_path):
        return SessionManager(project_dir=str(tmp_path))

    @patch("platform.system", return_value="Windows")
    @patch("subprocess.run")
    def test_terminate_windows(self, mock_run, mock_system, manager):
        """Windows 上使用 taskkill。"""
        manager._terminate_process(12345)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "taskkill" in args
        assert "12345" in args

    @patch("platform.system", return_value="Linux")
    @patch("os.kill")
    def test_terminate_linux(self, mock_kill, mock_system, manager):
        """Linux 上使用 SIGTERM。"""
        import signal

        manager._terminate_process(12345)
        mock_kill.assert_called_once_with(12345, signal.SIGTERM)

    @patch("subprocess.run", side_effect=Exception("taskkill failed"))
    @patch("platform.system", return_value="Windows")
    def test_terminate_failure_no_raise(self, mock_system, mock_run, manager):
        """终止失败不抛异常。"""
        # 不应抛异常
        manager._terminate_process(12345)
