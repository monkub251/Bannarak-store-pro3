"""All pages. Server-backed pages are generated from the action registry."""
from __future__ import annotations

import logging
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFormLayout, QFrame, QHBoxLayout, QHeaderView,
                               QKeySequenceEdit, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QPlainTextEdit, QPushButton, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
                               QTabWidget, QVBoxLayout, QWidget)

from ..core import compat, diagnostics, feature_status, process_audit
from ..core import hotkeys as hk
from ..core.config import COMPAT_STATUSES
from ..core.paths import bundle_dir
from ..core.registry import ACTION_BY_ID, CATEGORY_BY_KEY, actions_for
from .nav import PAGE_TITLES
from .theme import PALETTE
from .widgets import ActionRow, ResultPanel

log = logging.getLogger("fmcc.ui")
STATE_COLORS = {"connected": "#f4f4f5", "checking": "#8f8f98", "unknown": "#5d5d65", "offline": "#ef6b60", "rejected": "#ef6b60"}
STATE_TEXT = {"connected": "Connected", "checking": "Checking", "unknown": "Not checked", "offline": "Unreachable", "rejected": "Token rejected"}


def header(title: str, subtitle: str = "") -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    t = QLabel(title)
    t.setObjectName("title")
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("subtitle")
        s.setWordWrap(True)
        lay.addWidget(s)
    return w


def page_layout(widget: QWidget, margins=(32, 28, 32, 20)) -> QVBoxLayout:
    lay = QVBoxLayout(widget)
    lay.setContentsMargins(*margins)
    lay.setSpacing(16)
    return lay


class WrapTable(QTableWidget):
    """Table whose rows re-fit their wrapped text whenever the width changes."""

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self.resizeRowsToContents)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self.resizeRowsToContents)


def make_table(headers: list[str], widths: list[int] | None = None) -> QTableWidget:
    t = WrapTable(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setShowGrid(False)
    t.setWordWrap(True)
    t.horizontalHeader().setStretchLastSection(True)
    t.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    for i, w in enumerate(widths or []):
        t.setColumnWidth(i, w)
    return t


def fill_table(t: QTableWidget, rows: list[list[str]], colors: dict[int, str] | None = None) -> None:
    t.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            item = QTableWidgetItem(text)
            t.setItem(r, c, item)
    t.resizeRowsToContents()


def message(label: QLabel, text: str, error: bool = False) -> None:
    label.setObjectName("error" if error else "muted")
    label.style().unpolish(label)
    label.style().polish(label)
    label.setText(text)


# --------------------------------------------------------------------------- generic action page
class ActionPage(QWidget):
    def __init__(self, ctl, key: str, with_header: bool = True):
        super().__init__()
        self.ctl, self.key = ctl, key
        cat = CATEGORY_BY_KEY[key]
        lay = page_layout(self, (32, 28, 32, 20) if with_header else (0, 16, 0, 0))
        top = QHBoxLayout()
        if with_header:
            top.addWidget(header(cat.title, cat.blurb), 1)
        else:
            top.addStretch(1)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search actions")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(240)
        self.search_edit.textChanged.connect(self._filter)
        top.addWidget(self.search_edit, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top)

        self.rows: list[ActionRow] = []
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 0, 8, 0)
        v.setSpacing(0)
        compact = ctl.cfg.data["ui"]["compact"]
        favs = ctl.cfg.data["favorites"]
        for action in actions_for(key):
            row = ActionRow(action, action.id in favs, compact)
            row.run_requested.connect(self._run)
            row.favorite_toggled.connect(ctl.toggle_favorite)
            self.rows.append(row)
            v.addWidget(row)
        self.empty = QLabel("No action matches your search.")
        self.empty.setObjectName("muted")
        self.empty.hide()
        v.addWidget(self.empty)
        v.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        self.result = ResultPanel()
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(scroll)
        split.addWidget(self.result)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        split.setChildrenCollapsible(False)
        lay.addWidget(split, 1)
        ctl.favorites_changed.connect(self._sync_favorites)
        ctl.ui_changed.connect(self._sync_compact)

    def _filter(self, text: str) -> None:
        shown = 0
        for row in self.rows:
            visible = row.matches(text)
            row.setVisible(visible)
            shown += visible
        self.empty.setVisible(shown == 0)

    def _sync_favorites(self) -> None:
        favs = self.ctl.cfg.data["favorites"]
        for row in self.rows:
            row.set_favorite(row.action.id in favs)

    def _sync_compact(self) -> None:
        compact = self.ctl.cfg.data["ui"]["compact"]
        for row in self.rows:
            row.set_compact(compact)

    def _run(self, action_id: str, raw: dict) -> None:
        title = ACTION_BY_ID[action_id].title
        self.ctl.run(action_id, raw, lambda ok, res, ms: self.result.show_result(title, ok, res, ms))


# --------------------------------------------------------------------------- overview
class DashboardPage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        lay = page_layout(self)
        lay.addWidget(header("Overview", "Your server connection, pinned actions and recent activity."))
        cols = QHBoxLayout()
        cols.setSpacing(28)
        lay.addLayout(cols, 1)

        left = QVBoxLayout()
        cap = QLabel("Pinned actions")
        cap.setObjectName("rowtitle")
        left.addWidget(cap)
        self.pins = QVBoxLayout()
        self.pins.setSpacing(0)
        pin_holder = QWidget()
        pin_holder.setLayout(self.pins)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(pin_holder)
        left.addWidget(scroll, 1)
        self.result = ResultPanel()
        left.addWidget(self.result)
        cols.addLayout(left, 3)

        right = QVBoxLayout()
        right.setSpacing(14)
        conn = QFrame()
        conn.setObjectName("panel")
        cl = QVBoxLayout(conn)
        cl.setContentsMargins(16, 14, 16, 14)
        row = QHBoxLayout()
        self.dot = QLabel("●")
        self.state = QLabel("")
        self.state.setObjectName("rowtitle")
        row.addWidget(self.dot)
        row.addWidget(self.state, 1)
        cl.addLayout(row)
        self.detail = QLabel("")
        self.detail.setObjectName("muted")
        self.detail.setWordWrap(True)
        cl.addWidget(self.detail)
        self.profile = QLabel("")
        self.profile.setObjectName("small")
        self.profile.setWordWrap(True)
        cl.addWidget(self.profile)
        self.check = QPushButton("Check connection")
        self.check.clicked.connect(lambda: ctl.check_connection(self._checked))
        cl.addWidget(self.check)
        right.addWidget(conn)

        right.addWidget(self._caption("Feature status"))
        self.counts = QLabel("")
        self.counts.setObjectName("muted")
        self.counts.setWordWrap(True)
        right.addWidget(self.counts)
        right.addWidget(self._caption("Recent activity"))
        self.recent = QLabel("")
        self.recent.setObjectName("muted")
        self.recent.setWordWrap(True)
        right.addWidget(self.recent)
        right.addStretch(1)
        cols.addLayout(right, 2)

        ctl.conn_changed.connect(self._conn)
        ctl.favorites_changed.connect(self.refresh)
        ctl.config_reloaded.connect(self.refresh)
        self.refresh()
        self._conn(ctl.conn_state, ctl.conn_detail)

    @staticmethod
    def _caption(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("rowtitle")
        return lbl

    def _conn(self, state: str, detail: str) -> None:
        self.dot.setStyleSheet(f"color:{STATE_COLORS[state]};")
        self.state.setText(STATE_TEXT[state])
        self.detail.setText(detail)
        name, prof = self.ctl.cfg.active()
        self.profile.setText(f'Profile "{name}" at {prof["server_url"]}/{prof["resource"]}')

    def _checked(self, ok, res, ms) -> None:
        if ok:
            self.result.show_result("Server status", True, res, ms)
        else:
            self.result.show_result("Connection check", False, res, ms)

    def refresh(self) -> None:
        while self.pins.count():
            widget = self.pins.takeAt(0).widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        favs = [f for f in self.ctl.cfg.data["favorites"] if f in ACTION_BY_ID]
        compact = self.ctl.cfg.data["ui"]["compact"]
        if not favs:
            empty = QLabel("Star an action on any page to pin it here for one-click access.")
            empty.setObjectName("muted")
            empty.setWordWrap(True)
            self.pins.addWidget(empty)
        for fid in favs:
            row = ActionRow(ACTION_BY_ID[fid], True, compact)
            row.run_requested.connect(lambda aid, raw: self.ctl.run(
                aid, raw, lambda ok, res, ms, t=ACTION_BY_ID[aid].title: self.result.show_result(t, ok, res, ms)))
            row.favorite_toggled.connect(self.ctl.toggle_favorite)
            self.pins.addWidget(row)
        self.pins.addStretch(1)
        c = feature_status.counts()
        self.counts.setText("\n".join(f"{s}: {c[s]}" for s in feature_status.STATUSES if c[s]))
        entries = self.ctl.audit.tail(6)
        self.recent.setText("\n".join(f'{e["time"][11:]}  {e["action"]}  {"done" if e["ok"] else "failed"}' for e in entries)
                            or "Nothing sent from this PC yet.")


# --------------------------------------------------------------------------- interface / settings
class SettingsPage(QWidget):
    SCALES = [("80%", 0.8), ("90%", 0.9), ("100%", 1.0), ("110%", 1.1), ("125%", 1.25), ("150%", 1.5)]

    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        lay = page_layout(self)
        lay.addWidget(header("Interface", "Connection profiles, appearance, hotkeys and backups."))
        tabs = QTabWidget()
        tabs.addTab(self._profiles_tab(), "Profiles")
        tabs.addTab(self._appearance_tab(), "Appearance")
        tabs.addTab(self._hotkeys_tab(), "Hotkeys")
        tabs.addTab(self._backups_tab(), "Backups")
        lay.addWidget(tabs, 1)
        ctl.config_reloaded.connect(self._reload_all)

    def _reload_all(self) -> None:
        self._fill_profiles()
        self._sync_appearance()
        self._fill_hotkeys()
        self._fill_backups()

    # ---- profiles
    def _profiles_tab(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 16, 0, 0)
        h.setSpacing(24)
        left = QVBoxLayout()
        self.plist = QListWidget()
        self.plist.setFixedWidth(220)
        self.plist.currentItemChanged.connect(self._load_profile)
        left.addWidget(self.plist, 1)
        new = QPushButton("New profile")
        new.clicked.connect(self._new_profile)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.clicked.connect(self._delete_profile)
        r = QHBoxLayout()
        r.addWidget(new)
        r.addWidget(self.delete_btn)
        left.addLayout(r)
        h.addLayout(left)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        self.f_name, self.f_url, self.f_res = QLineEdit(), QLineEdit(), QLineEdit()
        self.f_token, self.f_timeout = QLineEdit(), QLineEdit()
        self.f_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_url.setPlaceholderText("http://127.0.0.1:30120")
        self.f_token.setPlaceholderText("From Config.Tokens in the server's config.lua")
        self.show_token = QCheckBox("Show token")
        self.show_token.toggled.connect(lambda on: self.f_token.setEchoMode(QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        self.f_tls = QCheckBox("Verify TLS certificates (https only)")
        self.f_name.setToolTip("To rename a profile, create a new one and delete the old one.")
        form.addRow("Name", self.f_name)
        form.addRow("Server address", self.f_url)
        form.addRow("Resource name", self.f_res)
        form.addRow("API token", self.f_token)
        form.addRow("", self.show_token)
        form.addRow("Timeout (seconds)", self.f_timeout)
        form.addRow("", self.f_tls)
        self.p_msg = QLabel("")
        self.p_msg.setObjectName("muted")
        self.p_msg.setWordWrap(True)
        form.addRow("", self.p_msg)
        btns = QHBoxLayout()
        save = QPushButton("Save profile")
        save.setObjectName("primary")
        save.clicked.connect(self._save_profile)
        use = QPushButton("Use this profile")
        use.clicked.connect(self._use_profile)
        test = QPushButton("Save and test connection")
        test.clicked.connect(self._test_profile)
        for b in (save, use, test):
            btns.addWidget(b)
        btns.addStretch(1)
        form.addRow("", btns)
        fw = QWidget()
        fw.setLayout(form)
        h.addWidget(fw, 1)
        self._fill_profiles()
        return w

    def _fill_profiles(self) -> None:
        cfg = self.ctl.cfg
        self.plist.blockSignals(True)
        self.plist.clear()
        active = cfg.data["active_profile"]
        for name in cfg.profiles:
            item = QListWidgetItem(f"{name}  (in use)" if name == active else name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.plist.addItem(item)
            if name == active:
                self.plist.setCurrentItem(item)
        self.plist.blockSignals(False)
        self._load_profile(self.plist.currentItem())

    def _selected(self) -> str | None:
        item = self.plist.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _load_profile(self, item, _prev=None) -> None:
        if item is None:
            return
        p = self.ctl.cfg.profiles[item.data(Qt.ItemDataRole.UserRole)]
        self.f_name.setText(item.data(Qt.ItemDataRole.UserRole))
        self.f_url.setText(p["server_url"])
        self.f_res.setText(p["resource"])
        self.f_token.setText(p["token"])
        self.f_timeout.setText(f'{p["timeout"]:g}')
        self.f_tls.setChecked(p["verify_tls"])
        message(self.p_msg, "")

    def _new_profile(self) -> None:
        self.plist.clearSelection()
        self.plist.setCurrentItem(None)
        for f, t in ((self.f_name, ""), (self.f_url, "http://127.0.0.1:30120"), (self.f_res, "fmcc_control"), (self.f_token, ""), (self.f_timeout, "6")):
            f.setText(t)
        self.f_tls.setChecked(True)
        self.f_name.setFocus()
        message(self.p_msg, "Fill in the fields, then choose Save profile.")

    def _save_profile(self) -> bool:
        try:
            name = self.f_name.text().strip()
            self.ctl.cfg.save_profile(name, {
                "server_url": self.f_url.text(), "resource": self.f_res.text().strip(), "token": self.f_token.text(),
                "timeout": self.f_timeout.text().strip(), "verify_tls": self.f_tls.isChecked()})
            self.ctl.cfg.save()
        except ValueError as exc:
            message(self.p_msg, str(exc), True)
            return False
        self._fill_profiles()
        for i in range(self.plist.count()):
            if self.plist.item(i).data(Qt.ItemDataRole.UserRole) == name:
                self.plist.setCurrentRow(i)
        message(self.p_msg, f'Saved "{name}".')
        if name == self.ctl.cfg.data["active_profile"]:
            self.ctl.conn_changed.emit(self.ctl.conn_state, self.ctl.conn_detail)
        return True

    def _use_profile(self) -> None:
        if not self._save_profile():
            return
        name = self.f_name.text().strip()
        self.ctl.cfg.set_active(name)
        self.ctl.cfg.save()
        self._fill_profiles()
        self.ctl.conn_changed.emit("unknown", f'Switched to "{name}". Not checked yet.')
        self.ctl.conn_state, self.ctl.conn_detail = "unknown", f'Switched to "{name}". Not checked yet.'
        message(self.p_msg, f'"{name}" is now in use.')

    def _delete_profile(self) -> None:
        name = self._selected()
        if not name:
            return
        try:
            self.ctl.cfg.delete_profile(name)
            self.ctl.cfg.save()
        except ValueError as exc:
            message(self.p_msg, str(exc), True)
            return
        self._fill_profiles()
        message(self.p_msg, f'Deleted "{name}".')

    def _test_profile(self) -> None:
        if not self._save_profile():
            return
        name = self.f_name.text().strip()
        message(self.p_msg, "Contacting the server…")

        def done(ok, res, ms):
            message(self.p_msg, f"Connected. The server answered in {ms} ms." if ok else str(res), not ok)
        self.ctl.check_connection(done, self.ctl.cfg.profiles[name])

    # ---- appearance
    def _appearance_tab(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setContentsMargins(0, 16, 0, 0)
        f.setVerticalSpacing(12)
        f.setHorizontalSpacing(16)
        self.scale = QComboBox()
        for text, _ in self.SCALES:
            self.scale.addItem(text)
        self.compact = QCheckBox("Compact mode: tighter rows, no descriptions")
        self.notify = QCheckBox("Show notifications")
        self.anim = QCheckBox("Animate page changes")
        f.addRow("Interface size", self.scale)
        f.addRow("", self.compact)
        f.addRow("", self.notify)
        f.addRow("", self.anim)
        self.scale.currentIndexChanged.connect(self._apply_appearance)
        for c in (self.compact, self.notify, self.anim):
            c.toggled.connect(self._apply_appearance)
        self._sync_appearance()
        return w

    def _sync_appearance(self) -> None:
        ui = self.ctl.cfg.data["ui"]
        for c in (self.scale, self.compact, self.notify, self.anim):
            c.blockSignals(True)
        self.scale.setCurrentIndex(min(range(len(self.SCALES)), key=lambda i: abs(self.SCALES[i][1] - ui["scale"])))
        self.compact.setChecked(ui["compact"])
        self.notify.setChecked(ui["notifications"])
        self.anim.setChecked(ui["animations"])
        for c in (self.scale, self.compact, self.notify, self.anim):
            c.blockSignals(False)

    def _apply_appearance(self) -> None:
        self.ctl.cfg.set_ui(scale=self.SCALES[self.scale.currentIndex()][1], compact=self.compact.isChecked(),
                            notifications=self.notify.isChecked(), animations=self.anim.isChecked())
        self.ctl.cfg.save()
        self.ctl.ui_changed.emit()

    # ---- hotkeys
    def _hotkeys_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 16, 0, 0)
        note = QLabel("Hotkeys work while this window has focus. Click a box and press the new combination.")
        note.setObjectName("muted")
        lay.addWidget(note)
        self.hk_msg = QLabel("")
        self.hk_msg.setObjectName("muted")
        lay.addWidget(self.hk_msg)
        inner = QWidget()
        self.hk_form = QFormLayout(inner)
        self.hk_form.setVerticalSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)
        reset = QPushButton("Restore default hotkeys")
        reset.clicked.connect(self._reset_hotkeys)
        lay.addWidget(reset, 0, Qt.AlignmentFlag.AlignLeft)
        self.hk_edits: dict[str, QKeySequenceEdit] = {}
        self._fill_hotkeys()
        return w

    def _hotkey_label(self, action: str) -> str:
        if action in hk.HOTKEY_LABELS:
            return hk.HOTKEY_LABELS[action]
        return "Go to " + PAGE_TITLES.get(action.removeprefix("nav."), action)

    def _fill_hotkeys(self) -> None:
        while self.hk_form.rowCount():
            self.hk_form.removeRow(0)
        self.hk_edits.clear()
        for action, seq in self.ctl.cfg.data["hotkeys"].items():
            edit = QKeySequenceEdit(QKeySequence(seq))
            edit.setMaximumSequenceLength(1)
            edit.setFixedWidth(200)
            edit.editingFinished.connect(lambda a=action, e=edit: self._hotkey_changed(a, e))
            self.hk_edits[action] = edit
            self.hk_form.addRow(self._hotkey_label(action), edit)

    def _hotkey_changed(self, action: str, edit: QKeySequenceEdit) -> None:
        text = edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        try:
            norm = self.ctl.cfg.set_hotkey(action, text)
            self.ctl.cfg.save()
            message(self.hk_msg, f"{self._hotkey_label(action)}: {norm}")
            self.ctl.hotkeys_changed.emit()
        except ValueError as exc:
            message(self.hk_msg, str(exc), True)
            edit.setKeySequence(QKeySequence(self.ctl.cfg.data["hotkeys"][action]))

    def _reset_hotkeys(self) -> None:
        self.ctl.cfg.data["hotkeys"] = dict(hk.DEFAULT_HOTKEYS)
        self.ctl.cfg.save()
        self._fill_hotkeys()
        self.ctl.hotkeys_changed.emit()
        message(self.hk_msg, "Default hotkeys restored.")

    # ---- backups
    def _backups_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 16, 0, 0)
        info = QLabel("Backups keep your profiles (including tokens), hotkeys and recorded compatibility results. The 10 newest are kept.")
        info.setObjectName("muted")
        info.setWordWrap(True)
        lay.addWidget(info)
        self.blist = QListWidget()
        lay.addWidget(self.blist, 1)
        self.b_msg = QLabel("")
        self.b_msg.setObjectName("muted")
        lay.addWidget(self.b_msg)
        row = QHBoxLayout()
        make = QPushButton("Back up now")
        make.setObjectName("primary")
        make.clicked.connect(self._backup_now)
        restore = QPushButton("Restore selected")
        restore.clicked.connect(self._restore)
        folder = QPushButton("Open folder")
        folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.ctl.cfg.dir))))
        for b in (make, restore, folder):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self._fill_backups()
        return w

    def _fill_backups(self) -> None:
        self.blist.clear()
        for p in self.ctl.cfg.list_backups():
            item = QListWidgetItem(p.name)
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.blist.addItem(item)

    def _backup_now(self) -> None:
        self.ctl.cfg.save()
        path = self.ctl.cfg.backup("manual")
        self._fill_backups()
        message(self.b_msg, f"Saved {path.name}" if path else "Nothing to back up yet.")

    def _restore(self) -> None:
        item = self.blist.currentItem()
        if not item:
            message(self.b_msg, "Select a backup first.", True)
            return
        if QMessageBox.question(self, "Restore backup", "Replace the current settings with this backup? The current settings are backed up first.") != QMessageBox.StandardButton.Yes:
            return
        try:
            warnings = self.ctl.cfg.restore(Path(item.data(Qt.ItemDataRole.UserRole)))
        except (ValueError, OSError) as exc:
            message(self.b_msg, f"Could not restore: {exc}", True)
            return
        self.ctl.load_warnings = warnings
        self.ctl.config_reloaded.emit()
        self.ctl.ui_changed.emit()
        self.ctl.hotkeys_changed.emit()
        message(self.b_msg, "Backup restored.")


# --------------------------------------------------------------------------- diagnostics
class DiagnosticsPage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        lay = page_layout(self)
        lay.addWidget(header("Diagnostics", "Check this PC first, then the server."))
        tabs = QTabWidget()
        local = QWidget()
        ll = QVBoxLayout(local)
        ll.setContentsMargins(0, 16, 0, 0)
        run = QPushButton("Run checks")
        run.setObjectName("primary")
        run.clicked.connect(self.run_checks)
        ll.addWidget(run, 0, Qt.AlignmentFlag.AlignLeft)
        self.table = make_table(["Check", "Result", "Details"], [220, 100])
        ll.addWidget(self.table, 1)
        tabs.addTab(local, "This PC")
        tabs.addTab(ActionPage(ctl, "diag", with_header=False), "Server")
        lay.addWidget(tabs, 1)
        self.run_checks()

    def run_checks(self) -> None:
        results = diagnostics.local_checks(self.ctl.cfg, self.ctl.load_warnings)
        words = {"ok": "OK", "warn": "Warning", "fail": "Problem"}
        fill_table(self.table, [[r.name, words[r.status], r.detail] for r in results])
        for i, r in enumerate(results):
            color = {"ok": PALETTE["text"], "warn": PALETTE["muted"], "fail": PALETTE["danger"]}[r.status]
            from PySide6.QtGui import QColor
            self.table.item(i, 1).setForeground(QColor(color))


# --------------------------------------------------------------------------- security
class SecurityPage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        lay = page_layout(self)
        lay.addWidget(header("Security", "Defensive checks for servers and PCs you are authorized to test. Nothing here bypasses or hides from an anti-cheat."))
        tabs = QTabWidget()
        tabs.addTab(ActionPage(ctl, "sec", with_header=False), "Server monitoring")
        tabs.addTab(self._compat_tab(), "Compatibility")
        tabs.addTab(self._process_tab(), "Process audit")
        lay.addWidget(tabs, 1)

    # ---- compatibility
    def _compat_tab(self) -> QWidget:
        self.profiles = compat.load_profiles(bundle_dir() / "compat_profiles")
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 16, 0, 0)
        h.setSpacing(24)
        self.clist = QListWidget()
        self.clist.setFixedWidth(220)
        h.addWidget(self.clist)
        right = QVBoxLayout()
        self.c_summary = QLabel("")
        self.c_summary.setObjectName("muted")
        self.c_summary.setWordWrap(True)
        right.addWidget(self.c_summary)
        self.c_checks = QPlainTextEdit()
        self.c_checks.setReadOnly(True)
        right.addWidget(self.c_checks, 1)
        form = QHBoxLayout()
        self.c_status = QComboBox()
        self.c_status.addItems(COMPAT_STATUSES)
        self.c_build = QLineEdit()
        self.c_build.setPlaceholderText("Anti-cheat version and server build tested")
        self.c_notes = QLineEdit()
        self.c_notes.setPlaceholderText("What you observed")
        save = QPushButton("Record result")
        save.setObjectName("primary")
        save.clicked.connect(self._save_compat)
        form.addWidget(self.c_status)
        form.addWidget(self.c_build, 1)
        form.addWidget(self.c_notes, 2)
        form.addWidget(save)
        right.addLayout(form)
        self.c_msg = QLabel("")
        self.c_msg.setObjectName("muted")
        right.addWidget(self.c_msg)
        h.addLayout(right, 1)
        self.clist.currentRowChanged.connect(self._show_compat)
        self._fill_compat()
        return w

    def _fill_compat(self) -> None:
        row = max(self.clist.currentRow(), 0)
        self.clist.blockSignals(True)
        self.clist.clear()
        results = self.ctl.cfg.data["compat_results"]
        for p in self.profiles:
            status = results.get(p.id, {}).get("status", "untested")
            self.clist.addItem(f"{p.name}   {status}")
        self.clist.blockSignals(False)
        self.clist.setCurrentRow(min(row, self.clist.count() - 1))
        self._show_compat(self.clist.currentRow())

    def _show_compat(self, row: int) -> None:
        if row < 0 or row >= len(self.profiles):
            return
        p = self.profiles[row]
        self.c_summary.setText(p.summary)
        self.c_checks.setPlainText("\n\n".join(f"{c.title}\n{c.how}" for c in p.checks))
        res = self.ctl.cfg.data["compat_results"].get(p.id)
        if res:
            self.c_status.setCurrentText(res["status"])
            self.c_build.setText(res["build"])
            self.c_notes.setText(res["notes"])
            message(self.c_msg, f'Recorded {res["date"]}.')
        else:
            self.c_status.setCurrentText("untested")
            self.c_build.clear()
            self.c_notes.clear()
            message(self.c_msg, "No result recorded. Compatibility is unverified until you test it.")

    def _save_compat(self) -> None:
        row = self.clist.currentRow()
        if row < 0:
            return
        p = self.profiles[row]
        try:
            self.ctl.cfg.set_compat_result(p.id, self.c_status.currentText(), self.c_build.text(), self.c_notes.text())
            self.ctl.cfg.save()
        except ValueError as exc:
            message(self.c_msg, str(exc), True)
            return
        self._fill_compat()
        message(self.c_msg, f"Recorded result for {p.name}.")

    # ---- process audit
    def _process_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 16, 0, 0)
        info = QLabel("Read-only inspection of this PC. List process names to watch for, one per line (no list is built in). "
                      "Save a loaded-module baseline of the game while it runs clean, then compare later to see added or removed DLLs.")
        info.setObjectName("muted")
        info.setWordWrap(True)
        lay.addWidget(info)
        top = QHBoxLayout()
        self.watch = QPlainTextEdit("\n".join(self.ctl.cfg.data["process_watchlist"]))
        self.watch.setPlaceholderText("process names to watch for, one per line")
        self.watch.setFixedHeight(90)
        top.addWidget(self.watch, 1)
        col = QVBoxLayout()
        scan = QPushButton("Scan processes")
        scan.setObjectName("primary")
        scan.clicked.connect(self._scan)
        col.addWidget(scan)
        col.addStretch(1)
        top.addLayout(col)
        lay.addLayout(top)
        row = QHBoxLayout()
        self.pcombo = QComboBox()
        self.pcombo.setMinimumWidth(240)
        base = QPushButton("Save module baseline")
        base.clicked.connect(self._baseline)
        cmp_ = QPushButton("Compare with baseline")
        cmp_.clicked.connect(self._compare)
        for x in (self.pcombo, base, cmp_):
            row.addWidget(x)
        row.addStretch(1)
        lay.addLayout(row)
        self.p_out = QPlainTextEdit()
        self.p_out.setObjectName("output")
        self.p_out.setReadOnly(True)
        lay.addWidget(self.p_out, 1)
        return w

    def _scan(self) -> None:
        try:
            self.ctl.cfg.data["process_watchlist"] = self.ctl.cfg.clean_watchlist(self.watch.toPlainText().splitlines())
            self.ctl.cfg.save()
            procs = process_audit.list_processes()
            hits = process_audit.watchlist_hits(self.ctl.cfg.data["process_watchlist"], procs)
            games = process_audit.game_processes(procs)
        except process_audit.ProcessAuditError as exc:
            self.p_out.setPlainText(str(exc))
            return
        self.pcombo.clear()
        for g in games:
            self.pcombo.addItem(f'{g["name"]} (PID {g["pid"]})', (g["pid"], g["name"]))
        lines = [f"Scanned {len(procs)} processes.", ""]
        lines.append("Watchlist matches:" if hits else "No watchlist matches." if self.ctl.cfg.data["process_watchlist"] else "The watchlist is empty, so nothing was matched.")
        lines += [f'  {h["name"]} (PID {h["pid"]})' for h in hits]
        lines += ["", "Game processes:" if games else "No FiveM or GTA V process is running."]
        lines += [f'  {g["name"]} (PID {g["pid"]})' for g in games]
        self.p_out.setPlainText("\n".join(lines))

    def _baseline_path(self, name: str) -> Path:
        safe = "".join(c for c in name.lower() if c.isalnum() or c in "._-") or "process"
        return self.ctl.cfg.dir / "module_baselines" / f"{safe}.json"

    def _current(self):
        data = self.pcombo.currentData()
        if not data:
            self.p_out.setPlainText("Scan processes first and start the game so it appears in the list.")
            return None
        return data

    def _baseline(self) -> None:
        data = self._current()
        if not data:
            return
        try:
            mods = process_audit.module_snapshot(data[0])
        except process_audit.ProcessAuditError as exc:
            self.p_out.setPlainText(str(exc))
            return
        process_audit.save_baseline(self._baseline_path(data[1]), data[1], mods)
        self.p_out.setPlainText(f"Saved a baseline of {len(mods)} loaded modules for {data[1]}.")

    def _compare(self) -> None:
        data = self._current()
        if not data:
            return
        base = process_audit.load_baseline(self._baseline_path(data[1]))
        if not base:
            self.p_out.setPlainText("No baseline saved for this process yet. Save one while the game is running clean.")
            return
        try:
            now = process_audit.module_snapshot(data[0])
        except process_audit.ProcessAuditError as exc:
            self.p_out.setPlainText(str(exc))
            return
        d = process_audit.diff(base["modules"], now)
        lines = [f'Compared {len(now)} loaded modules with the baseline of {len(base["modules"])}.', ""]
        lines.append("Added since baseline:" if d["added"] else "No modules added since baseline.")
        lines += [f"  {m}" for m in d["added"]]
        lines.append("")
        lines.append("Removed since baseline:" if d["removed"] else "No modules removed since baseline.")
        lines += [f"  {m}" for m in d["removed"]]
        lines += ["", "A new module is not proof of cheating (overlays, drivers and updates add modules). Review each path."]
        self.p_out.setPlainText("\n".join(lines))


# --------------------------------------------------------------------------- access
class AccessPage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        lay = page_layout(self)
        lay.addWidget(header("Access", "Your role on the server and everything this app has sent."))
        tabs = QTabWidget()
        tabs.addTab(ActionPage(ctl, "access", with_header=False), "Server")
        local = QWidget()
        ll = QVBoxLayout(local)
        ll.setContentsMargins(0, 16, 0, 0)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        ll.addWidget(refresh, 0, Qt.AlignmentFlag.AlignLeft)
        self.table = make_table(["Time", "Profile", "Action", "Result", "Message"], [150, 110, 190, 80])
        ll.addWidget(self.table, 1)
        tabs.addTab(local, "Sent from this PC")
        lay.addWidget(tabs, 1)
        self.refresh()

    def refresh(self) -> None:
        entries = self.ctl.audit.tail(200)
        fill_table(self.table, [[e["time"], e["profile"], e["action"], "Done" if e["ok"] else "Failed", e["message"]] for e in entries])


# --------------------------------------------------------------------------- feature status
class FeaturesPage(QWidget):
    def __init__(self, ctl):
        super().__init__()
        lay = page_layout(self)
        lay.addWidget(header("Feature status", "What works, what is untested and what is not built. Nothing is marked Implemented without an automated test."))
        row = QHBoxLayout()
        self.filter = QComboBox()
        self.filter.addItems(["All statuses", *feature_status.STATUSES])
        self.filter.currentIndexChanged.connect(self._fill)
        self.summary = QLabel("")
        self.summary.setObjectName("muted")
        row.addWidget(self.filter)
        row.addWidget(self.summary, 1)
        lay.addLayout(row)
        self.table = make_table(["Area", "Feature", "Status", "Notes"], [190, 360, 150])
        lay.addWidget(self.table, 1)
        self._fill()

    def _fill(self) -> None:
        want = self.filter.currentText()
        rows = [[CATEGORY_BY_KEY[k].title if k in CATEGORY_BY_KEY else "Build", n, s, note]
                for k, n, s, note in feature_status.FEATURES if want == "All statuses" or s == want]
        fill_table(self.table, rows)
        c = feature_status.counts()
        self.summary.setText(f"{len(rows)} shown. " + ", ".join(f"{c[s]} {s.lower()}" for s in feature_status.STATUSES if c[s]))


# --------------------------------------------------------------------------- logs
class LogsPage(QWidget):
    LEVELS = ["INFO", "WARNING", "ERROR"]

    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        lay = page_layout(self)
        lay.addWidget(header("Logs", "Application log for this session. Tokens are hidden. The full log is in the data folder."))
        row = QHBoxLayout()
        self.level = QComboBox()
        self.level.addItems(["All levels", "Warnings and errors", "Errors only"])
        self.level.currentIndexChanged.connect(self.refresh)
        folder = QPushButton("Open log folder")
        folder.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.ctl.cfg.dir / "logs"))))
        row.addWidget(self.level)
        row.addStretch(1)
        row.addWidget(folder)
        lay.addLayout(row)
        self.text = QPlainTextEdit()
        self.text.setObjectName("output")
        self.text.setReadOnly(True)
        lay.addWidget(self.text, 1)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.refresh()

    def showEvent(self, e) -> None:
        self.timer.start()
        self.refresh()
        super().showEvent(e)

    def hideEvent(self, e) -> None:
        self.timer.stop()
        super().hideEvent(e)

    def refresh(self) -> None:
        allowed = {0: None, 1: {"WARNING", "ERROR", "CRITICAL"}, 2: {"ERROR", "CRITICAL"}}[self.level.currentIndex()]
        lines = [f'{time.strftime("%H:%M:%S", time.localtime(t))}  {lvl:<8} {msg}' for t, lvl, msg in self.ctl.ring.records
                 if allowed is None or lvl in allowed]
        text = "\n".join(lines) or "Nothing logged yet."
        if text != self.text.toPlainText():
            self.text.setPlainText(text)
            bar = self.text.verticalScrollBar()
            bar.setValue(bar.maximum())
