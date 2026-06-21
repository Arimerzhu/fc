"""Agent 统一结构化日志 — P2.1

提供结构化 stage 转换事件、任务事件、错误事件。
遵循 Karpathy 规范：单一职责，可读 > 可写，避免隐藏状态。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable


# ── 日志级别 ──────────────────────────────────────────

LEVEL_STAGE = logging.INFO + 1
LEVEL_IO = logging.INFO + 2
LEVEL_DEBUG = logging.DEBUG
logging.addLevelName(LEVEL_STAGE, "STAGE")
logging.addLevelName(LEVEL_IO, "IO")


# ── 结构化事件数据类 ─────────────────────────────

@dataclass
class StageEvent:
    """Pipeline stage 转换事件。"""
    from_stage: str
    to_stage: str
    elapsed_ms: float = 0.0
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskEvent:
    """单个任务执行事件。"""
    task_id: str
    status: str  # "start" | "success" | "fail" | "retry"
    duration_ms: float = 0.0
    detail: str = ""


@dataclass
class ErrorEvent:
    """错误分类事件。"""
    error_level: str  # DESIGN | CODE | DRAWING
    message: str
    retry_attempt: int = 0


# ── AgentLogger ─────────────────────────────────

class AgentLogger:
    """统一的 Agent 日志门面。

    同时输出到 Python logging + 内部事件列表（便于测试/诊断）。
    """

    def __init__(self, name: str, verbose: bool = False) -> None:
        self.name = name
        self.verbose = verbose
        self._logger = logging.getLogger(f"fc.agent.{name}")
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            handler.setFormatter(logging.Formatter(fmt))
            self._logger.addHandler(handler)
        self._logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        self.events: list[dict[str, Any]] = []
        self._stage_timers: dict[str, float] = {}

    # ── stage 事件 ─────────────────────────────────

    def stage_enter(self, stage: str, **context: Any) -> None:
        self._stage_timers[stage] = time.perf_counter()
        event = {"type": "stage_enter", "stage": stage, "context": dict(context)}
        self._logger.log(LEVEL_STAGE, self._format(event))
        self.events.append(event)

    def stage_exit(self, stage: str, success: bool = True,
                   **context: Any) -> None:
        start = self._stage_timers.pop(stage, time.perf_counter())
        duration_ms = (time.perf_counter() - start) * 1000
        event = {
            "type": "stage_exit",
            "stage": stage,
            "success": success,
            "duration_ms": round(duration_ms, 2),
            "context": dict(context),
        }
        self._logger.log(LEVEL_STAGE, self._format(event))
        self.events.append(event)

    # ── task 事件 ──────────────────────────────────

    def task(self, task_id: str, status: str, **kw: Any) -> None:
        event = {"type": "task", "task_id": task_id, "status": status}
        event.update(kw)
        self._logger.info(self._format(event))
        self.events.append(event)

    # ── error 事件 ─────────────────────────────────

    def error(self, error_level: str, message: str, **kw: Any) -> None:
        event = {
            "type": "error",
            "error_level": error_level,
            "message": message[:200],
        }
        event.update(kw)
        self._logger.warning(self._format(event))
        self.events.append(event)

    # ── IO 事件（Agent 间数据传递） ─────────

    def io(self, from_agent: str, to_agent: str, payload_size: int) -> None:
        event = {
            "type": "io",
            "from": from_agent,
            "to": to_agent,
            "payload_size_bytes": payload_size,
        }
        self._logger.log(LEVEL_IO, self._format(event))
        self.events.append(event)

    # ── context manager 辅助 ───────────────

    def measure_stage(self, stage: str, **context: Any) -> "_StageCM":
        """with agent_log.measure_stage("design_planned"): ..."""
        return _StageCM(self, stage, context)

    # ── 辅助 ─────────────────────────────────────

    def _format(self, event: dict[str, Any]) -> str:
        if self.verbose:
            return json.dumps(event, ensure_ascii=False, default=str)
        # 精简模式
        t = event.get("type", "")
        if t == "stage_enter":
            return f"→ {event.get('stage')}"
        if t == "stage_exit":
            dur = event.get("duration_ms", 0)
            ok = "✓" if event.get("success") else "✗"
            return f"← {event.get('stage')} [{dur:.1f}ms] {ok}"
        if t == "task":
            return f"{event.get('status')} {event.get('task_id')}"
        if t == "error":
            return f"[{event.get('error_level')}] {event.get('message')}"
        if t == "io":
            return f"{event.get('from')} → {event.get('to')} ({event.get('payload_size_bytes')}B)"
        return str(event)

    def summary(self) -> dict[str, Any]:
        """返回日志汇总 — 用于测试和报告。"""
        stages_enter = [e for e in self.events if e.get("type") == "stage_enter"]
        stages_exit = [e for e in self.events if e.get("type") == "stage_exit"]
        errors = [e for e in self.events if e.get("type") == "error"]
        total_ms = sum(e.get("duration_ms", 0) for e in stages_exit)
        return {
            "total_events": len(self.events),
            "stages_entered": len(stages_enter),
            "stages_exited": len(stages_exit),
            "errors": len(errors),
            "total_stage_time_ms": round(total_ms, 2),
        }


class _StageCM:
    """measure_stage() 的 context manager 辅助。"""

    def __init__(self, logger: AgentLogger, stage: str, context: dict[str, Any]) -> None:
        self._logger = logger
        self._stage = stage
        self._context = context

    def __enter__(self) -> "_StageCM":
        self._logger.stage_enter(self._stage, **self._context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self._logger.stage_exit(self._stage, success=exc_type is None)
        return False  # 不抑制异常


# ── 单例 / 便捷工厂 ──────────────────────────

_default_loggers: dict[str, AgentLogger] = {}


def get_logger(name: str, verbose: bool = False) -> AgentLogger:
    """按名称获取 Agent logger（有缓存）。"""
    if name not in _default_loggers:
        _default_loggers[name] = AgentLogger(name, verbose=verbose)
    return _default_loggers[name]


def reset_loggers() -> None:
    """测试用：清空 logger 缓存。"""
    _default_loggers.clear()
