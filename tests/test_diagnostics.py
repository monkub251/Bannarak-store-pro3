from app.core import diagnostics
from app.core.config import ConfigManager


def by_name(results):
    return {r.name: r for r in results}


def test_fresh_config_flags_missing_token(tmp_path):
    cfg = ConfigManager(tmp_path / "config.json")
    r = by_name(diagnostics.local_checks(cfg))
    assert r["API token"].status == diagnostics.FAIL and "config.lua" in r["API token"].detail
    assert r["Server address"].status == diagnostics.OK
    assert r["Data folder is writable"].status == diagnostics.OK
    assert r["Hotkeys"].status == diagnostics.OK


def test_short_token_and_remote_http_warn(tmp_path):
    cfg = ConfigManager(tmp_path / "config.json")
    cfg.save_profile("default", {"token": "short", "server_url": "http://203.0.113.5:30120"})
    r = by_name(diagnostics.local_checks(cfg))
    assert r["API token"].status == diagnostics.WARN
    assert r["Transport security"].status == diagnostics.WARN


def test_good_profile_all_clear(tmp_path):
    cfg = ConfigManager(tmp_path / "config.json")
    cfg.save_profile("default", {"token": "x" * 30})
    cfg.save()
    cfg.backup()
    r = by_name(diagnostics.local_checks(cfg))
    assert r["API token"].status == diagnostics.OK and r["Transport security"].status == diagnostics.OK
    assert r["Config backups"].status == diagnostics.OK


def test_hotkey_conflict_detected(tmp_path):
    cfg = ConfigManager(tmp_path / "config.json")
    cfg.data["hotkeys"]["nav.player"] = cfg.data["hotkeys"]["nav.combat"]
    assert by_name(diagnostics.local_checks(cfg))["Hotkeys"].status == diagnostics.FAIL


def test_load_warnings_surface(tmp_path):
    cfg = ConfigManager(tmp_path / "config.json")
    r = by_name(diagnostics.local_checks(cfg, ["something was reset"]))
    assert r["Config file"].status == diagnostics.WARN and "reset" in r["Config file"].detail
