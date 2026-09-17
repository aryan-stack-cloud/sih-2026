"""Structured JSON logging with correlation-ID passthrough (NFR-008).

Every log line carries the same correlation IDs the Backend uses so a single simulation can be
traced across the Backend -> Ai-ml-2 -> Ai-ml-1 hop: ``simulation_id`` and ``training_run_id``.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from typing import Any

_correlation: ContextVar[dict[str, Any]] = ContextVar("correlation", default={})

_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
    "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
    "relativeCreated", "thread", "threadName", "processName", "process", "taskName",
    "message", "asctime",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(_correlation.get())
        # Anything passed via logger.info(..., extra={...}) lands here too.
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def set_correlation(**ids: Any) -> None:
    """Attach correlation IDs to every subsequent log line on this task/thread."""
    current = dict(_correlation.get())
    current.update({k: v for k, v in ids.items() if v is not None})
    _correlation.set(current)


def clear_correlation() -> None:
    _correlation.set({})


def configure(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
