"""Local, offline checks that explain problems before the user hits a network error."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import hotkeys as hk
from .config import ConfigManager, validate_url

OK, WARN, FAIL = "ok", "warn", "fail"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str


def _writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write-test"
        probe.write_text("x")
        probe.unlink()
        return True
    except OSError:
        return False


def local_checks(cfg: ConfigManager, load_warnings: list[str] | None = None) -> list[CheckResult]:
    out: list[CheckResult] = []
    out.append(CheckResult("Config file", WARN if load_warnings else OK,
                           "; ".join(load_warnings) if load_warnings else str(cfg.path)))
    out.append(CheckResult("Data folder is writable", OK if _writable(cfg.dir) else FAIL, str(cfg.dir)))
    name, profile = cfg.active()
    try:
        validate_url(profile["server_url"])
        out.append(CheckResult("Server address", OK, f'{profile["server_url"]} (profile "{name}")'))
    except ValueError as exc:
        out.append(CheckResult("Server address", FAIL, str(exc)))
    token = profile.get("token", "")
    if not token:
        out.append(CheckResult("API token", FAIL, "No token. Paste the one from the server's config.lua in Interface > Profiles."))
    elif len(token) < 24:
        out.append(CheckResult("API token", WARN, "Shorter than 24 characters; the server refuses tokens that short."))
    else:
        out.append(CheckResult("API token", OK, "Set (hidden)"))
    if profile["server_url"].startswith("http://") and not any(
            profile["server_url"].startswith(f"http://{h}") for h in ("127.0.0.1", "localhost", "[::1]")):
        out.append(CheckResult("Transport security", WARN, "The token travels unencrypted over http to a remote host. Prefer https or a VPN."))
    elif not profile.get("verify_tls", True):
        out.append(CheckResult("Transport security", WARN, "TLS verification is off for this profile."))
    else:
        out.append(CheckResult("Transport security", OK, "No issue found"))
    conflicts = hk.find_conflicts(cfg.data["hotkeys"])
    out.append(CheckResult("Hotkeys", FAIL if conflicts else OK,
                           "; ".join(f"{s}: {', '.join(a)}" for s, a in conflicts.items()) or "No conflicts"))
    backups = cfg.list_backups()
    out.append(CheckResult("Config backups", OK if backups else WARN,
                           f"{len(backups)} saved" if backups else "None yet. Create one in Interface > Backups."))
    try:
        import psutil  # noqa: F401
        out.append(CheckResult("Process audit support", OK, "psutil is available"))
    except ImportError:
        out.append(CheckResult("Process audit support", WARN, "psutil missing; process audit is unavailable"))
    return out
