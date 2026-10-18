"""Structured application logging with secret redaction and an in-memory ring for the Logs page."""
from __future__ import annotations

import logging
import re
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path

_SECRET = re.compile(r"(?i)(bearer\s+|token['\"]?\s*[:=]\s*['\"]?)[^\s'\",}]+")


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _SECRET.sub(r"\1[hidden]", record.getMessage())
        record.args = ()
        return True


class RingHandler(logging.Handler):
    def __init__(self, size: int = 500):
        super().__init__()
        self.records: deque = deque(maxlen=size)

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append((record.created, record.levelname, record.getMessage()))


def setup(log_dir: Path) -> RingHandler:
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("fmcc")
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    ring = RingHandler()
    file_handler = RotatingFileHandler(log_dir / "app.log", maxBytes=500_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    for h in (file_handler, ring):
        h.addFilter(RedactFilter())
        root.addHandler(h)
    return ring
