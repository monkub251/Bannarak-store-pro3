"""Reusable widgets: parameter editors, action rows, result panel, activity line, toast."""
from __future__ import annotations

import json

from PySide6.QtCore import QPropertyAnimation, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

from ..core.registry import Action, Param
from .icons import icon
from .theme import PALETTE


class ParamEditor:
    """One input for one action parameter; value() returns the raw value for registry.coerce_params."""

    def __init__(self, p: Param):
        self.param = p
        if p.kind == "bool":
            self.widget = QCheckBox("On")
            self.widget.setChecked(bool(p.default))
            self._get = self.widget.isChecked
        elif p.kind == "choice":
            self.widget = QComboBox()
            self.widget.addItems(list(p.choices))
            self._get = self.widget.currentText
        else:
            self.widget = QLineEdit()
            if p.kind in ("int", "float") and p.min is not None:
                self.widget.setPlaceholderText(f"{p.min:g} to {p.max:g}")
                self.widget.setMinimumWidth(110)
            elif p.default not in (None, ""):
                self.widget.setPlaceholderText(str(p.default))
                self.widget.setMinimumWidth(170)
            else:
                self.widget.setMinimumWidth(170)
            self.widget.setMaxLength(p.max_len if p.kind == "str" else 24)
            self._get = self.widget.text

    def value(self):
        return self._get()


class ActionRow(QFrame):
    run_requested = Signal(str, dict)
    favorite_toggled = Signal(str)

    def __init__(self, action: Action, favorite: bool = False, compact: bool = False):
        super().__init__()
        self.setObjectName("row")
        self.action = action
        self.editors = {p.name: ParamEditor(p) for p in action.params}

        root = QHBoxLayout(self)
        root.setContentsMargins(4, 8 if compact else 12, 4, 8 if compact else 12)
        root.setSpacing(10)

        self.star = QPushButton()
        self.star.setObjectName("star")
        self.star.setFixedSize(28, 28)
        self.star.setToolTip("Pin to Overview")
        self.star.clicked.connect(lambda: self.favorite_toggled.emit(action.id))
        self.set_favorite(favorite)
        root.addWidget(self.star, 0, Qt.AlignmentFlag.AlignTop)

        body = QVBoxLayout()
        body.setSpacing(2 if compact else 4)
        title = QLabel(action.title)
        title.setObjectName("rowtitle")
        body.addWidget(title)
        self.desc = QLabel(action.description)
        self.desc.setObjectName("muted")
        self.desc.setWordWrap(True)
        self.desc.setVisible(not compact)
        body.addWidget(self.desc)
        if self.editors:
            fields = QHBoxLayout()
            fields.setSpacing(12)
            fields.setContentsMargins(0, 4, 0, 0)
            for name, editor in self.editors.items():
                col = QVBoxLayout()
                col.setSpacing(3)
                label = QLabel(editor.param.title)
                label.setObjectName("small")
                col.addWidget(label)
                col.addWidget(editor.widget)
                fields.addLayout(col)
            fields.addStretch(1)
            body.addLayout(fields)
        root.addLayout(body, 1)

        self.run = QPushButton("Run…" if action.danger else "Run")
        self.run.setObjectName("danger" if action.danger else "primary")
        self.run.setMinimumWidth(78)
        self.run.clicked.connect(self._clicked)
        root.addWidget(self.run, 0, Qt.AlignmentFlag.AlignBottom)

    def set_favorite(self, on: bool) -> None:
        self.star.setIcon(icon("star", "#f4f4f5" if on else "#5d5d65", 18, filled=on))
        self.star.setToolTip("Unpin from Overview" if on else "Pin to Overview")

    def set_compact(self, compact: bool) -> None:
        self.desc.setVisible(not compact)

    def matches(self, text: str) -> bool:
        text = text.strip().lower()
        return not text or text in self.action.title.lower() or text in self.action.description.lower() or text in self.action.id

    def raw_params(self) -> dict:
        return {name: e.value() for name, e in self.editors.items()}

    def _clicked(self) -> None:
        if self.action.danger:
            box = QMessageBox(self)
            box.setWindowTitle(self.action.title)
            box.setText(f"{self.action.title}?")
            box.setInformativeText(self.action.description + "\n\nThis changes the live server.")
            box.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok)
            box.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if box.exec() != QMessageBox.StandardButton.Ok:
                return
        self.run_requested.emit(self.action.id, self.raw_params())


class ResultPanel(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(6)
        head = QHBoxLayout()
        self.title = QLabel("Results appear here")
        self.title.setObjectName("rowtitle")
        self.status = QLabel("")
        self.status.setObjectName("muted")
        head.addWidget(self.title)
        head.addStretch(1)
        head.addWidget(self.status)
        lay.addLayout(head)
        self.text = QPlainTextEdit()
        self.text.setObjectName("output")
        self.text.setReadOnly(True)
        self.text.setMinimumHeight(90)
        lay.addWidget(self.text)

    def show_result(self, title: str, ok: bool, payload, ms: int) -> None:
        self.title.setText(title)
        self.status.setText(f"Done in {ms} ms" if ok else "Failed")
        self.status.setObjectName("muted" if ok else "error")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.text.setPlainText(json.dumps(payload, indent=2, ensure_ascii=False) if ok else str(payload))


class ActivityLine(QWidget):
    """A hairline across the top of the window. A light segment travels along it while a request is in flight."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(2)
        self.busy, self._pos = False, 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        if busy:
            self.timer.start()
        else:
            self.timer.stop()
            self._pos = 0.0
            self.update()

    def _tick(self) -> None:
        self._pos = (self._pos + 0.012) % 1.3
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(PALETTE["line"]))
        if self.busy:
            w = self.width()
            seg = w * 0.28
            x = (self._pos - 0.15) * w
            grad = QLinearGradient(x, 0, x + seg, 0)
            clear, white = QColor(244, 244, 245, 0), QColor(244, 244, 245, 230)
            grad.setColorAt(0, clear)
            grad.setColorAt(0.6, white)
            grad.setColorAt(1, clear)
            p.fillRect(QRectF(x, 0, seg, self.height()), grad)


class Toast(QLabel):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setMaximumWidth(380)
        self.hide()
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.anim = QPropertyAnimation(self.effect, b"opacity", self)
        self.anim.setDuration(180)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._fade_out)
        self.anim.finished.connect(self._after_anim)
        self._hiding = False

    def notify(self, text: str, kind: str = "info", animate: bool = True) -> None:
        border = PALETTE["danger"] if kind == "error" else PALETTE["line2"]
        self.setStyleSheet(f"background:{PALETTE['surface2']};border:1px solid {border};border-radius:8px;padding:10px 14px;")
        self.setText(text)
        self.adjustSize()
        parent = self.parentWidget()
        self.move(parent.width() - self.width() - 24, parent.height() - self.height() - 24)
        self.raise_()
        self._hiding = False
        self.show()
        if animate:
            self.anim.stop()
            self.anim.setStartValue(0.0)
            self.anim.setEndValue(1.0)
            self.anim.start()
        else:
            self.effect.setOpacity(1.0)
        self.timer.start(4200)

    def _fade_out(self) -> None:
        self._hiding = True
        self.anim.stop()
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.start()

    def _after_anim(self) -> None:
        if self._hiding:
            self.hide()
