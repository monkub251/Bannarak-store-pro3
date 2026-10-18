from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMainWindow, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from . import pages
from .controller import Controller
from .icons import icon
from .nav import NAV
from .theme import build_qss
from .widgets import ActivityLine, Toast


class MainWindow(QMainWindow):
    def __init__(self, ctl: Controller):
        super().__init__()
        self.ctl = ctl
        self.setWindowTitle("FIVE M Control Center")
        self.setMinimumSize(1060, 680)
        self.resize(1280, 800)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.activity = ActivityLine()
        outer.addWidget(self.activity)
        body = QHBoxLayout()
        body.setSpacing(0)
        outer.addLayout(body, 1)

        self.rail = QWidget()
        self.rail.setObjectName("rail")
        rl = QVBoxLayout(self.rail)
        rl.setContentsMargins(14, 20, 14, 14)
        rl.setSpacing(2)
        brand = QLabel("Control Center")
        brand.setObjectName("brand")
        sub = QLabel("for FiveM servers")
        sub.setObjectName("small")
        rl.addWidget(brand)
        rl.addWidget(sub)
        rl.addSpacing(10)

        self.stack = QStackedWidget()
        self._icon_names: dict[str, str] = {}
        self.buttons: dict[str, QPushButton] = {}
        self.index: dict[str, int] = {}
        self.pages: dict[str, QWidget] = {}
        for group, items in NAV:
            if group:
                g = QLabel(group)
                g.setObjectName("group")
                rl.addWidget(g)
            for key, title, icon_name in items:
                btn = QPushButton(title)
                btn.setObjectName("nav")
                btn.setProperty("active", False)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _=False, k=key: self.show_page(k))
                rl.addWidget(btn)
                self.buttons[key] = btn
                self._icon_names[key] = icon_name
                page = self._make_page(key)
                self.pages[key] = page
                self.index[key] = self.stack.addWidget(page)
        rl.addStretch(1)
        self.status_dot = QLabel("")
        self.status_text = QLabel("")
        self.status_text.setObjectName("small")
        self.status_text.setWordWrap(True)
        rl.addWidget(self.status_dot)
        rl.addWidget(self.status_text)
        body.addWidget(self.rail)
        body.addWidget(self.stack, 1)

        self.toast = Toast(root)
        ctl.toast.connect(self._toast)
        ctl.busy_changed.connect(self.activity.set_busy)
        ctl.conn_changed.connect(self._conn)
        ctl.ui_changed.connect(self.apply_ui)
        ctl.hotkeys_changed.connect(self.bind_hotkeys)

        self.shortcuts: list[QShortcut] = []
        self.current = "dashboard"
        self.apply_ui()
        self.bind_hotkeys()
        self._conn(ctl.conn_state, ctl.conn_detail)
        self.show_page("dashboard", animate=False)

    def _make_page(self, key: str) -> QWidget:
        ctl = self.ctl
        return {
            "dashboard": lambda: pages.DashboardPage(ctl), "settings": lambda: pages.SettingsPage(ctl),
            "diag": lambda: pages.DiagnosticsPage(ctl), "sec": lambda: pages.SecurityPage(ctl),
            "access": lambda: pages.AccessPage(ctl), "features": lambda: pages.FeaturesPage(ctl),
            "logs": lambda: pages.LogsPage(ctl),
        }.get(key, lambda: pages.ActionPage(ctl, key))()

    # ------------------------------------------------------------------ appearance
    def apply_ui(self) -> None:
        ui = self.ctl.cfg.data["ui"]
        QApplication.instance().setStyleSheet(build_qss(ui["scale"], ui["compact"]))
        self.rail.setFixedWidth(round(236 * ui["scale"]))
        for key, btn in self.buttons.items():
            btn.setIcon(icon(self._icon_names[key], "#f4f4f5" if key == self.current else "#8f8f98", round(18 * ui["scale"])))

    def _conn(self, state: str, detail: str) -> None:
        self.status_dot.setText(f'<span style="color:{pages.STATE_COLORS[state]}">●</span>  {pages.STATE_TEXT[state]}')
        name, _ = self.ctl.cfg.active()
        self.status_text.setText(f"Profile: {name}")
        self.status_text.setToolTip(detail)

    def _toast(self, text: str, kind: str) -> None:
        if self.ctl.cfg.data["ui"]["notifications"]:
            self.toast.notify(text, kind, self.ctl.cfg.data["ui"]["animations"])

    # ------------------------------------------------------------------ navigation
    def show_page(self, key: str, animate: bool = True) -> None:
        if key not in self.index:
            return
        prev = self.current
        self.current = key
        for k, b in self.buttons.items():
            b.setProperty("active", k == key)
            b.style().unpolish(b)
            b.style().polish(b)
            b.setIcon(icon(self._icon_names[k], "#f4f4f5" if k == key else "#8f8f98", round(18 * self.ctl.cfg.data["ui"]["scale"])))
        page = self.pages[key]
        self.stack.setCurrentIndex(self.index[key])
        if animate and prev != key and self.ctl.cfg.data["ui"]["animations"]:
            effect = QGraphicsOpacityEffect(page)
            page.setGraphicsEffect(effect)
            self._anim = QPropertyAnimation(effect, b"opacity", self)
            self._anim.setDuration(140)
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.finished.connect(lambda p=page: p.setGraphicsEffect(None))
            self._anim.start()

    def bind_hotkeys(self) -> None:
        for s in self.shortcuts:
            s.setEnabled(False)
            s.deleteLater()
        self.shortcuts = []
        for action, seq in self.ctl.cfg.data["hotkeys"].items():
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ShortcutContext.WindowShortcut)
            if action.startswith("nav."):
                sc.activated.connect(lambda k=action.removeprefix("nav."): self.show_page(k))
            elif action == "ui.search":
                sc.activated.connect(self._focus_search)
            elif action == "ui.compact":
                sc.activated.connect(self._toggle_compact)
            elif action == "ui.refresh":
                sc.activated.connect(lambda: self.ctl.check_connection())
            self.shortcuts.append(sc)

    def _focus_search(self) -> None:
        edit = getattr(self.pages[self.current], "search_edit", None)
        if edit is None:
            for child in self.pages[self.current].findChildren(pages.QLineEdit):
                if child.placeholderText() == "Search actions" and child.isVisible():
                    edit = child
                    break
        if edit is not None:
            edit.setFocus()
            edit.selectAll()

    def _toggle_compact(self) -> None:
        ui = self.ctl.cfg.data["ui"]
        self.ctl.cfg.set_ui(compact=not ui["compact"])
        self.ctl.cfg.save()
        self.ctl.ui_changed.emit()
