"""Honest per-feature status. Update this file when a feature's real state changes.

Implemented         implemented and verified by an automated test (see tests/)
Partially Implemented  some of it works; the note says what is missing
Blocked             cannot proceed; the note names the reason
Not Implemented     not built in this version
Not Tested          code exists, but it needs a live FiveM server or Windows to verify
"""
from __future__ import annotations

IMPL, PART, BLOCK, NOT, UNTESTED = "Implemented", "Partially Implemented", "Blocked", "Not Implemented", "Not Tested"
STATUSES = (IMPL, PART, BLOCK, NOT, UNTESTED)

LIVE = "Needs a live FiveM server (OneSync) to verify. Handler syntax is checked."

FEATURES: tuple[tuple[str, str, str, str], ...] = (
    ("player", "Player info, heal, armor, freeze, ped model", UNTESTED, LIVE),
    ("player", "Teleport to coordinates, player, waypoint, preset", UNTESTED, LIVE),
    ("player", "Free camera and noclip", NOT, "Not built in this version."),
    ("combat", "Custom crosshair, hit markers, practice statistics, target dummy", UNTESTED, LIVE),
    ("combat", "Admin overlay (names, distance, health) for ACE-permitted staff", UNTESTED, LIVE),
    ("combat", "Skeleton overlay", NOT, "Not built: it only helps a player on public servers."),
    ("combat", "Aimbot, silent aim, aim assist", NOT, "Deliberately not built: unfair-advantage tooling."),
    ("weapon", "Give weapon, set ammo, add component, remove all, current weapon", UNTESTED, LIVE),
    ("weapon", "Weapon skins and tints, presets, reload control", NOT, "Not built in this version."),
    ("fun", "Animations, scenarios, ragdoll, local clone (module off by default)", UNTESTED, LIVE),
    ("fun", "NPC interactions and visual effects", NOT, "Not built in this version."),
    ("vehicle", "Spawn, info, repair, delete, colors, max upgrades, catalog", UNTESTED, LIVE),
    ("vehicle", "Vehicle presets and special movement controls", NOT, "Not built in this version."),
    ("players", "Player list, search, notes, kick", UNTESTED, LIVE),
    ("players", "Spectate and stop spectating", UNTESTED, LIVE),
    ("world", "Time, weather, freeze time, entity counts", UNTESTED, LIVE + " May conflict with other weather/time sync resources."),
    ("world", "Location presets and waypoint management", PART, "Presets come from Config.Locations; no in-app preset editor."),
    ("inventory", "Item catalog and search", UNTESTED, LIVE),
    ("inventory", "Inventory view and give via ox_inventory, qb-core, es_extended", UNTESTED, "Adapters written from public APIs; never run against those frameworks."),
    ("inventory", "Inventory on a standalone server", BLOCK, "FiveM has no built-in inventory; a supported inventory resource is required."),
    ("ui", "Configuration save/load with validation and safe defaults", IMPL, "tests/test_config.py"),
    ("ui", "Backups, restore and corrupt-file recovery", IMPL, "tests/test_config.py"),
    ("ui", "Profile manager (add, edit, delete, switch)", IMPL, "tests/test_config.py, tests/test_ui_smoke.py"),
    ("ui", "Hotkey editor with validation and conflict detection", IMPL, "tests/test_hotkeys.py. Hotkeys work while the app window has focus."),
    ("ui", "Global (system-wide) hotkeys", NOT, "Not built; in-app shortcuts only."),
    ("ui", "UI scale, compact mode, animations toggle, notifications", IMPL, "tests/test_ui_smoke.py (offscreen, Linux)"),
    ("ui", "Favorites, quick actions and search", IMPL, "tests/test_config.py, tests/test_ui_smoke.py"),
    ("ui", "Theme settings", PART, "One monochrome theme; no theme switcher."),
    ("ui", "Preset manager", NOT, "Profiles cover server connections only."),
    ("ui", "Structured logging with secret redaction", IMPL, "tests/test_logging_audit.py"),
    ("diag", "Local checks (config, profile, token, folders, hotkeys)", IMPL, "tests/test_diagnostics.py"),
    ("diag", "Server status, resources, config validation, errors, performance counters", UNTESTED, LIVE),
    ("diag", "API client error mapping with actionable messages", IMPL, "tests/test_client.py (against a local mock server)"),
    ("sec", "Resource integrity baseline and check (SHA-256, manifest files)", UNTESTED, "SHA-256 verified against standard vectors and hashlib; the FiveM file-reading path needs a live server."),
    ("sec", "Entity-spawn, movement and event-rate monitoring with alerts", UNTESTED, "Alerts only, no automatic punishment. Thresholds are untuned heuristics. Rate limiter logic is unit-tested."),
    ("sec", "Identifier validation (masked output)", UNTESTED, "Format logic unit-tested in Lua; live path untested."),
    ("sec", "Process watchlist scan and loaded-module baseline diff", PART, "Unit-tested on Linux against a test process. Windows and the FiveM process are untested."),
    ("sec", "Combat anomaly analysis", NOT, "Not built in this version."),
    ("sec", "Client integrity verification", BLOCK, "A server resource cannot attest the client binary; this needs the anti-cheat vendor's own tooling."),
    ("sec", "Compatibility profiles (BT, GhostX, Global, other) with result recording", IMPL, "tests/test_compat.py. The checklists are documentation only."),
    ("sec", "Verified compatibility with BT, GhostX or Global", UNTESTED, "No evidence exists yet. Record results in Security > Compatibility after authorized tests."),
    ("access", "Role-based permissions enforced on the server for every action", UNTESTED, "Pattern matching is unit-tested; the HTTP path needs a live server."),
    ("access", "Local audit log of every action sent", IMPL, "tests/test_logging_audit.py"),
    ("access", "Server audit log and role listing", UNTESTED, LIVE),
    ("build", "Windows .exe build (PyInstaller)", UNTESTED, "Spec, batch script and GitHub Actions workflow are included; not run on Windows."),
)


def counts() -> dict[str, int]:
    out = {s: 0 for s in STATUSES}
    for _, _, status, _ in FEATURES:
        out[status] += 1
    return out


def render_markdown() -> str:
    from .registry import CATEGORY_BY_KEY
    lines = ["# Feature status", "", "Generated from `app/core/feature_status.py`. Nothing here is marked Implemented without an automated test.", ""]
    c = counts()
    lines += ["| Status | Features |", "|---|---|"] + [f"| {s} | {c[s]} |" for s in STATUSES] + [""]
    keys = list(dict.fromkeys(f[0] for f in FEATURES))
    for key in keys:
        title = CATEGORY_BY_KEY[key].title if key in CATEGORY_BY_KEY else "Build"
        lines += [f"## {title}", "", "| Feature | Status | Notes |", "|---|---|---|"]
        lines += [f"| {n} | {s} | {note} |" for k, n, s, note in FEATURES if k == key]
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_markdown())
