"""Persistent configuration: validation, safe defaults, atomic saves, backups and profiles."""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

from . import hotkeys as hk
from .paths import data_dir

SCHEMA = 1
PROFILE_NAME = re.compile(r"^[A-Za-z0-9 _.-]{1,40}$")
RESOURCE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
COMPAT_STATUSES = ("untested", "pass", "partial", "fail")
MAX_BACKUPS = 10

DEFAULT_PROFILE = {
    "server_url": "http://127.0.0.1:30120", "resource": "fmcc_control", "token": "", "timeout": 6.0, "verify_tls": True,
}
DEFAULT_UI = {"scale": 1.0, "compact": False, "notifications": True, "animations": True}


def default_config() -> dict:
    return {
        "schema": SCHEMA,
        "active_profile": "default",
        "profiles": {"default": copy.deepcopy(DEFAULT_PROFILE)},
        "ui": copy.deepcopy(DEFAULT_UI),
        "hotkeys": dict(hk.DEFAULT_HOTKEYS),
        "favorites": [],
        "process_watchlist": [],
        "compat_results": {},
    }


def validate_url(url: str) -> str:
    """Return a normalized base URL or raise ValueError with a fix the user can act on."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Enter the server address, for example http://127.0.0.1:30120")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError("The address must start with http:// or https://")
    if not parsed.hostname:
        raise ValueError("The address has no host name.")
    if parsed.username or parsed.password:
        raise ValueError("Do not put credentials in the address; use the token field.")
    try:
        parsed.port
    except ValueError:
        raise ValueError("The port must be a number from 1 to 65535.") from None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def sanitize_profile(raw: object) -> tuple[dict, list[str]]:
    """Return (clean profile, warnings). Invalid fields fall back to safe defaults."""
    out, warnings = copy.deepcopy(DEFAULT_PROFILE), []
    raw = raw if isinstance(raw, dict) else {}
    if "server_url" in raw:
        try:
            out["server_url"] = validate_url(raw["server_url"])
        except ValueError as exc:
            warnings.append(f"server_url reset: {exc}")
    if "resource" in raw:
        if isinstance(raw["resource"], str) and RESOURCE_NAME.match(raw["resource"]):
            out["resource"] = raw["resource"]
        else:
            warnings.append("resource name reset: use letters, digits, _ . - only")
    if isinstance(raw.get("token"), str):
        out["token"] = raw["token"].strip()[:256]
    t = raw.get("timeout")
    if isinstance(t, (int, float)) and not isinstance(t, bool) and 1 <= t <= 60:
        out["timeout"] = float(t)
    elif "timeout" in raw:
        warnings.append("timeout reset: use 1 to 60 seconds")
    if isinstance(raw.get("verify_tls"), bool):
        out["verify_tls"] = raw["verify_tls"]
    return out, warnings


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class ConfigManager:
    def __init__(self, path: Path | None = None):
        self.dir = path.parent if path else data_dir()
        self.path = path or self.dir / "config.json"
        self.backup_dir = self.dir / "backups"
        self.data = default_config()

    # ------------------------------------------------------------ load / save
    def load(self) -> list[str]:
        warnings: list[str] = []
        self.data = default_config()
        if not self.path.exists():
            return warnings
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("top level must be an object")
        except (OSError, ValueError) as exc:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            moved = self.path.with_name(f"config.corrupt-{stamp}.json")
            try:
                os.replace(self.path, moved)
                warnings.append(f"Config was unreadable ({exc}). It was kept as {moved.name} and defaults were loaded.")
            except OSError:
                warnings.append(f"Config was unreadable ({exc}). Defaults were loaded.")
            return warnings
        self._merge(raw, warnings)
        return warnings

    def _merge(self, raw: dict, warnings: list[str]) -> None:
        d = self.data
        profiles = {}
        for name, prof in (raw.get("profiles") or {}).items() if isinstance(raw.get("profiles"), dict) else []:
            if not isinstance(name, str) or not PROFILE_NAME.match(name):
                warnings.append(f"Profile {str(name)[:20]!r} skipped: invalid name")
                continue
            clean, w = sanitize_profile(prof)
            profiles[name] = clean
            warnings += [f"[{name}] {m}" for m in w]
        if profiles:
            d["profiles"] = profiles
        active = raw.get("active_profile")
        d["active_profile"] = active if active in d["profiles"] else next(iter(d["profiles"]))
        if isinstance(raw.get("ui"), dict):
            ui = raw["ui"]
            s = ui.get("scale")
            if isinstance(s, (int, float)) and not isinstance(s, bool) and 0.8 <= s <= 1.6:
                d["ui"]["scale"] = float(s)
            elif "scale" in ui:
                warnings.append("UI scale reset: use 0.8 to 1.6")
            for key in ("compact", "notifications", "animations"):
                if isinstance(ui.get(key), bool):
                    d["ui"][key] = ui[key]
        if isinstance(raw.get("hotkeys"), dict):
            for action, seq in raw["hotkeys"].items():
                if action in hk.DEFAULT_HOTKEYS:
                    try:
                        d["hotkeys"][action] = hk.normalize(seq)
                    except ValueError as exc:
                        warnings.append(f"Hotkey {action} reset: {exc}")
        if isinstance(raw.get("favorites"), list):
            d["favorites"] = [f for f in raw["favorites"] if isinstance(f, str) and re.match(r"^[a-z_]+\.[a-z_]+$", f)][:50]
        if isinstance(raw.get("process_watchlist"), list):
            d["process_watchlist"] = self.clean_watchlist(raw["process_watchlist"])
        if isinstance(raw.get("compat_results"), dict):
            for pid, res in raw["compat_results"].items():
                if isinstance(res, dict) and res.get("status") in COMPAT_STATUSES and isinstance(pid, str):
                    d["compat_results"][pid[:40]] = {
                        "status": res["status"], "date": str(res.get("date", ""))[:10],
                        "build": str(res.get("build", ""))[:60], "notes": str(res.get("notes", ""))[:500],
                    }

    @staticmethod
    def clean_watchlist(items) -> list[str]:
        out = []
        for item in items:
            if isinstance(item, str):
                name = item.strip().lower()[:64]
                if name and name not in out:
                    out.append(name)
        return out[:100]

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(self.path, json.dumps(self.data, indent=2, sort_keys=True))

    # ------------------------------------------------------------ backups
    def backup(self, reason: str = "manual") -> Path | None:
        if not self.path.exists():
            return None
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^a-z0-9]+", "-", reason.lower()).strip("-")[:20] or "backup"
        target = self.backup_dir / f"config-{time.strftime('%Y%m%d-%H%M%S')}-{safe}.json"
        n = 1
        while target.exists():
            target = target.with_name(f"{target.stem}-{n}.json")
            n += 1
        shutil.copy2(self.path, target)
        for old in self.list_backups()[MAX_BACKUPS:]:
            old.unlink(missing_ok=True)
        return target

    def list_backups(self) -> list[Path]:
        if not self.backup_dir.exists():
            return []
        return sorted(self.backup_dir.glob("config-*.json"), key=lambda p: p.name, reverse=True)

    def restore(self, backup: Path) -> list[str]:
        """Validate a backup, keep the current file as a backup, then load it."""
        backup = Path(backup)
        raw = json.loads(backup.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or "profiles" not in raw:
            raise ValueError("That file is not a Control Center backup.")
        self.backup("before-restore")
        shutil.copy2(backup, self.path)
        return self.load()

    # ------------------------------------------------------------ profiles
    @property
    def profiles(self) -> dict:
        return self.data["profiles"]

    def active(self) -> tuple[str, dict]:
        name = self.data["active_profile"]
        return name, self.data["profiles"][name]

    def save_profile(self, name: str, fields: dict) -> None:
        if not PROFILE_NAME.match(name or ""):
            raise ValueError("Profile names use letters, digits, spaces, _ . - (up to 40 characters).")
        merged = dict(self.data["profiles"].get(name, DEFAULT_PROFILE))
        merged.update(fields)
        merged["server_url"] = validate_url(merged["server_url"])
        if not RESOURCE_NAME.match(str(merged["resource"])):
            raise ValueError("Resource names use letters, digits, _ . - only.")
        try:
            timeout = float(merged["timeout"])
        except (TypeError, ValueError):
            raise ValueError("Timeout must be a number of seconds.") from None
        if not 1 <= timeout <= 60:
            raise ValueError("Timeout must be between 1 and 60 seconds.")
        merged["timeout"] = timeout
        merged["token"] = str(merged.get("token", "")).strip()[:256]
        merged["verify_tls"] = bool(merged.get("verify_tls", True))
        self.data["profiles"][name] = merged

    def delete_profile(self, name: str) -> None:
        if name not in self.data["profiles"]:
            raise ValueError("That profile does not exist.")
        if len(self.data["profiles"]) == 1:
            raise ValueError("Keep at least one profile.")
        del self.data["profiles"][name]
        if self.data["active_profile"] == name:
            self.data["active_profile"] = next(iter(self.data["profiles"]))

    def set_active(self, name: str) -> None:
        if name not in self.data["profiles"]:
            raise ValueError("That profile does not exist.")
        self.data["active_profile"] = name

    # ------------------------------------------------------------ misc settings
    def set_ui(self, **kw) -> None:
        if "scale" in kw and not (isinstance(kw["scale"], (int, float)) and 0.8 <= kw["scale"] <= 1.6):
            raise ValueError("Scale must be between 0.8 and 1.6.")
        for key, value in kw.items():
            if key not in DEFAULT_UI:
                raise ValueError(f"Unknown setting: {key}")
            self.data["ui"][key] = float(value) if key == "scale" else bool(value)

    def set_hotkey(self, action: str, sequence: str) -> str:
        if action not in hk.DEFAULT_HOTKEYS:
            raise ValueError("Unknown hotkey.")
        norm = hk.normalize(sequence)
        for other, seq in self.data["hotkeys"].items():
            if other != action and seq == norm:
                raise ValueError(f"{norm} is already used by {other}.")
        self.data["hotkeys"][action] = norm
        return norm

    def toggle_favorite(self, action_id: str) -> bool:
        favs = self.data["favorites"]
        if action_id in favs:
            favs.remove(action_id)
            return False
        favs.append(action_id)
        return True

    def set_compat_result(self, profile_id: str, status: str, build: str = "", notes: str = "") -> None:
        if status not in COMPAT_STATUSES:
            raise ValueError("Status must be untested, pass, partial or fail.")
        self.data["compat_results"][profile_id] = {
            "status": status, "date": time.strftime("%Y-%m-%d"), "build": build.strip()[:60], "notes": notes.strip()[:500],
        }
