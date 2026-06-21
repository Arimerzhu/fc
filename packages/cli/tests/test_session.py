"""Tests for the ``session`` command group.

Covers all session sub-commands: undo, redo, status, history, snapshot, restore.
Uses MockBackend so no real FreeCAD installation is required.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile

from fc_core.types import ToolResponse
from fc_cli.main import cli

from tests.conftest import MockBackend


# ── helpers ------------------------------------------------------------------


def _json_output(result) -> dict:
    """Parse JSON from Click result output."""
    return json.loads(result.output.strip())


def _patch_session_backend(mock: MockBackend):
    """Patch _get_backend inside fc_cli.commands.session_cmd."""
    from unittest.mock import patch
    return patch("fc_cli.commands.session_cmd._get_backend", return_value=mock)


# ── session undo -------------------------------------------------------------


class TestSessionUndo:
    """Tests for ``fc session undo``."""

    def test_undo_default(self, mock_backend: MockBackend, runner):
        """Undo with default steps."""
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["session", "undo"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_undo_multiple_steps(self, mock_backend: MockBackend, runner):
        """Undo multiple steps."""
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["session", "undo", "--steps", "3"])
        assert result.exit_code == 0

    def test_undo_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for undo."""
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "session", "undo"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"

    def test_undo_disconnect(self, mock_backend: MockBackend, runner):
        """Backend disconnect must be called."""
        with _patch_session_backend(mock_backend):
            runner.invoke(cli, ["session", "undo"])
        assert mock_backend.disconnected is True


# ── session redo -------------------------------------------------------------


class TestSessionRedo:
    """Tests for ``fc session redo``."""

    def test_redo_default(self, mock_backend: MockBackend, runner):
        """Redo with default steps."""
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["session", "redo"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_redo_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for redo."""
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "session", "redo"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["status"] == "ok"


# ── session status -----------------------------------------------------------


class TestSessionStatus:
    """Tests for ``fc session status``."""

    def test_status(self, mock_backend: MockBackend, runner):
        """Show session status."""
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["session", "status"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")

    def test_status_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce a response for status (dict output, not ToolResponse)."""
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "session", "status"])
        assert result.exit_code == 0
        # session status mixes backend data with local flags; output is plain dict
        data = _json_output(result)
        assert "backend" in data


# ── session history ----------------------------------------------------------


class TestSessionHistory:
    """Tests for ``fc session history``."""

    def test_history(self, mock_backend: MockBackend, runner):
        """Show session history."""
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["session", "history"])
        assert result.exit_code == 0

    def test_history_json_output(self, mock_backend: MockBackend, runner):
        """--json should output history entries as dict."""
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "session", "history"])
        assert result.exit_code == 0
        data = _json_output(result)
        # History output is {"entries": [...], "total": N} — no "status" key
        assert "entries" in data
        assert "total" in data


# ── session snapshot ---------------------------------------------------------


class TestSessionSnapshot:
    """Tests for ``fc session snapshot``."""

    def _clean(self, tmp: str) -> None:
        if os.path.exists(tmp):
            os.unlink(tmp)
        hist_dir = os.path.splitext(tmp)[0] + "_history"
        if os.path.isdir(hist_dir):
            shutil.rmtree(hist_dir, ignore_errors=True)

    def test_snapshot(self, mock_backend: MockBackend, runner):
        """Create a snapshot (requires --project)."""
        with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
            tmp = f.name
        try:
            with _patch_session_backend(mock_backend):
                result = runner.invoke(cli, [
                    "--project", tmp, "session", "snapshot", "test_snap",
                ])
            assert result.exit_code == 0
            assert mock_backend.was_called("document_save")
        finally:
            self._clean(tmp)

    def test_snapshot_json_output(self, mock_backend: MockBackend, runner):
        """--json should produce valid JSON for snapshot."""
        with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
            tmp = f.name
        try:
            with _patch_session_backend(mock_backend):
                result = runner.invoke(cli, [
                    "--json", "--project", tmp, "session", "snapshot", "snap2",
                ])
            assert result.exit_code == 0
            data = _json_output(result)
            # Snapshot output is a metadata dict with "name" key
            assert "name" in data
        finally:
            self._clean(tmp)

    def test_snapshot_invalid_name(self, mock_backend: MockBackend, runner):
        """Snapshot with invalid name should fail (error exits with code 1)."""
        with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
            tmp = f.name
        try:
            with _patch_session_backend(mock_backend):
                result = runner.invoke(cli, [
                    "--project", tmp, "session", "snapshot", "invalid name!",
                ])
            # _output.error() calls sys.exit(1) when not in repl_mode
            assert result.exit_code != 0
        finally:
            self._clean(tmp)

    def test_snapshot_missing_name(self, runner):
        """Snapshot without name argument should fail."""
        result = runner.invoke(cli, ["session", "snapshot"])
        assert result.exit_code != 0


# ── session restore ----------------------------------------------------------


class TestSessionRestore:
    """Tests for ``fc session restore``."""

    def _clean(self, tmp: str) -> None:
        if os.path.exists(tmp):
            os.unlink(tmp)
        hist_dir = os.path.splitext(tmp)[0] + "_history"
        if os.path.isdir(hist_dir):
            shutil.rmtree(hist_dir, ignore_errors=True)

    def test_restore_not_found(self, mock_backend: MockBackend, runner):
        """Restore a non-existent snapshot should fail (error exits with code 1)."""
        with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
            tmp = f.name
        try:
            with _patch_session_backend(mock_backend):
                result = runner.invoke(cli, [
                    "--project", tmp, "session", "restore", "nonexistent",
                ])
            # _output.error() calls sys.exit(1) when not in repl_mode
            assert result.exit_code != 0
        finally:
            self._clean(tmp)

    def test_restore_invalid_name(self, mock_backend: MockBackend, runner):
        """Restore with invalid name should fail (error exits with code 1)."""
        with tempfile.NamedTemporaryFile(suffix=".FCStd", delete=False) as f:
            tmp = f.name
        try:
            with _patch_session_backend(mock_backend):
                result = runner.invoke(cli, [
                    "--project", tmp, "session", "restore", "bad name!",
                ])
            assert result.exit_code != 0
        finally:
            self._clean(tmp)

    def test_restore_missing_name(self, runner):
        """Restore without name argument should fail."""
        result = runner.invoke(cli, ["session", "restore"])
        assert result.exit_code != 0


# ── error handling -----------------------------------------------------------


class TestSessionErrors:
    """Tests for error handling in session commands."""

    def test_undo_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on undo, command exits with non-zero code."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "UNDO_FAILED", "Simulated failure"),
        )
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "session", "undo"])
        # The session_undo command checks r.status and calls _output.error()
        # which calls sys.exit(1) when not in repl_mode
        assert result.exit_code != 0

    def test_redo_backend_error(self, mock_backend: MockBackend, runner):
        """When backend returns error on redo, command exits with non-zero code."""
        mock_backend.stage_response(
            "execute_code",
            ToolResponse.error("execute_code", "REDO_FAILED", "Simulated failure"),
        )
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "session", "redo"])
        assert result.exit_code != 0


# ── session start/stop/list（Phase 2 持久化会话）──


def _make_session_info(name="test", pid=12345, port=9875, mode="gui",
                       project_path="", freecad_path="/usr/bin/freecad"):
    """构造 SessionInfo 测试数据。"""
    from fc_core.session import SessionInfo
    return SessionInfo(
        name=name, pid=pid, port=port, mode=mode,
        started_at=1234567890.0, project_path=project_path,
        freecad_path=freecad_path,
    )


class TestSessionStart:
    """Tests for ``fc session start``."""

    def test_start_success(self, runner):
        """成功启动会话。"""
        from unittest.mock import patch
        mock_info = _make_session_info(name="test", port=9875)
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.start.return_value = mock_info
            result = runner.invoke(cli, ["--json", "session", "start", "--name", "test"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["name"] == "test"
        assert data["port"] == 9875
        assert data["mode"] == "gui"

    def test_start_with_options(self, runner):
        """带选项启动会话。"""
        from unittest.mock import patch
        mock_info = _make_session_info(name="mySession", port=9876,
                                       project_path="/path/to/project")
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.start.return_value = mock_info
            result = runner.invoke(cli, [
                "--json", "session", "start",
                "--name", "mySession",
                "--mode", "gui",
                "--port", "9876",
                "--project", "/path/to/project",
            ])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["name"] == "mySession"
        assert data["port"] == 9876
        MockMgr.return_value.start.assert_called_once_with(
            "mySession", mode="gui", port=9876, project="/path/to/project",
        )

    def test_start_invalid_name(self, runner):
        """无效会话名应失败。"""
        from unittest.mock import patch
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.start.side_effect = ValueError("无效的会话名")
            result = runner.invoke(cli, ["--json", "session", "start", "--name", "bad name!"])
        assert result.exit_code != 0

    def test_start_already_exists(self, runner):
        """会话已存在应失败。"""
        from unittest.mock import patch
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.start.side_effect = ValueError("会话已存在")
            result = runner.invoke(cli, ["--json", "session", "start", "--name", "test"])
        assert result.exit_code != 0

    def test_start_timeout(self, runner):
        """RPC 服务器超时应失败。"""
        from unittest.mock import patch
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.start.side_effect = TimeoutError("RPC 服务器超时")
            result = runner.invoke(cli, ["--json", "session", "start", "--name", "test"])
        assert result.exit_code != 0

    def test_start_freecad_not_found(self, runner):
        """FreeCAD 未安装应失败。"""
        from unittest.mock import patch
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.start.side_effect = FileNotFoundError("FreeCAD 未找到")
            result = runner.invoke(cli, ["--json", "session", "start", "--name", "test"])
        assert result.exit_code != 0

    def test_start_missing_name(self, runner):
        """缺少 --name 参数应失败。"""
        result = runner.invoke(cli, ["session", "start"])
        assert result.exit_code != 0


class TestSessionStop:
    """Tests for ``fc session stop``."""

    def test_stop_success(self, runner):
        """成功停止会话。"""
        from unittest.mock import patch
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.stop.return_value = True
            result = runner.invoke(cli, ["--json", "session", "stop", "--name", "test"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["stopped"] is True
        assert data["name"] == "test"

    def test_stop_with_session_option(self, runner):
        """通过 --session 选项停止会话。"""
        from unittest.mock import patch
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.stop.return_value = True
            result = runner.invoke(cli, ["--json", "--session", "mySession", "session", "stop"])
        assert result.exit_code == 0
        MockMgr.return_value.stop.assert_called_once_with("mySession")

    def test_stop_no_name(self, runner):
        """未指定会话名应失败。"""
        import fc_cli.main as main_mod
        old_session = main_mod._session_name
        main_mod._session_name = None
        try:
            result = runner.invoke(cli, ["--json", "session", "stop"])
            assert result.exit_code != 0
        finally:
            main_mod._session_name = old_session

    def test_stop_nonexistent(self, runner):
        """停止不存在的会话（stop 返回 True，视为已停止）。"""
        from unittest.mock import patch
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.stop.return_value = True
            result = runner.invoke(cli, ["--json", "session", "stop", "--name", "nonexistent"])
        assert result.exit_code == 0


class TestSessionList:
    """Tests for ``fc session list``."""

    def test_list_empty(self, runner):
        """空列表。"""
        from unittest.mock import patch
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.list.return_value = []
            result = runner.invoke(cli, ["--json", "session", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["count"] == 0
        assert data["sessions"] == []

    def test_list_with_sessions(self, runner):
        """有会话的列表。"""
        from unittest.mock import patch
        sessions = [
            _make_session_info(name="s1", pid=100, port=9875),
            _make_session_info(name="s2", pid=200, port=9876),
        ]
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.list.return_value = sessions
            result = runner.invoke(cli, ["--json", "session", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert data["count"] == 2
        assert len(data["sessions"]) == 2
        assert data["sessions"][0]["name"] == "s1"
        assert data["sessions"][1]["name"] == "s2"
        assert data["sessions"][1]["port"] == 9876

    def test_list_json_format(self, runner):
        """JSON 输出格式验证。"""
        from unittest.mock import patch
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.list.return_value = []
            result = runner.invoke(cli, ["--json", "session", "list"])
        assert result.exit_code == 0
        data = _json_output(result)
        assert "sessions" in data
        assert "count" in data


class TestSessionRouting:
    """Tests for --session X global option routing."""

    def test_session_routing_calls_get_backend(self, runner):
        """--session X 应通过 SessionManager.get_backend 获取 backend。"""
        from unittest.mock import patch, MagicMock
        mock_backend = MagicMock()
        mock_backend.execute_code.return_value = ToolResponse.ok(
            "execute_code",
            {"name": "TestDoc", "label": "TestDoc", "objects_count": 0,
             "undo_count": 0, "redo_count": 0},
            "",
        )
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.get_backend.return_value = mock_backend
            result = runner.invoke(cli, ["--json", "--session", "test", "session", "status"])
        assert result.exit_code == 0
        MockMgr.return_value.get_backend.assert_called_once_with("test")
        mock_backend.connect.assert_called_once()
        mock_backend.disconnect.assert_called_once()

    def test_session_routing_overrides_backend_type(self, runner):
        """--session X 优先于 --backend rpc。"""
        from unittest.mock import patch, MagicMock
        mock_backend = MagicMock()
        mock_backend.execute_code.return_value = ToolResponse.ok(
            "execute_code", {}, "",
        )
        with patch("fc_core.session.SessionManager") as MockMgr:
            MockMgr.return_value.get_backend.return_value = mock_backend
            result = runner.invoke(cli, [
                "--json", "--backend", "rpc", "--session", "test",
                "session", "status",
            ])
        assert result.exit_code == 0
        # get_backend 被调用，而不是直接创建 RPCBackend
        MockMgr.return_value.get_backend.assert_called_once_with("test")

    def test_no_session_uses_headless(self, runner, mock_backend: MockBackend):
        """不指定 --session 时使用 _get_backend 默认逻辑。"""
        with _patch_session_backend(mock_backend):
            result = runner.invoke(cli, ["--json", "session", "status"])
        assert result.exit_code == 0
        assert mock_backend.was_called("execute_code")
