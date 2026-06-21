"""FCRPCServer 单元测试。

覆盖：
- find_free_port 端口查找
- FCRPCServer 方法注册
- RPC 方法逻辑（mock FreeCAD 模块）
- start/stop 生命周期
"""

from __future__ import annotations

import socket
import threading
from unittest.mock import MagicMock, patch

import pytest

from fc_core.scripts.fc_rpc_server import FCRPCServer, find_free_port


# ── find_free_port ──


class TestFindFreePort:
    """端口查找函数测试。"""

    def test_finds_free_port(self):
        """能找到可用端口。"""
        port = find_free_port("localhost", start=20000, max_tries=10)
        assert 20000 <= port < 20010

    def test_returns_usable_port(self):
        """返回的端口确实可用。"""
        port = find_free_port("localhost", start=20100, max_tries=10)
        # 验证端口可绑定
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", port))

    def test_skips_occupied_ports(self):
        """跳过已占用的端口。"""
        # 占用一个端口
        occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        occupied.bind(("localhost", 20200))
        occupied.listen(1)
        try:
            port = find_free_port("localhost", start=20200, max_tries=10)
            assert port != 20200
            assert 20201 <= port < 20210
        finally:
            occupied.close()

    def test_raises_when_no_free_port(self):
        """无可用端口时抛出 OSError。"""
        # 占用所有端口
        sockets = []
        try:
            for p in range(20300, 20305):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(("localhost", p))
                s.listen(1)
                sockets.append(s)
            with pytest.raises(OSError, match="无可用端口"):
                find_free_port("localhost", start=20300, max_tries=5)
        finally:
            for s in sockets:
                s.close()


# ── FCRPCServer 方法注册 ──


class TestMethodRegistration:
    """RPC 方法注册测试。"""

    def test_register_all_methods(self):
        """start() 后所有方法已注册。"""
        server = FCRPCServer(port=0)  # 端口 0 让系统分配
        # Mock SimpleXMLRPCServer 避免真实绑定
        with patch(
            "xmlrpc.server.SimpleXMLRPCServer"
        ) as mock_server_class:
            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            server.start()

            # 验证所有方法已注册
            registered_names = {
                call.args[1] for call in mock_server.register_function.call_args_list
            }
            expected_methods = {
                "ping", "get_version", "execute_code",
                "create_document", "open_document", "save_document",
                "inject_gui_data",
                "get_objects", "get_object", "create_object",
                "edit_object", "delete_object", "import_file",
                "shutdown",
            }
            assert registered_names == expected_methods
            server.stop()

    def test_start_creates_daemon_thread(self):
        """start() 创建 daemon 线程。"""
        server = FCRPCServer(port=0)
        with patch("xmlrpc.server.SimpleXMLRPCServer"):
            server.start()
            assert server._thread is not None
            assert server._thread.daemon is True
            server.stop()

    def test_stop_cleans_up(self):
        """stop() 清理服务器和线程。"""
        server = FCRPCServer(port=0)
        with patch("xmlrpc.server.SimpleXMLRPCServer"):
            server.start()
            server.stop()
            assert server._server is None
            assert server._thread is None


# ── RPC 方法逻辑（mock FreeCAD）──


class TestRPCMethods:
    """RPC 方法逻辑测试。"""

    @pytest.fixture
    def server(self):
        return FCRPCServer(port=0)

    @pytest.fixture
    def mock_freecad(self):
        """Mock FreeCAD 模块。"""
        mock_fc = MagicMock()
        with patch(
            "fc_core.scripts.fc_rpc_server._get_freecad", return_value=mock_fc
        ):
            yield mock_fc

    def test_ping(self, server):
        """ping 始终返回 True。"""
        assert server.ping() is True

    def test_get_version_success(self, server, mock_freecad):
        """get_version 成功。"""
        mock_freecad.Version.return_value = ["1", "1", "0"]
        result = server.get_version()
        assert result["success"] is True
        assert result["version"] == ["1", "1", "0"]

    def test_get_version_failure(self, server):
        """get_version 失败时返回错误。"""
        with patch(
            "fc_core.scripts.fc_rpc_server._get_freecad",
            side_effect=ImportError("No FreeCAD"),
        ):
            result = server.get_version()
            assert result["success"] is False
            assert "No FreeCAD" in result["error"]

    def test_execute_code_success(self, server):
        """execute_code 成功执行并返回 _fc_result。"""
        code = "_fc_result = {'status': 'ok', 'data': {'x': 1}}"
        result = server.execute_code(code)
        assert result["success"] is True
        assert result["status"] == "ok"
        assert result["data"]["x"] == 1

    def test_execute_code_no_result_var(self, server):
        """execute_code 无 _fc_result 时返回默认。"""
        code = "x = 1 + 1"
        result = server.execute_code(code)
        assert result["success"] is True
        assert result["status"] == "ok"

    def test_execute_code_error(self, server):
        """execute_code 执行出错时返回错误。"""
        code = "raise ValueError('test error')"
        result = server.execute_code(code)
        assert result["success"] is False
        assert "test error" in result["error"]

    def test_create_document_success(self, server, mock_freecad):
        """create_document 成功。"""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"
        mock_doc.Label = "TestDoc"
        mock_freecad.newDocument.return_value = mock_doc

        result = server.create_document("TestDoc")
        assert result["success"] is True
        assert result["name"] == "TestDoc"
        mock_freecad.newDocument.assert_called_once_with("TestDoc")

    def test_create_document_error(self, server, mock_freecad):
        """create_document 失败。"""
        mock_freecad.newDocument.side_effect = Exception("create failed")
        result = server.create_document("Bad")
        assert result["success"] is False
        assert "create failed" in result["error"]

    def test_save_document_no_active(self, server, mock_freecad):
        """save_document 无活动文档时失败。"""
        mock_freecad.ActiveDocument = None
        result = server.save_document("/tmp/test.FCStd")
        assert result["success"] is False
        assert "无活动文档" in result["error"]

    def test_save_document_success(self, server, mock_freecad):
        """save_document 成功。"""
        mock_doc = MagicMock()
        mock_doc.FileName = "/tmp/test.FCStd"
        mock_freecad.ActiveDocument = mock_doc

        result = server.save_document("/tmp/test.FCStd")
        assert result["success"] is True
        assert result["path"] == "/tmp/test.FCStd"
        mock_doc.saveAs.assert_called_once()

    def test_inject_gui_data_no_active(self, server, mock_freecad):
        """inject_gui_data 无活动文档时失败。"""
        mock_freecad.ActiveDocument = None
        mock_fc_gui = MagicMock()
        with patch.dict(
            "sys.modules",
            {"FreeCADGui": mock_fc_gui, "pivy": MagicMock()},
        ):
            result = server.inject_gui_data("/tmp/test.FCStd")
        assert result["success"] is False
        assert "无活动文档" in result["error"]

    def test_inject_gui_data_no_path(self, server, mock_freecad):
        """inject_gui_data 未指定路径且文档未保存时失败。"""
        mock_doc = MagicMock()
        mock_doc.FileName = ""
        mock_freecad.ActiveDocument = mock_doc
        with patch.dict("sys.modules", {"FreeCADGui": MagicMock(), "pivy": MagicMock()}):
            result = server.inject_gui_data("")
        assert result["success"] is False
        assert "未指定 file_path" in result["error"]

    def test_inject_gui_data_success(self, server, mock_freecad):
        """inject_gui_data 成功注入并保存。"""
        import os
        target_path = os.path.abspath("/tmp/test.FCStd")
        mock_doc = MagicMock()
        mock_doc.FileName = target_path
        mock_freecad.ActiveDocument = mock_doc

        mock_gui_module = MagicMock()
        mock_gui_module.activeDocument.return_value.activeView.return_value.getCameraNode.return_value = None
        with patch.dict(
            "sys.modules",
            {"FreeCADGui": mock_gui_module, "pivy": MagicMock()},
        ):
            result = server.inject_gui_data(target_path, view="isometric", fit_all=True)

        assert result["success"] is True
        assert result["path"] == target_path
        assert result["view"] == "isometric"
        assert result["fit_all"] is True
        mock_doc.saveAs.assert_called_once()
        mock_doc.recompute.assert_called_once()

    def test_get_objects_no_active(self, server, mock_freecad):
        """get_objects 无活动文档时失败。"""
        mock_freecad.ActiveDocument = None
        result = server.get_objects()
        assert result["success"] is False
        assert "无活动文档" in result["error"]

    def test_get_objects_success(self, server, mock_freecad):
        """get_objects 成功返回对象列表。"""
        mock_obj1 = MagicMock()
        mock_obj1.Name = "Box"
        mock_obj1.Label = "Box"
        mock_obj1.TypeId = "Part::Box"
        mock_obj2 = MagicMock()
        mock_obj2.Name = "Cylinder"
        mock_obj2.Label = "Cylinder"
        mock_obj2.TypeId = "Part::Cylinder"

        mock_doc = MagicMock()
        mock_doc.Objects = [mock_obj1, mock_obj2]
        mock_freecad.ActiveDocument = mock_doc

        result = server.get_objects()
        assert result["success"] is True
        assert result["count"] == 2
        assert result["objects"][0]["name"] == "Box"
        assert result["objects"][1]["type"] == "Part::Cylinder"

    def test_get_object_not_found(self, server, mock_freecad):
        """get_object 对象不存在时失败。"""
        mock_doc = MagicMock()
        mock_doc.getObject.return_value = None
        mock_freecad.ActiveDocument = mock_doc

        result = server.get_object("Nonexistent")
        assert result["success"] is False
        assert "对象不存在" in result["error"]

    def test_create_object_success(self, server, mock_freecad):
        """create_object 成功。"""
        mock_obj = MagicMock()
        mock_obj.Name = "Box_1"
        mock_obj.Label = "Box_1"
        mock_doc = MagicMock()
        mock_doc.addObject.return_value = mock_obj
        mock_freecad.ActiveDocument = mock_doc

        result = server.create_object({
            "Name": "Box_1",
            "Type": "Part::Box",
            "Properties": {"Length": 100},
        })
        assert result["success"] is True
        assert result["name"] == "Box_1"
        mock_doc.addObject.assert_called_once_with("Part::Box", "Box_1")

    def test_delete_object_success(self, server, mock_freecad):
        """delete_object 成功。"""
        mock_obj = MagicMock()
        mock_obj.Name = "Box_1"
        mock_doc = MagicMock()
        mock_doc.getObject.return_value = mock_obj
        mock_freecad.ActiveDocument = mock_doc

        result = server.delete_object("Box_1")
        assert result["success"] is True
        mock_doc.removeObject.assert_called_once_with("Box_1")

    def test_shutdown_returns_true(self, server):
        """shutdown 返回 True。"""
        with patch.object(server, "stop") as mock_stop:
            result = server.shutdown()
            assert result is True


# ── 集成测试：真实 RPC 通信 ──


class TestRPCIntegration:
    """真实 XML-RPC 通信测试（不依赖 FreeCAD）。"""

    def test_ping_via_rpc(self):
        """通过真实 XML-RPC 调用 ping。"""
        server = FCRPCServer(port=0)
        server.start()
        try:
            actual_port = server._server.server_address[1]
            import xmlrpc.client

            client = xmlrpc.client.ServerProxy(
                f"http://localhost:{actual_port}",
                allow_none=True,
            )
            assert client.ping() is True
        finally:
            server.stop()

    def test_execute_code_via_rpc(self):
        """通过真实 XML-RPC 调用 execute_code。"""
        server = FCRPCServer(port=0)
        server.start()
        try:
            actual_port = server._server.server_address[1]
            import xmlrpc.client

            client = xmlrpc.client.ServerProxy(
                f"http://localhost:{actual_port}",
                allow_none=True,
            )
            result = client.execute_code("_fc_result = {'status': 'ok', 'data': {'x': 42}}")
            assert result["success"] is True
            assert result["data"]["x"] == 42
        finally:
            server.stop()
