"""
Structured logging configuration.

Provides both human-readable and JSON-structured log formatters.
Called once at application startup via ``configure_logging()``.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class _StructuredFormatter(logging.Formatter):
    """Emits one JSON object per log line for machine consumption."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        # Attach optional contextual extras
        for key in ("node", "session_id", "latency_ms", "event_type", "provider"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = str(record.exc_info[1])
        return json.dumps(entry, default=str)


_HUMAN_FMT = "%(asctime)s | %(levelname)-7s | %(name)-30s | %(message)s"
_HUMAN_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    level: str = "INFO",
    *,
    structured: bool = False,
) -> None:
    """Bootstrap application logging.

    Call exactly once, before any other import triggers a log statement.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove any pre-existing handlers (e.g. from pytest)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if structured:
        handler.setFormatter(_StructuredFormatter())
    else:
        handler.setFormatter(logging.Formatter(_HUMAN_FMT, datefmt=_HUMAN_DATEFMT))

    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
