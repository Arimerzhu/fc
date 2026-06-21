"""FreeCAD RPC 服务器脚本。

由 FreeCAD GUI 启动时加载，在后台线程提供 XML-RPC 接口，
使外部进程（如 fc CLI）可以远程控制 FreeCAD。

用法::

    freecad fc_rpc_server.py --port 9875 --session-name mysession

脚本在 FreeCAD 的 Python 环境中运行，可访问 FreeCAD API。
服务器在 daemon 线程中运行，随 FreeCAD 退出而退出。
"""

from __future__ import annotations

import argparse
import logging
import os
import socket
import threading
from typing import Any

logger = logging.getLogger(__name__)


def _get_freecad():
    """延迟导入 FreeCAD 模块（仅在 FreeCAD 环境中可用）。"""
    import FreeCAD
    return FreeCAD


class FCRPCServer:
    """FreeCAD XML-RPC 服务器。

    在 FreeCAD GUI 内运行，提供远程调用接口。
    所有方法返回 dict，包含 success 字段和结果或错误信息。
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9875,
        session_name: str = "",
    ):
        self._host = host
        self._port = port
        self._session_name = session_name
        self._server = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """启动 RPC 服务器（非阻塞，后台线程运行）。"""
        from xmlrpc.server import SimpleXMLRPCServer

        self._server = SimpleXMLRPCServer(
            (self._host, self._port),
            allow_none=True,
            logRequests=False,
        )
        self._register_methods()
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name=f"fc-rpc-{self._session_name or self._port}",
        )
        self._thread.start()
        logger.info(
            f"RPC 服务器已启动: {self._host}:{self._port} "
            f"(session: {self._session_name or 'unnamed'})"
        )

    def stop(self) -> None:
        """停止 RPC 服务器。"""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            if self._thread.is_alive():
                self._thread.join(timeout=5)
            self._thread = None
        logger.info("RPC 服务器已停止")

    def _register_methods(self) -> None:
        """注册所有 RPC 方法到服务器。"""
        methods = [
            ("ping", self.ping),
            ("get_version", self.get_version),
            ("execute_code", self.execute_code),
            ("create_document", self.create_document),
            ("open_document", self.open_document),
            ("save_document", self.save_document),
            ("inject_gui_data", self.inject_gui_data),
            ("get_objects", self.get_objects),
            ("get_object", self.get_object),
            ("create_object", self.create_object),
            ("edit_object", self.edit_object),
            ("delete_object", self.delete_object),
            ("import_file", self.import_file),
            ("shutdown", self.shutdown),
        ]
        for name, func in methods:
            self._server.register_function(func, name)

    # ── RPC 方法 ──

    def ping(self) -> bool:
        """健康检查。"""
        return True

    def get_version(self) -> dict[str, Any]:
        """获取 FreeCAD 版本。"""
        try:
            FreeCAD = _get_freecad()
            version = FreeCAD.Version()
            return {"success": True, "version": version}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_code(self, code: str) -> dict[str, Any]:
        """执行任意 Python 代码。

        代码中可通过 `_fc_result` 变量返回结构化结果。
        """
        try:
            local_vars: dict[str, Any] = {}
            exec(code, {"__builtins__": __builtins__}, local_vars)
            result = local_vars.get(
                "_fc_result", {"status": "ok", "data": {}, "message": ""}
            )
            if isinstance(result, dict):
                return {"success": True, **result}
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_document(self, name: str = "Untitled") -> dict[str, Any]:
        """创建新文档。"""
        try:
            FreeCAD = _get_freecad()
            doc = FreeCAD.newDocument(name)
            return {
                "success": True,
                "name": doc.Name,
                "label": doc.Label,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_document(self, file_path: str) -> dict[str, Any]:
        """打开已有文档。"""
        try:
            FreeCAD = _get_freecad()
            doc = FreeCAD.open(os.path.abspath(file_path))
            return {
                "success": True,
                "name": doc.Name,
                "label": doc.Label,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_document(self, file_path: str = "") -> dict[str, Any]:
        """保存当前文档。file_path 为空则保存到原路径。"""
        try:
            FreeCAD = _get_freecad()
            doc = FreeCAD.ActiveDocument
            if doc is None:
                return {"success": False, "error": "无活动文档"}
            if file_path:
                doc.saveAs(os.path.abspath(file_path))
            else:
                doc.save()
            return {
                "success": True,
                "path": file_path or doc.FileName,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def inject_gui_data(
        self,
        file_path: str = "",
        view: str = "isometric",
        fit_all: bool = True,
    ) -> dict[str, Any]:
        """注入 GUI 视图数据并重新保存文档。

        解决 FreeCADCmd 模式保存的 FCStd 文件缺少 GuiDocument.xml、
        相机位置、ViewProvider 设置的问题。流程:
          1. 调用 Gui.SendMsgToActiveView("ViewFit") 适配视图
          2. 设置视图方向 (isometric/front/top/side)
          3. 通过 doc.saveAs() 重新保存，触发 GuiDocument.xml 写入

        Args:
            file_path: FCStd 文件路径；为空则使用活动文档当前路径
            view: 视图方向 — isometric | front | top | side | back | left | right
            fit_all: 是否调用 ViewFit 自动适配
        """
        try:
            FreeCAD = _get_freecad()
            import FreeCADGui as _Gui

            doc = FreeCAD.ActiveDocument
            if doc is None:
                return {"success": False, "error": "无活动文档"}

            view_directions = {
                "isometric": (1, 1, 1),
                "front": (0, 0, 1),
                "top": (0, 1, 0),
                "side": (1, 0, 0),
                "back": (0, 0, -1),
                "left": (-1, 0, 0),
                "right": (1, 0, 0),
            }
            direction = view_directions.get(view, (1, 1, 1))

            try:
                _Gui.activeDocument().activeView().viewIsometric()
            except Exception:
                pass

            try:
                cam = _Gui.activeDocument().activeView().getCameraNode()
                if cam is not None:
                    from pivy import coin
                    cam.position = coin.SbVec3f(*[d * 1000 for d in direction])
                    cam.pointAt(coin.SbVec3f(0, 0, 0), coin.SbVec3f(0, 0, 1))
            except Exception as e:
                logger.warning(f"设置相机位置失败: {e}")

            if fit_all:
                try:
                    _Gui.SendMsgToActiveView("ViewFit")
                except Exception as e:
                    logger.warning(f"ViewFit 失败: {e}")

            doc.recompute()
            _Gui.updateGui()

            target_path = file_path or doc.FileName
            if not target_path:
                return {
                    "success": False,
                    "error": "未指定 file_path 且文档未保存过",
                }
            doc.saveAs(os.path.abspath(target_path))

            gui_doc_path = os.path.abspath(target_path)
            return {
                "success": True,
                "path": gui_doc_path,
                "view": view,
                "fit_all": fit_all,
                "message": f"GUI 视图数据已注入并重新保存: {gui_doc_path}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_objects(self) -> dict[str, Any]:
        """获取当前文档中所有对象。"""
        try:
            FreeCAD = _get_freecad()
            doc = FreeCAD.ActiveDocument
            if doc is None:
                return {"success": False, "error": "无活动文档"}
            objs = [
                {
                    "name": obj.Name,
                    "label": obj.Label,
                    "type": obj.TypeId,
                }
                for obj in doc.Objects
            ]
            return {"success": True, "objects": objs, "count": len(objs)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_object(self, name: str) -> dict[str, Any]:
        """获取单个对象的详细信息。"""
        try:
            FreeCAD = _get_freecad()
            doc = FreeCAD.ActiveDocument
            if doc is None:
                return {"success": False, "error": "无活动文档"}
            obj = doc.getObject(name)
            if obj is None:
                return {"success": False, "error": f"对象不存在: {name}"}
            props = {}
            for prop_name in obj.PropertiesList:
                try:
                    props[prop_name] = str(obj.getPropertyByName(prop_name))
                except Exception:
                    pass
            return {
                "success": True,
                "name": obj.Name,
                "label": obj.Label,
                "type": obj.TypeId,
                "properties": props,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_object(self, obj_data: dict[str, Any]) -> dict[str, Any]:
        """创建新对象。

        Args:
            obj_data: {"Name": "...", "Type": "Part::Box", "Properties": {...}}
        """
        try:
            FreeCAD = _get_freecad()
            doc = FreeCAD.ActiveDocument
            if doc is None:
                return {"success": False, "error": "无活动文档"}
            obj_type = obj_data.get("Type", "Part::Box")
            obj_name = obj_data.get("Name", "")
            properties = obj_data.get("Properties", {})

            obj = doc.addObject(obj_type, obj_name)
            for prop_name, prop_value in properties.items():
                if hasattr(obj, prop_name):
                    setattr(obj, prop_name, prop_value)
            doc.recompute()
            return {"success": True, "name": obj.Name, "label": obj.Label}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def edit_object(self, name: str, data: dict[str, Any]) -> dict[str, Any]:
        """编辑对象属性。

        Args:
            name: 对象名
            data: {"Properties": {...}}
        """
        try:
            FreeCAD = _get_freecad()
            doc = FreeCAD.ActiveDocument
            if doc is None:
                return {"success": False, "error": "无活动文档"}
            obj = doc.getObject(name)
            if obj is None:
                return {"success": False, "error": f"对象不存在: {name}"}
            properties = data.get("Properties", {})
            for prop_name, prop_value in properties.items():
                if hasattr(obj, prop_name):
                    setattr(obj, prop_name, prop_value)
            doc.recompute()
            return {"success": True, "name": obj.Name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_object(self, name: str) -> dict[str, Any]:
        """删除对象。"""
        try:
            FreeCAD = _get_freecad()
            doc = FreeCAD.ActiveDocument
            if doc is None:
                return {"success": False, "error": "无活动文档"}
            obj = doc.getObject(name)
            if obj is None:
                return {"success": False, "error": f"对象不存在: {name}"}
            doc.removeObject(obj.Name)
            return {"success": True, "name": name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def import_file(self, file_path: str, fmt: str = "") -> dict[str, Any]:
        """导入文件到当前文档。

        Args:
            file_path: 文件路径
            fmt: 格式（step/stl/iges/brep），为空则根据扩展名判断
        """
        try:
            FreeCAD = _get_freecad()
            if not fmt:
                fmt = os.path.splitext(file_path)[1].lstrip(".").lower()

            doc = FreeCAD.ActiveDocument
            if doc is None:
                doc = FreeCAD.newDocument("Imported")

            abs_path = os.path.abspath(file_path)

            if fmt in ("step", "stp"):
                import Part

                shape = Part.Shape()
                shape.read(abs_path)
                obj = doc.addObject("Part::Feature", "ImportedPart")
                obj.Shape = shape
                doc.recompute()
                return {"success": True, "name": obj.Name}
            elif fmt == "stl":
                import Mesh

                Mesh.insert(abs_path, doc.Name)
                doc.recompute()
                return {"success": True}
            elif fmt in ("iges", "igs"):
                import Part

                shape = Part.Shape()
                shape.read(abs_path)
                obj = doc.addObject("Part::Feature", "ImportedPart")
                obj.Shape = shape
                doc.recompute()
                return {"success": True, "name": obj.Name}
            elif fmt == "brep":
                import Part

                shape = Part.Shape()
                shape.read(abs_path)
                obj = doc.addObject("Part::Feature", "ImportedPart")
                obj.Shape = shape
                doc.recompute()
                return {"success": True, "name": obj.Name}
            else:
                return {"success": False, "error": f"不支持的格式: {fmt}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def shutdown(self) -> bool:
        """关闭 RPC 服务器（通过 RPC 调用）。

        在新线程中执行 stop()，避免阻塞当前 RPC 响应。
        """
        threading.Thread(target=self.stop, daemon=True).start()
        return True


def find_free_port(host: str = "localhost", start: int = 9875, max_tries: int = 100) -> int:
    """查找可用端口。

    Args:
        host: 监听地址
        start: 起始端口
        max_tries: 最大尝试次数

    Returns:
        可用端口号

    Raises:
        OSError: 无可用端口
    """
    for port in range(start, start + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                return port
        except OSError:
            continue
    raise OSError(
        f"在 {start}-{start + max_tries - 1} 范围内无可用端口"
    )


def main() -> None:
    """命令行入口。由 FreeCAD GUI 启动时调用。

    参数通过环境变量传递（因为 FreeCAD 的 --pass 只接受一个参数）：
    - FC_RPC_PORT: RPC 端口
    - FC_RPC_HOST: 监听地址（默认 localhost）
    - FC_RPC_SESSION: 会话名
    """
    import os as _os

    # 从环境变量读取配置
    parser = argparse.ArgumentParser(description="FreeCAD RPC Server")
    parser.add_argument("--host", default=None, help="监听地址")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="监听端口（默认自动分配）",
    )
    parser.add_argument("--session-name", default=None, help="会话名")
    args, _ = parser.parse_known_args()

    # 环境变量优先级高于命令行参数
    host = args.host or _os.environ.get("FC_RPC_HOST", "localhost")
    port_str = _os.environ.get("FC_RPC_PORT")
    port = int(port_str) if port_str else args.port
    session_name = args.session_name or _os.environ.get("FC_RPC_SESSION", "")

    port = port if port is not None else find_free_port(host)
    session_name = session_name or ""

    server = FCRPCServer(host=host, port=port, session_name=session_name)
    server.start()

    # 输出就绪标记，供 SessionManager 检测启动完成
    print(f"[FCRPC_READY] {host}:{port} session={session_name}")

    try:
        FreeCAD = _get_freecad()
        print(f"[FCRPC] FreeCAD version: {FreeCAD.Version()}")
    except Exception:
        pass

    # 脚本退出后：
    # - FreeCAD GUI：主窗口保持打开，daemon 线程继续运行
    # - FreeCADCmd：需要阻止主线程退出，否则 daemon 线程也会被终止
    import threading

    # 用于优雅关闭的全局事件
    _shutdown_event = threading.Event()

    # 如果需要阻止 FreeCADCmd 退出，设置一个信号处理
    import signal

    def _signal_handler(signum, frame):
        print("[FCRPC] Received shutdown signal")
        _shutdown_event.set()
        server.stop()

    try:
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)
    except (AttributeError, ValueError):
        # Windows 不支持某些信号
        pass

    # 如果是在 FreeCADCmd 中（没有 GUI），阻止主线程退出
    try:
        import FreeCADGui
        _has_gui = hasattr(FreeCADGui, "getMainWindow") and FreeCADGui.getMainWindow() is not None
    except Exception:
        _has_gui = False

    if not _has_gui:
        # FreeCADCmd 环境：daemon 线程会阻止进程退出
        # 但我们需要显式等待 shutdown 信号
        print(f"[FCRPC] Server running on {host}:{port}, waiting for shutdown...")
        try:
            _shutdown_event.wait()
        except KeyboardInterrupt:
            pass
        print("[FCRPC] Shutting down...")
        server.stop()
        print("[FCRPC] Done")
    else:
        # FreeCAD GUI 环境：主窗口保持打开，线程自动运行
        print(f"[FCRPC] Server running on {host}:{port}")



if __name__ == "__main__":
    main()
