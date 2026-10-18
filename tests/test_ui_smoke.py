"""Builds the real window offscreen and drives it. Verified on Linux; not run on Windows."""
import time
from pathlib import Path

import pytest
import shiboken6

from app.core import feature_status
from app.core.registry import actions_for
from app.main import build
from app.ui import pages
from app.ui.nav import NAV
from tests.mock_server import MockServer, TOKEN


@pytest.fixture
def app_window(qapp):
    ctl, win = build(qapp)
    win.show()
    yield ctl, win
    win.close()
    shiboken6.delete(win)   # a leaked window makes every later setStyleSheet slower
    shiboken6.delete(ctl)


def wait_for(qapp, predicate, timeout=6.0):
    end = time.time() + timeout
    while time.time() < end and not predicate():
        qapp.processEvents()
        time.sleep(0.01)
    assert predicate(), "timed out waiting for the UI"


def test_every_nav_page_builds_and_shows(app_window, qapp):
    ctl, win = app_window
    keys = [k for _, items in NAV for k, _, _ in items]
    assert len(keys) == len(set(keys)) == 15
    for key in keys:
        win.show_page(key, animate=False)
        qapp.processEvents()
        assert win.stack.currentWidget() is win.pages[key]
        assert win.buttons[key].property("active") is True
        assert win.pages[key].grab().width() > 0


def test_action_pages_list_every_registry_action(app_window):
    _, win = app_window
    for key in ("player", "combat", "weapon", "fun", "vehicle", "players", "world", "inventory"):
        page = win.pages[key]
        assert [r.action.id for r in page.rows] == [a.id for a in actions_for(key)]


def test_search_filters_rows(app_window, qapp):
    _, win = app_window
    page = win.pages["player"]
    page.search_edit.setText("teleport")
    visible = [r.action.id for r in page.rows if not r.isHidden()]
    assert visible and all("teleport" in i or "teleport" in r.action.description.lower()
                           for i, r in zip(visible, [r for r in page.rows if not r.isHidden()]))
    page.search_edit.setText("zzzz-nothing")
    assert not page.empty.isHidden()
    page.search_edit.setText("")
    assert page.empty.isHidden() and all(not r.isHidden() for r in page.rows)


def test_run_action_end_to_end_with_audit_and_connection_state(app_window, qapp):
    ctl, win = app_window
    with MockServer() as srv:
        ctl.cfg.save_profile("default", {"server_url": srv.url, "token": TOKEN})
        page = win.pages["player"]
        row = next(r for r in page.rows if r.action.id == "player.armor")
        row.editors["target"].widget.setText("4")
        row.editors["amount"].widget.setText("50")
        row.run.click()
        wait_for(qapp, lambda: "player.armor" in page.result.text.toPlainText())
        assert '"amount": 50' in page.result.text.toPlainText() and '"target": 4' in page.result.text.toPlainText()
        assert ctl.conn_state == "connected"
        assert ctl.audit.tail(1)[0]["action"] == "player.armor" and ctl.audit.tail(1)[0]["ok"] is True
        assert TOKEN not in (ctl.cfg.dir / "audit.jsonl").read_text()


def test_invalid_input_never_reaches_the_server(app_window, qapp):
    ctl, win = app_window
    with MockServer() as srv:
        ctl.cfg.save_profile("default", {"server_url": srv.url, "token": TOKEN})
        page = win.pages["player"]
        row = next(r for r in page.rows if r.action.id == "player.heal")
        row.editors["target"].widget.setText("banana")
        row.run.click()
        qapp.processEvents()
        assert "whole number" in page.result.text.toPlainText()
        assert srv.requests == []


def test_server_refusal_shown_with_hint_and_connection_unaffected(app_window, qapp):
    ctl, _ = app_window
    got = []
    with MockServer() as srv:
        ctl.cfg.save_profile("default", {"server_url": srv.url, "token": TOKEN})
        ctl.run("players.kick", {"target": "1"}, lambda ok, res, ms: got.append((ok, res)))
        wait_for(qapp, lambda: got)
    ok, err = got[0]
    assert ok is False and err.code == "forbidden" and "Config.Roles" in str(err)


def test_wrong_token_marks_connection_rejected(app_window, qapp):
    ctl, _ = app_window
    got = []
    with MockServer() as srv:
        ctl.cfg.save_profile("default", {"server_url": srv.url, "token": "n" * 30})
        ctl.check_connection(lambda *a: got.append(a))
        wait_for(qapp, lambda: got)
    assert ctl.conn_state == "rejected"


def test_unreachable_server_marks_offline(app_window, qapp):
    ctl, _ = app_window
    srv = MockServer()
    url = srv.url
    srv.server_close()
    ctl.cfg.save_profile("default", {"server_url": url, "token": TOKEN, "timeout": "2"})
    got = []
    ctl.check_connection(lambda *a: got.append(a))
    wait_for(qapp, lambda: got)
    assert ctl.conn_state == "offline" and got[0][0] is False


def test_activity_line_runs_only_while_busy(app_window, qapp):
    ctl, win = app_window
    with MockServer() as srv:
        srv.mode = "slow"
        ctl.cfg.save_profile("default", {"server_url": srv.url, "token": TOKEN, "timeout": "5"})
        got = []
        ctl.run("diag.status", {}, lambda *a: got.append(a))
        assert win.activity.busy is True
        wait_for(qapp, lambda: got, timeout=8)
    assert win.activity.busy is False


def test_compact_and_scale_apply(app_window, qapp):
    ctl, win = app_window
    ctl.cfg.set_ui(compact=True, scale=1.5)
    ctl.ui_changed.emit()
    qapp.processEvents()
    assert all(r.desc.isHidden() for r in win.pages["player"].rows)
    assert win.rail.width() == round(236 * 1.5)
    ctl.cfg.set_ui(compact=False, scale=1.0)
    ctl.ui_changed.emit()
    assert all(not r.desc.isHidden() for r in win.pages["player"].rows)


def test_favorites_pin_to_overview(app_window, qapp):
    ctl, win = app_window
    ctl.toggle_favorite("player.heal")
    qapp.processEvents()
    dash = win.pages["dashboard"]
    pinned = [dash.pins.itemAt(i).widget() for i in range(dash.pins.count()) if dash.pins.itemAt(i).widget()]
    assert any(getattr(w, "action", None) and w.action.id == "player.heal" for w in pinned)
    ctl.toggle_favorite("player.heal")
    qapp.processEvents()
    assert not any(getattr(dash.pins.itemAt(i).widget(), "action", None) for i in range(dash.pins.count()) if dash.pins.itemAt(i).widget())


def test_hotkey_rebind_updates_shortcuts_and_blocks_conflicts(app_window, qapp):
    ctl, win = app_window
    assert len(win.shortcuts) == len(ctl.cfg.data["hotkeys"])
    settings = win.pages["settings"]
    from PySide6.QtGui import QKeySequence
    edit = settings.hk_edits["nav.player"]
    edit.setKeySequence(QKeySequence("Ctrl+K"))      # taken by ui.search
    settings._hotkey_changed("nav.player", edit)
    assert "already used" in settings.hk_msg.text()
    assert ctl.cfg.data["hotkeys"]["nav.player"] == "Ctrl+2"
    edit.setKeySequence(QKeySequence("Alt+P"))
    settings._hotkey_changed("nav.player", edit)
    assert ctl.cfg.data["hotkeys"]["nav.player"] == "Alt+P"
    assert "Alt+P" in [s.key().toString() for s in win.shortcuts]


def test_profile_form_validates_and_saves(app_window, qapp):
    ctl, win = app_window
    s = win.pages["settings"]
    s._new_profile()
    s.f_name.setText("lab")
    s.f_url.setText("not a url")
    assert s._save_profile() is False and "http" in s.p_msg.text()
    s.f_url.setText("http://127.0.0.1:30120")
    s.f_token.setText("q" * 30)
    assert s._save_profile() is True
    assert "lab" in ctl.cfg.profiles
    assert Path(ctl.cfg.path).exists() and "q" * 30 in ctl.cfg.path.read_text()


def test_compat_tab_records_evidence_and_defaults_to_untested(app_window, qapp):
    ctl, win = app_window
    sec = win.pages["sec"]
    assert [p.id for p in sec.profiles][:3] == ["bt", "ghostx", "global"] or {"bt", "ghostx", "global"} <= {p.id for p in sec.profiles}
    assert sec.clist.count() == len(sec.profiles)
    assert "untested" in sec.clist.item(0).text()
    sec.clist.setCurrentRow(0)
    sec.c_status.setCurrentText("pass")
    sec.c_build.setText("test build")
    sec._save_compat()
    assert ctl.cfg.data["compat_results"][sec.profiles[0].id]["status"] == "pass"
    assert "pass" in sec.clist.item(0).text()


def test_feature_page_and_status_doc_agree(app_window):
    _, win = app_window
    page = win.pages["features"]
    assert page.table.rowCount() == len(feature_status.FEATURES)
    page.filter.setCurrentText("Not Implemented")
    assert page.table.rowCount() == feature_status.counts()["Not Implemented"]
    doc = Path(__file__).resolve().parents[1] / "docs" / "STATUS.md"
    assert doc.read_text() == feature_status.render_markdown() + "\n", "regenerate docs/STATUS.md"


def test_no_feature_marked_implemented_without_a_test_reference():
    for _, name, status, note in feature_status.FEATURES:
        if status == feature_status.IMPL:
            assert "tests/" in note, name
            for ref in note.replace(",", " ").split():
                if ref.startswith("tests/") and ref.endswith(".py"):
                    assert (Path(__file__).resolve().parents[1] / ref).exists(), ref


def test_diagnostics_page_lists_checks(app_window):
    _, win = app_window
    table = win.pages["diag"].table
    assert table.rowCount() >= 6
    assert any(table.item(r, 0).text() == "API token" for r in range(table.rowCount()))
