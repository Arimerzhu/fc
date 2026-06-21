"""Session management commands.

Commands for undo/redo and session state:
  session undo    — Undo last operation
  session redo    — Redo last undone operation
  session status  — Show session status
  session history — Show operation history
  session snapshot — Create a named snapshot
  session restore  — Restore a named snapshot
  session start   — 启动 FreeCAD 持久化会话（GUI 子进程 + RPC 服务器）
  session stop    — 停止持久化会话
  session list    — 列出所有活动会话
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time

import click


def _handle_error(f):
    from fc_cli.main import handle_error
    return handle_error(f)


def _get_backend():
    """获取 backend 实例（委托给 main.get_backend 统一管理）。"""
    from fc_cli.main import get_backend
    return get_backend()


def _get_history_dir() -> str | None:
    """Get the session history directory based on project path."""
    from fc_cli.main import _project_path
    if _project_path:
        base = os.path.splitext(_project_path)[0]
        return base + "_history"
    return None


def _load_history() -> list[dict]:
    """Load operation history from disk."""
    hist_dir = _get_history_dir()
    if not hist_dir:
        return []
    hist_file = os.path.join(hist_dir, "history.json")
    if os.path.isfile(hist_file):
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_history(history: list[dict]) -> None:
    """Save operation history to disk."""
    hist_dir = _get_history_dir()
    if not hist_dir:
        return
    os.makedirs(hist_dir, exist_ok=True)
    hist_file = os.path.join(hist_dir, "history.json")
    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False, default=str)


def _append_history(operation: str, details: str = "") -> None:
    """Append an operation to the history."""
    from fc_cli.main import _project_path
    history = _load_history()
    history.append({
        "timestamp": time.time(),
        "operation": operation,
        "details": details,
        "project": _project_path,
    })
    _save_history(history)


@click.group("session")
def session_group():
    """Session management commands (undo/redo/status)."""
    pass


@session_group.command("undo")
@click.option("--steps", default=1, type=int, help="Number of operations to undo.")
@_handle_error
def session_undo(steps: int) -> None:
    """Undo the last operation(s)."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code_lines = ["import FreeCAD", "doc = FreeCAD.ActiveDocument"]
        for _ in range(steps):
            code_lines.append("doc.undo()")
        code_lines.append("doc.recompute()")
        code_lines.append(
            '_fc_result = {"status": "ok", "data": {"steps": ' + str(steps) + '}, "message": ""}'
        )
        r = backend.execute_code("\n".join(code_lines))
        if r.status == "ok":
            _append_history("undo", f"steps={steps}")
            _output.output(r.to_dict(), f"Undone {steps} operation(s)")
        else:
            _output.error(f"Undo failed: {r.message}", code="UNDO_FAILED")
    finally:
        backend.disconnect()


@session_group.command("redo")
@click.option("--steps", default=1, type=int, help="Number of operations to redo.")
@_handle_error
def session_redo(steps: int) -> None:
    """Redo the last undone operation(s)."""
    from fc_cli.main import _output
    backend = _get_backend()
    try:
        backend.connect()
        code_lines = ["import FreeCAD", "doc = FreeCAD.ActiveDocument"]
        for _ in range(steps):
            code_lines.append("doc.redo()")
        code_lines.append("doc.recompute()")
        code_lines.append(
            '_fc_result = {"status": "ok", "data": {"steps": ' + str(steps) + '}, "message": ""}'
        )
        r = backend.execute_code("\n".join(code_lines))
        if r.status == "ok":
            _append_history("redo", f"steps={steps}")
            _output.output(r.to_dict(), f"Redone {steps} operation(s)")
        else:
            _output.error(f"Redo failed: {r.message}", code="REDO_FAILED")
    finally:
        backend.disconnect()


@session_group.command("status")
@_handle_error
def session_status() -> None:
    """Show current session status."""
    from fc_cli.main import _output, _backend_type, _project_path
    backend = _get_backend()
    try:
        backend.connect()
        code = """\
import FreeCAD
doc = FreeCAD.ActiveDocument
undo_count = doc.UndoCount if hasattr(doc, 'UndoCount') else 0
redo_count = doc.RedoCount if hasattr(doc, 'RedoCount') else 0
_fc_result = {
    "status": "ok",
    "data": {
        "name": doc.Name,
        "label": doc.Label,
        "objects_count": len(doc.Objects),
        "undo_count": undo_count,
        "redo_count": redo_count,
    },
    "message": ""
}
"""
        r = backend.execute_code(code)
        status = {
            "backend": _backend_type,
            "project": _project_path or "none",
            "connected": True,
        }
        if r.status == "ok":
            status.update(r.data)
        _output.output(status, "Session status:")
    finally:
        backend.disconnect()


@session_group.command("history")
@click.option("--limit", default=20, type=int, help="Max entries to show.")
@_handle_error
def session_history(limit: int) -> None:
    """Show operation history."""
    from fc_cli.main import _output
    history = _load_history()
    if history:
        # Show most recent first
        entries = list(reversed(history[-limit:]))
        _output.output(
            {"entries": entries, "total": len(history)},
            f"Last {len(entries)} operation(s):",
        )
    else:
        _output.output({"entries": [], "total": 0}, "No history (use --project for session persistence)")


@session_group.command("snapshot")
@click.argument("name")
@click.option("--description", "-d", default="", help="Snapshot description.")
@_handle_error
def session_snapshot(name: str, description: str) -> None:
    """Create a named snapshot (saves current state to history)."""
    from fc_cli.main import _output
    # Prevent path traversal: only allow safe names
    if not re.match(r'^[A-Za-z0-9_\-]+$', name):
        _output.error(
            f"Invalid snapshot name: {name}",
            code="INVALID_NAME",
            suggestion="Use only alphanumeric characters, hyphens, and underscores",
        )
        return
    hist_dir = _get_history_dir()
    if not hist_dir:
        _output.error("Snapshots require a project file",
                      code="NO_PROJECT",
                      suggestion="Use --project flag to enable session persistence")
        return

    backend = _get_backend()
    try:
        backend.connect()
        # Save current document state
        snapshot_dir = os.path.join(hist_dir, "snapshots", name)
        os.makedirs(snapshot_dir, exist_ok=True)

        # Save the document
        doc_path = os.path.join(snapshot_dir, f"{name}.FCStd")
        r = backend.document_save(doc_path)
        if r.status != "ok":
            _output.error(f"Snapshot failed: {r.message}", code="SNAPSHOT_FAILED")
            return

        # Save metadata
        meta = {
            "name": name,
            "description": description,
            "timestamp": time.time(),
            "document": doc_path,
        }
        with open(os.path.join(snapshot_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

        _append_history("snapshot", f"name={name}")
        _output.output(meta, f"Snapshot '{name}' created")
    finally:
        backend.disconnect()


@session_group.command("restore")
@click.argument("name")
@_handle_error
def session_restore(name: str) -> None:
    """Restore a named snapshot."""
    from fc_cli.main import _output

    # Prevent path traversal: only allow safe names
    if not re.match(r'^[A-Za-z0-9_\-]+$', name):
        _output.error(
            f"Invalid snapshot name: {name}",
            code="INVALID_NAME",
            suggestion="Use only alphanumeric characters, hyphens, and underscores",
        )
        return

    hist_dir = _get_history_dir()
    if not hist_dir:
        _output.error("Snapshots require a project file",
                      code="NO_PROJECT",
                      suggestion="Use --project flag to enable session persistence")
        return

    snapshot_dir = os.path.join(hist_dir, "snapshots", name)
    meta_file = os.path.join(snapshot_dir, "meta.json")

    if not os.path.isfile(meta_file):
        _output.error(f"Snapshot not found: {name}", code="NOT_FOUND",
                      suggestion=f"Available: {', '.join(_list_snapshots(hist_dir))}")
        return

    with open(meta_file, "r") as f:
        meta = json.load(f)

    doc_path = meta.get("document", "")
    if not os.path.isfile(doc_path):
        _output.error(f"Snapshot document missing: {doc_path}", code="FILE_MISSING")
        return

    backend = _get_backend()
    try:
        backend.connect()
        r = backend.document_open(doc_path)
        if r.status == "ok":
            _append_history("restore", f"name={name}")
            _output.output(meta, f"Restored snapshot '{name}'")
        else:
            _output.error(f"Restore failed: {r.message}", code="RESTORE_FAILED")
    finally:
        backend.disconnect()


def _list_snapshots(hist_dir: str) -> list[str]:
    """List available snapshot names."""
    snap_dir = os.path.join(hist_dir, "snapshots")
    if not os.path.isdir(snap_dir):
        return []
    return [d for d in os.listdir(snap_dir) if os.path.isdir(os.path.join(snap_dir, d))]


# ── 持久化会话管理（Phase 2）──


@session_group.command("start")
@click.option("--name", required=True, help="会话名（唯一标识，只允许字母/数字/下划线/连字符）")
@click.option("--mode", type=click.Choice(["gui", "headless"]), default="gui",
              help="FreeCAD 模式（当前只支持 gui）")
@click.option("--port", type=int, default=None, help="RPC 端口（默认从 9875 自动分配）")
@click.option("--project", type=click.Path(), default=None, help="项目文件路径（可选）")
@_handle_error
def session_start(name: str, mode: str, port: int | None, project: str | None) -> None:
    """启动 FreeCAD 持久化会话（GUI 子进程 + RPC 服务器）。

    启动后可用 --session X 选项让其他命令复用此会话的 RPCBackend。
    """
    from fc_cli.main import _output
    from fc_core.session import SessionManager

    mgr = SessionManager()
    try:
        info = mgr.start(name, mode=mode, port=port, project=project)
        _output.output(
            info.to_dict(),
            f"会话 '{name}' 已启动 (pid={info.pid}, port={info.port}, mode={info.mode})",
        )
    except (ValueError, FileNotFoundError, TimeoutError) as e:
        _output.error(str(e), code="SESSION_START_FAILED")


@session_group.command("stop")
@click.option("--name", default=None, help="会话名（默认停止 --session 指定的会话）")
@_handle_error
def session_stop(name: str | None) -> None:
    """停止 FreeCAD 持久化会话。

    优先通过 RPC shutdown 优雅关闭，失败则强制终止进程。
    """
    from fc_cli.main import _output, _session_name
    from fc_core.session import SessionManager

    session_name = name or _session_name
    if not session_name:
        _output.error(
            "未指定会话名（用 --name 或全局 --session）",
            code="NO_SESSION",
        )
        return

    mgr = SessionManager()
    if mgr.stop(session_name):
        _output.output(
            {"name": session_name, "stopped": True},
            f"会话 '{session_name}' 已停止",
        )
    else:
        _output.error(f"停止会话失败: {session_name}", code="SESSION_STOP_FAILED")


@session_group.command("list")
@_handle_error
def session_list() -> None:
    """列出所有活动会话。"""
    from fc_cli.main import _output
    from fc_core.session import SessionManager

    mgr = SessionManager()
    sessions = mgr.list()
    _output.output(
        {
            "sessions": [s.to_dict() for s in sessions],
            "count": len(sessions),
        },
        f"活动会话: {len(sessions)} 个",
    )
