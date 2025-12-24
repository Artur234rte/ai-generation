import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any, MutableMapping

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    """Фильтр request_id."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.__dict__["request_id"] = request_id_ctx_var.get("")
        return True


class JsonFormatter(logging.Formatter):
    """JSON-формат логов."""

    def format(self, record: logging.LogRecord) -> str:
        base: MutableMapping[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            base["request_id"] = request_id
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
            }:
                continue
            if key == "request_id":
                continue
            base[key] = value

        return json.dumps(base, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """Настроить логирование."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
