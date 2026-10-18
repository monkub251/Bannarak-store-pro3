# FIVE M CONTROL CENTER

A Windows desktop app plus a FiveM Lua resource for server administration, diagnostics, authorized testing and defensive security checks.
Black-and-white interface, all 12 feature categories, persistent profiles, hotkeys, structured logs and honest per-feature status.

> Read [docs/STATUS.md](docs/STATUS.md) first. The Lua handlers have never run on a live FiveM server and the `.exe` has not been built on Windows yet.
> Those are marked **Not Tested**, and nothing is marked Implemented without an automated test.

## Contents
| Path | What it is |
|---|---|
| `app/` | The desktop app (Python 3.10+, PySide6). `core/` is UI-free and unit-tested. |
| `fivem_resource/fmcc_control/` | The server resource. Copy this folder into your server's `resources/`. |
| `compat_profiles/` | Anti-cheat test checklists (BT, GhostX, Global, other). |
| `tests/` | Python tests and Lua tests. |
| `docs/` | Architecture, security notes, compatibility procedure, generated feature status. |
| `fmcc.spec`, `build_windows.bat`, `.github/workflows/build-windows.yml` | Windows build. |

## 1. Install the resource
1. Copy `fivem_resource/fmcc_control` to `resources/` on your server.
2. Open its `config.lua`. Replace the placeholder token with a long random string (24+ characters). Optional: adjust roles, catalogs, modules.
3. In `server.cfg` (OneSync must be on):
   ```
   set onesync on
   ensure fmcc_control
   add_ace group.admin fmcc.overlay allow   # only if you want the admin overlay
   ```
4. Restart the server. The console should print `API ready at http://<server-ip>:<port>/fmcc_control/api`.
   If it prints a warning about the token, the API refuses all requests until you fix it.

The resource works standalone. Inventory actions need ox_inventory, qb-core or es_extended (optional adapters, untested).
World time and weather control may conflict with other weather/time sync resources.

## 2. Run the app
From source (any OS with Python 3.10+):
```
pip install -r requirements.txt
python run.py
```
Then **Interface > Profiles**: enter the server address (for example `http://127.0.0.1:30120`), resource name, and your token, choose
**Save and test connection**. Use **Diagnostics > This PC** if anything is unclear; it explains each problem.

## 3. Build the Windows .exe
On Windows with Python 3.10+: double-click `build_windows.bat`. It installs dependencies, runs the tests, and builds `dist\FiveMControlCenter.exe`.
Or push to GitHub and run the **Build Windows exe** workflow; download the artifact. Neither route has been run yet: see Status.

## Using it
- **Overview**: connection state, pinned actions (star any action), recent activity.
- **Control** pages: every action has its own validated inputs. Destructive actions ask for confirmation.
- **Interface**: profiles, appearance (size, compact mode, animations, notifications), hotkeys (in-app, conflicts blocked), backups.
- **Diagnostics / Security / Access**: local checks, server monitors and integrity checks, compatibility results, process audit, audit logs.
- **Feature status**: the live status table.

Default hotkeys: Ctrl+1 to Ctrl+9 and Ctrl+0 for the main pages, Ctrl+K search, Ctrl+Shift+C compact mode, F5 check connection. All editable.

## Tests
```
./run_tests.sh        # Lua tests, then the Python suite
```
Last run in the build environment (Linux, Python 3.12, PySide6 6.12, Lua 5.4): 100 Python tests and 44 Lua checks passed.
They cover config, profiles, backups, hotkeys, parameter validation, the HTTP client against a mock server, logging redaction,
audit log, diagnostics, process inspection, compatibility profiles, Lua/Python consistency, SHA-256 against `hashlib`, Lua syntax,
and the full window driven offscreen. They do not cover a live FiveM server, Windows rendering, or any anti-cheat product.

## Known limitations
See `docs/STATUS.md`. In short: no free camera or noclip, no skeleton overlay, no aim tools (deliberately), no global hotkeys,
no weapon skins or vehicle presets, no combat anomaly analysis, no client-binary attestation, and no verified compatibility with any anti-cheat.

## Licence and responsibility
You are responsible for using this only on servers you are authorized to administer or test, and for following your anti-cheat vendor's terms.
