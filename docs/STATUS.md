# Feature status

Generated from `app/core/feature_status.py`. Nothing here is marked Implemented without an automated test.

| Status | Features |
|---|---|
| Implemented | 11 |
| Partially Implemented | 3 |
| Blocked | 2 |
| Not Implemented | 9 |
| Not Tested | 20 |

## Player and movement

| Feature | Status | Notes |
|---|---|---|
| Player info, heal, armor, freeze, ped model | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |
| Teleport to coordinates, player, waypoint, preset | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |
| Free camera and noclip | Not Implemented | Not built in this version. |

## Combat training

| Feature | Status | Notes |
|---|---|---|
| Custom crosshair, hit markers, practice statistics, target dummy | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |
| Admin overlay (names, distance, health) for ACE-permitted staff | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |
| Skeleton overlay | Not Implemented | Not built: it only helps a player on public servers. |
| Aimbot, silent aim, aim assist | Not Implemented | Deliberately not built: unfair-advantage tooling. |

## Weapons

| Feature | Status | Notes |
|---|---|---|
| Give weapon, set ammo, add component, remove all, current weapon | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |
| Weapon skins and tints, presets, reload control | Not Implemented | Not built in this version. |

## Fun and testing

| Feature | Status | Notes |
|---|---|---|
| Animations, scenarios, ragdoll, local clone (module off by default) | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |
| NPC interactions and visual effects | Not Implemented | Not built in this version. |

## Vehicles

| Feature | Status | Notes |
|---|---|---|
| Spawn, info, repair, delete, colors, max upgrades, catalog | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |
| Vehicle presets and special movement controls | Not Implemented | Not built in this version. |

## Players

| Feature | Status | Notes |
|---|---|---|
| Player list, search, notes, kick | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |
| Spectate and stop spectating | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |

## World

| Feature | Status | Notes |
|---|---|---|
| Time, weather, freeze time, entity counts | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. May conflict with other weather/time sync resources. |
| Location presets and waypoint management | Partially Implemented | Presets come from Config.Locations; no in-app preset editor. |

## Inventory

| Feature | Status | Notes |
|---|---|---|
| Item catalog and search | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |
| Inventory view and give via ox_inventory, qb-core, es_extended | Not Tested | Adapters written from public APIs; never run against those frameworks. |
| Inventory on a standalone server | Blocked | FiveM has no built-in inventory; a supported inventory resource is required. |

## Interface

| Feature | Status | Notes |
|---|---|---|
| Configuration save/load with validation and safe defaults | Implemented | tests/test_config.py |
| Backups, restore and corrupt-file recovery | Implemented | tests/test_config.py |
| Profile manager (add, edit, delete, switch) | Implemented | tests/test_config.py, tests/test_ui_smoke.py |
| Hotkey editor with validation and conflict detection | Implemented | tests/test_hotkeys.py. Hotkeys work while the app window has focus. |
| Global (system-wide) hotkeys | Not Implemented | Not built; in-app shortcuts only. |
| UI scale, compact mode, animations toggle, notifications | Implemented | tests/test_ui_smoke.py (offscreen, Linux) |
| Favorites, quick actions and search | Implemented | tests/test_config.py, tests/test_ui_smoke.py |
| Theme settings | Partially Implemented | One monochrome theme; no theme switcher. |
| Preset manager | Not Implemented | Profiles cover server connections only. |
| Structured logging with secret redaction | Implemented | tests/test_logging_audit.py |

## Diagnostics

| Feature | Status | Notes |
|---|---|---|
| Local checks (config, profile, token, folders, hotkeys) | Implemented | tests/test_diagnostics.py |
| Server status, resources, config validation, errors, performance counters | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |
| API client error mapping with actionable messages | Implemented | tests/test_client.py (against a local mock server) |

## Security

| Feature | Status | Notes |
|---|---|---|
| Resource integrity baseline and check (SHA-256, manifest files) | Not Tested | SHA-256 verified against standard vectors and hashlib; the FiveM file-reading path needs a live server. |
| Entity-spawn, movement and event-rate monitoring with alerts | Not Tested | Alerts only, no automatic punishment. Thresholds are untuned heuristics. Rate limiter logic is unit-tested. |
| Identifier validation (masked output) | Not Tested | Format logic unit-tested in Lua; live path untested. |
| Process watchlist scan and loaded-module baseline diff | Partially Implemented | Unit-tested on Linux against a test process. Windows and the FiveM process are untested. |
| Combat anomaly analysis | Not Implemented | Not built in this version. |
| Client integrity verification | Blocked | A server resource cannot attest the client binary; this needs the anti-cheat vendor's own tooling. |
| Compatibility profiles (BT, GhostX, Global, other) with result recording | Implemented | tests/test_compat.py. The checklists are documentation only. |
| Verified compatibility with BT, GhostX or Global | Not Tested | No evidence exists yet. Record results in Security > Compatibility after authorized tests. |

## Access

| Feature | Status | Notes |
|---|---|---|
| Role-based permissions enforced on the server for every action | Not Tested | Pattern matching is unit-tested; the HTTP path needs a live server. |
| Local audit log of every action sent | Implemented | tests/test_logging_audit.py |
| Server audit log and role listing | Not Tested | Needs a live FiveM server (OneSync) to verify. Handler syntax is checked. |

## Build

| Feature | Status | Notes |
|---|---|---|
| Windows .exe build (PyInstaller) | Not Tested | Spec, batch script and GitHub Actions workflow are included; not run on Windows. |

