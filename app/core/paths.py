"""Filesystem locations. No machine-specific paths: everything derives from the user profile or the bundle."""
import os
import sys
from pathlib import Path

APP_NAME = "FiveMControlCenter"


def data_dir() -> Path:
    override = os.environ.get("FMCC_DATA_DIR")
    if override:
        path = Path(override)
    elif os.name == "nt":
        path = Path(os.environ.get("APPDATA") or Path.home()) / APP_NAME
    else:
        path = Path.home() / ".config" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundle_dir() -> Path:
    """Folder that holds bundled read-only assets (compat_profiles). Works from source and from PyInstaller."""
    frozen = getattr(sys, "_MEIPASS", None)
    return Path(frozen) if frozen else Path(__file__).resolve().parents[2]
