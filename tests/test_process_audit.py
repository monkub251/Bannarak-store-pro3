import os

import pytest

from app.core import process_audit as pa

pytestmark = pytest.mark.skipif(not pa.available(), reason="psutil not installed")


def test_lists_current_process():
    procs = pa.list_processes()
    assert any(p["pid"] == os.getpid() for p in procs)


def test_watchlist_matching_is_case_and_extension_insensitive():
    procs = [{"pid": 1, "name": "Evil.EXE"}, {"pid": 2, "name": "calc.exe"}]
    assert pa.watchlist_hits(["evil"], procs) == [procs[0]]
    assert pa.watchlist_hits(["evil.exe"], procs) == [procs[0]]
    assert pa.watchlist_hits([], procs) == []


def test_game_process_detection():
    procs = [{"pid": 1, "name": "FiveM.exe"}, {"pid": 2, "name": "GTA5.exe"}, {"pid": 3, "name": "notepad.exe"}]
    assert [p["pid"] for p in pa.game_processes(procs)] == [1, 2]


def test_module_snapshot_of_own_process_and_diff(tmp_path):
    mods = pa.module_snapshot(os.getpid())
    assert mods and all(m.lower().endswith(pa.MODULE_SUFFIXES) for m in mods)
    path = tmp_path / "b.json"
    pa.save_baseline(path, "python", mods)
    base = pa.load_baseline(path)
    assert base["modules"] == mods
    d = pa.diff(base["modules"], mods + ["/tmp/new_thing.so"])
    assert d == {"added": ["/tmp/new_thing.so"], "removed": []}
    assert pa.diff(mods, mods[1:])["removed"] == [mods[0]]


def test_missing_process_and_bad_baseline(tmp_path):
    with pytest.raises(pa.ProcessAuditError):
        pa.module_snapshot(999999)
    assert pa.load_baseline(tmp_path / "nope.json") is None
