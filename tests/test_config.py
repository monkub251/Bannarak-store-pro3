import json

import pytest

from app.core import hotkeys as hk
from app.core.config import ConfigManager, validate_url, default_config


def make(tmp_path):
    return ConfigManager(tmp_path / "config.json")


def test_defaults_when_missing(tmp_path):
    cfg = make(tmp_path)
    assert cfg.load() == []
    assert cfg.data == default_config()
    assert cfg.active()[0] == "default"


def test_save_load_roundtrip(tmp_path):
    cfg = make(tmp_path)
    cfg.save_profile("test server", {"server_url": "https://example.org:30120/", "token": "x" * 30, "timeout": "10"})
    cfg.set_active("test server")
    cfg.set_ui(scale=1.25, compact=True)
    cfg.toggle_favorite("player.heal")
    cfg.save()
    again = make(tmp_path)
    assert again.load() == []
    assert again.active()[1]["server_url"] == "https://example.org:30120"
    assert again.active()[1]["timeout"] == 10.0
    assert again.data["ui"]["scale"] == 1.25 and again.data["ui"]["compact"] is True
    assert again.data["favorites"] == ["player.heal"]


def test_corrupt_file_is_kept_and_defaults_load(tmp_path):
    (tmp_path / "config.json").write_text("{not json")
    cfg = make(tmp_path)
    warnings = cfg.load()
    assert warnings and "unreadable" in warnings[0]
    assert cfg.data == default_config()
    assert list(tmp_path.glob("config.corrupt-*.json"))


def test_invalid_values_fall_back_with_warnings(tmp_path):
    bad = {"profiles": {"ok": {"server_url": "ftp://x", "timeout": 999, "resource": "bad name!"}, "bad/name": {}},
           "ui": {"scale": 9}, "hotkeys": {"ui.search": "K"}, "active_profile": "missing", "favorites": ["player.heal", "../x", 5]}
    (tmp_path / "config.json").write_text(json.dumps(bad))
    cfg = make(tmp_path)
    warnings = " | ".join(cfg.load())
    assert "server_url reset" in warnings and "timeout reset" in warnings and "resource name reset" in warnings
    assert "skipped" in warnings and "UI scale reset" in warnings and "Hotkey ui.search reset" in warnings
    assert cfg.active() == ("ok", cfg.profiles["ok"])
    assert cfg.profiles["ok"]["server_url"] == "http://127.0.0.1:30120"
    assert cfg.data["ui"]["scale"] == 1.0
    assert cfg.data["hotkeys"]["ui.search"] == "Ctrl+K"
    assert cfg.data["favorites"] == ["player.heal"]


@pytest.mark.parametrize("url", ["", "127.0.0.1:30120", "ftp://a", "http://", "http://user:pw@host", "http://host:99999"])
def test_bad_urls_rejected(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_good_url_normalized():
    assert validate_url(" http://Host:30120/ ") == "http://Host:30120"


def test_profile_rules(tmp_path):
    cfg = make(tmp_path)
    with pytest.raises(ValueError):
        cfg.save_profile("bad/name", {})
    with pytest.raises(ValueError):
        cfg.save_profile("a", {"timeout": "abc"})
    with pytest.raises(ValueError):
        cfg.save_profile("a", {"timeout": "0"})
    cfg.save_profile("second", {"token": "t" * 30})
    cfg.set_active("second")
    cfg.delete_profile("second")
    assert cfg.data["active_profile"] == "default"
    with pytest.raises(ValueError):
        cfg.delete_profile("default")  # last profile


def test_backup_and_restore(tmp_path):
    cfg = make(tmp_path)
    cfg.save_profile("keep", {"token": "k" * 30})
    cfg.save()
    backup = cfg.backup("manual")
    assert backup.exists()
    cfg.delete_profile("keep")
    cfg.save()
    cfg.restore(backup)
    assert "keep" in cfg.profiles
    assert any("before-restore" in p.name for p in cfg.list_backups())


def test_backup_rotation(tmp_path):
    cfg = make(tmp_path)
    cfg.save()
    for _ in range(14):
        cfg.backup("x")
    assert len(cfg.list_backups()) == 10


def test_restore_rejects_foreign_file(tmp_path):
    cfg = make(tmp_path)
    cfg.save()
    other = tmp_path / "other.json"
    other.write_text('{"hello": 1}')
    with pytest.raises(ValueError):
        cfg.restore(other)


def test_hotkey_conflict_blocked(tmp_path):
    cfg = make(tmp_path)
    with pytest.raises(ValueError, match="already used"):
        cfg.set_hotkey("nav.player", "ctrl+1")
    assert cfg.set_hotkey("nav.player", "alt+p") == "Alt+P"
    assert hk.find_conflicts(cfg.data["hotkeys"]) == {}


def test_favorites_toggle(tmp_path):
    cfg = make(tmp_path)
    assert cfg.toggle_favorite("player.heal") is True
    assert cfg.toggle_favorite("player.heal") is False


def test_compat_result_validation(tmp_path):
    cfg = make(tmp_path)
    with pytest.raises(ValueError):
        cfg.set_compat_result("bt", "works-great")
    cfg.set_compat_result("bt", "partial", "v1", "kicked once")
    cfg.save()
    again = make(tmp_path)
    again.load()
    assert again.data["compat_results"]["bt"]["status"] == "partial"


def test_save_is_atomic_no_tmp_left(tmp_path):
    cfg = make(tmp_path)
    cfg.save()
    assert not list(tmp_path.glob("*.tmp"))
