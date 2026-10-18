"""Local audit trail of every action this app sent, plus redaction helpers."""
from __future__ import annotations

import json
import time
from pathlib import Path

SECRET_KEYS = {"token", "password", "secret", "authorization"}
MAX_BYTES = 1_000_000


def redact(value):
    if isinstance(value, dict):
        return {k: ("[hidden]" if str(k).lower() in SECRET_KEYS else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str) and len(value) > 200:
        return value[:200] + "..."
    return value


class AuditLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def add(self, profile: str, action: str, params: dict, ok: bool, message: str = "") -> None:
        entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "profile": profile, "action": action,
                 "params": redact(params), "ok": ok, "message": message[:300]}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size > MAX_BYTES:
            self.path.replace(self.path.with_suffix(".old.jsonl"))
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    def tail(self, n: int = 100) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines()[-n:]:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return list(reversed(out))
