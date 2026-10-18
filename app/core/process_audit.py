"""Read-only process and module inspection for authorized, defensive testing on your own PC.

Nothing here modifies, injects into or hides from any process. The watchlist is yours: no signature database ships.
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    import psutil
except ImportError:  # the UI explains this instead of crashing
    psutil = None

GAME_PREFIXES = ("fivem", "gta5", "gtav", "fivem_b")
MODULE_SUFFIXES = (".dll", ".exe", ".so", ".asi", ".ocx")


class ProcessAuditError(Exception):
    pass


def available() -> bool:
    return psutil is not None


def list_processes() -> list[dict]:
    if psutil is None:
        raise ProcessAuditError("psutil is not installed. Run: pip install psutil")
    out = []
    for p in psutil.process_iter(["pid", "name"]):
        name = p.info.get("name")
        if name:
            out.append({"pid": p.info["pid"], "name": name})
    return out


def watchlist_hits(watchlist: list[str], processes: list[dict]) -> list[dict]:
    wanted = {w.lower() for w in watchlist}
    return [p for p in processes if p["name"].lower() in wanted or p["name"].lower().removesuffix(".exe") in wanted]


def game_processes(processes: list[dict]) -> list[dict]:
    return [p for p in processes if p["name"].lower().startswith(GAME_PREFIXES)]


def module_snapshot(pid: int) -> list[str]:
    if psutil is None:
        raise ProcessAuditError("psutil is not installed. Run: pip install psutil")
    try:
        maps = psutil.Process(pid).memory_maps()
    except psutil.NoSuchProcess:
        raise ProcessAuditError(f"Process {pid} is no longer running.") from None
    except (psutil.AccessDenied, PermissionError):
        raise ProcessAuditError("Access denied. Run Control Center as the same user as the game, and with the same elevation.") from None
    paths = {m.path for m in maps if m.path.lower().endswith(MODULE_SUFFIXES)}
    return sorted(paths, key=str.lower)


def save_baseline(path: Path, pid_name: str, modules: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"process": pid_name, "modules": modules}, indent=2), encoding="utf-8")


def load_baseline(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data.get("modules"), list) else None
    except (OSError, ValueError, AttributeError):
        return None


def diff(baseline: list[str], current: list[str]) -> dict:
    b, c = {m.lower(): m for m in baseline}, {m.lower(): m for m in current}
    return {"added": sorted(c[k] for k in c.keys() - b.keys()), "removed": sorted(b[k] for k in b.keys() - c.keys())}
