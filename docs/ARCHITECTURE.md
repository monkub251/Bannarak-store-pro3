# Architecture

```
FiveMControlCenter.exe  (Python + PySide6)                 FiveM server
 ├─ ui/        pages generated from the action registry     └─ fmcc_control (Lua resource)
 ├─ core/      config, profiles, hotkeys, client, audit,        ├─ server/main.lua      HTTP API, auth, rate limit, dispatch
 │             diagnostics, process audit, compat profiles      ├─ server/actions.lua   one handler per action
 └─ HTTPS/HTTP  POST /<resource>/api  + Bearer token  ───────►  ├─ server/security.lua  alerts, integrity, guarded events
                                                                ├─ server/core.lua      pure logic, unit-tested
                                                                └─ client/main.lua      effects on the target player only
```

## Why this stack
Python with PySide6 gives a native Windows window, a testable core that runs headless, and PyInstaller produces one `.exe`.
The Lua resource uses only documented FiveM interfaces: `SetHttpHandler`, `TriggerClientEvent`, KVP storage and standard natives.

## Request flow
1. The app validates input against `app/core/registry.py` and sends `{"action": "player.heal", "params": {"target": 3}}`.
2. The resource checks, in order: endpoint, token configured, lockout after failed logins, rate limit, token (constant-time compare),
   body size and JSON, action exists, module enabled, role permits the action, parameters valid.
3. The handler runs. Most actions send an event to the target's client; the reply says "dispatched", because the server cannot confirm the client applied it.
4. Both sides write an audit entry (the app locally, the server in `data/audit.json`). Tokens are never logged.

## Permissions
Tokens map to roles in `config.lua`. Patterns: `*`, `player.*`, `player.heal`, `!players.kick` (last match wins).
Every check happens in the server resource; the app UI never decides access.

## Adding an action
1. Add an `Action` in `app/core/registry.py`.
2. Add `A('category.name', function(a) ... end)` in `server/actions.lua` and, if it affects a client, a `RegisterNetEvent('fmcc:cl:<name>')` in `client/main.lua`.
3. Run `./run_tests.sh`: `tests/test_consistency.py` fails until the three agree.
4. Add a row to `app/core/feature_status.py` (start it as Not Tested) and regenerate `docs/STATUS.md`:
   `python -c "from app.core import feature_status as f; open('docs/STATUS.md','w').write(f.render_markdown()+'\n')"`
