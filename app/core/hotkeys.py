"""Hotkey parsing, validation and conflict detection. Works without Qt so it can be tested headless."""
from __future__ import annotations

import re

MODIFIERS = ("Ctrl", "Alt", "Shift", "Meta")
_KEY = re.compile(r"^([A-Z0-9]|F([1-9]|1[0-2]))$")

DEFAULT_HOTKEYS = {
    "nav.dashboard": "Ctrl+1", "nav.player": "Ctrl+2", "nav.combat": "Ctrl+3", "nav.weapon": "Ctrl+4",
    "nav.fun": "Ctrl+5", "nav.vehicle": "Ctrl+6", "nav.players": "Ctrl+7", "nav.world": "Ctrl+8",
    "nav.inventory": "Ctrl+9", "nav.settings": "Ctrl+0", "nav.diag": "Ctrl+Shift+1", "nav.sec": "Ctrl+Shift+2",
    "nav.access": "Ctrl+Shift+3", "nav.features": "Ctrl+Shift+4", "nav.logs": "Ctrl+Shift+5",
    "ui.search": "Ctrl+K", "ui.compact": "Ctrl+Shift+C", "ui.refresh": "F5",
}

HOTKEY_LABELS = {
    "ui.search": "Focus search", "ui.compact": "Toggle compact mode", "ui.refresh": "Check connection",
}


def normalize(sequence: str) -> str:
    """Return the canonical form ('Ctrl+Shift+K') or raise ValueError."""
    if not isinstance(sequence, str) or not sequence.strip():
        raise ValueError("Press a key combination.")
    parts = [p.strip() for p in sequence.split("+")]
    if "" in parts:
        raise ValueError("Use the form Ctrl+K.")
    key = parts[-1].upper() if len(parts[-1]) == 1 else parts[-1].upper()
    mods = []
    for m in parts[:-1]:
        canon = next((x for x in MODIFIERS if x.lower() == m.lower()), None)
        if canon is None:
            raise ValueError(f"Unknown modifier: {m}")
        if canon in mods:
            raise ValueError(f"{canon} is used twice.")
        mods.append(canon)
    if not _KEY.match(key):
        raise ValueError("The last key must be a letter, a digit or F1 to F12.")
    if not mods and not key.startswith("F"):
        raise ValueError("Add Ctrl, Alt or Shift so normal typing is not captured.")
    ordered = [m for m in MODIFIERS if m in mods]
    return "+".join(ordered + [key])


def find_conflicts(hotkeys: dict[str, str]) -> dict[str, list[str]]:
    """Map each duplicated sequence to the actions that share it."""
    seen: dict[str, list[str]] = {}
    for action, seq in hotkeys.items():
        seen.setdefault(seq, []).append(action)
    return {seq: actions for seq, actions in seen.items() if len(actions) > 1}
