# Security notes

## What this project will not do
No anti-cheat bypass or detection evasion, no HWID or identifier spoofing, no DLL injection or manual mapping,
no memory manipulation, no stealth, no aimbot, silent aim or aim assist, and no ESP for use on public servers.
`tests/test_consistency.py` fails if the action list gains obviously cheat-style actions.

## Protections that are built
- Server API refuses every request until a token of 24+ characters is set (placeholders are rejected).
- Constant-time token comparison, lockout after 5 failed logins per minute per address, request rate limit, body size cap.
- Role-based permissions enforced on the server for every action; modules can be switched off (`fun` is off by default).
- Catalog restrictions for vehicles and weapons; every parameter is validated server-side.
- The monitors (entity spawn bursts, on-foot speed, event spam, integrity changes) only raise alerts for human review.
- Identifiers are masked in all output. Tokens are redacted from logs and from the audit file.
- `config.lua` is a server-only script; the manifest never sends it to clients (checked by a test).

## What you must do
- Use `https` (reverse proxy) or a VPN if the server is not on the same machine. Over plain `http` the token travels unencrypted.
- The app stores tokens in plaintext in `%APPDATA%\FiveMControlCenter\config.json`. Protect that folder and your backups.
- Treat alert thresholds as starting points; they are untuned heuristics and can false-positive (respawns, special game modes).
