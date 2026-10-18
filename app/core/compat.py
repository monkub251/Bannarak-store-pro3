"""Anti-cheat compatibility profiles: documented test checklists plus the evidence you record.

A profile never asserts compatibility. Status stays 'untested' until you record a result from a real, authorized test.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    id: str
    title: str
    how: str


@dataclass(frozen=True)
class CompatProfile:
    id: str
    name: str
    summary: str
    checks: tuple[Check, ...]


def load_profiles(folder: Path) -> list[CompatProfile]:
    out = []
    for file in sorted(Path(folder).glob("*.json")):
        try:
            raw = json.loads(file.read_text(encoding="utf-8"))
            out.append(CompatProfile(
                id=str(raw["id"]), name=str(raw["name"]), summary=str(raw.get("summary", "")),
                checks=tuple(Check(str(c["id"]), str(c["title"]), str(c["how"])) for c in raw["checks"]),
            ))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return out
