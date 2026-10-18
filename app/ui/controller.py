"""Glue between the UI and the core: runs API calls off the UI thread, audits them and tracks connection state."""
from __future__ import annotations

import logging
import time
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from ..core import registry
from ..core.audit import AuditLog
from ..core.client import ApiClient, ApiError
from ..core.config import ConfigManager

log = logging.getLogger("fmcc.controller")
Done = Callable[[bool, object, int], None]


class _Job(QObject):
    done = Signal(bool, object, int)

    def __init__(self, parent, callback: Done):
        super().__init__(parent)
        self.callback = callback
        self.done.connect(self._handle)

    @Slot(bool, object, int)
    def _handle(self, ok, result, ms):
        try:
            self.callback(ok, result, ms)
        finally:
            self.deleteLater()


class _Task(QRunnable):
    def __init__(self, fn, job: _Job):
        super().__init__()
        self.fn, self.job = fn, job

    def run(self):
        t0 = time.perf_counter()
        try:
            result, ok = self.fn(), True
        except ApiError as exc:
            result, ok = exc, False
        except Exception as exc:  # never let a worker die silently
            result, ok = ApiError("error", f"Unexpected error: {exc}"), False
        self.job.done.emit(ok, result, int((time.perf_counter() - t0) * 1000))


class Controller(QObject):
    busy_changed = Signal(bool)
    conn_changed = Signal(str, str)     # state: unknown | checking | connected | rejected | offline, detail
    ui_changed = Signal()
    hotkeys_changed = Signal()
    favorites_changed = Signal()
    config_reloaded = Signal()
    toast = Signal(str, str)            # message, kind: info | error

    def __init__(self, cfg: ConfigManager, load_warnings: list[str], audit: AuditLog, ring):
        super().__init__()
        self.cfg, self.load_warnings, self.audit, self.ring = cfg, load_warnings, audit, ring
        self.conn_state, self.conn_detail = "unknown", "Not checked yet"
        self._pending = 0

    def client(self, profile: dict | None = None) -> ApiClient:
        p = profile or self.cfg.active()[1]
        return ApiClient(p["server_url"], p["resource"], p["token"], p["timeout"], p["verify_tls"])

    def _set_conn(self, state: str, detail: str) -> None:
        if (state, detail) != (self.conn_state, self.conn_detail):
            self.conn_state, self.conn_detail = state, detail
            self.conn_changed.emit(state, detail)

    def _submit(self, fn, callback: Done) -> None:
        self._pending += 1
        if self._pending == 1:
            self.busy_changed.emit(True)

        def finished(ok, result, ms):
            self._pending -= 1
            if self._pending == 0:
                self.busy_changed.emit(False)
            callback(ok, result, ms)

        job = _Job(self, finished)
        QThreadPool.globalInstance().start(_Task(fn, job))

    def run(self, action_id: str, raw_params: dict, done: Done) -> None:
        try:
            params = registry.coerce_params(action_id, raw_params)
        except ValueError as exc:
            err = ApiError("invalid", str(exc))
            self.toast.emit(str(exc), "error")
            done(False, err, 0)
            return
        client, name = self.client(), self.cfg.active()[0]

        def finished(ok, result, ms):
            self.audit.add(name, action_id, params, ok, "" if ok else result.message)
            if ok:
                self._set_conn("connected", f"{name}: answered in {ms} ms")
                log.info("%s ok (%d ms)", action_id, ms)
            else:
                log.warning("%s failed: %s", action_id, result.message)
                if result.code in ("unauthorized", "locked", "no_token"):
                    self._set_conn("rejected", result.message)
                elif result.is_network:
                    self._set_conn("offline", result.message)
                self.toast.emit(result.message, "error")
            done(ok, result, ms)

        self._submit(lambda: client.call(action_id, params), finished)

    def check_connection(self, done: Done | None = None, profile: dict | None = None) -> None:
        client = self.client(profile)
        self._set_conn("checking", "Contacting the server")

        def finished(ok, result, ms):
            if ok:
                self._set_conn("connected", f"{self.cfg.active()[0]}: answered in {ms} ms")
            elif result.code in ("unauthorized", "locked", "no_token", "forbidden"):
                self._set_conn("rejected", result.message)
            else:
                self._set_conn("offline", result.message)
            if done:
                done(ok, result, ms)

        self._submit(lambda: client.call("diag.status"), finished)

    # ---------------------------------------------------------- settings changes
    def save(self) -> None:
        self.cfg.save()

    def toggle_favorite(self, action_id: str) -> bool:
        state = self.cfg.toggle_favorite(action_id)
        self.cfg.save()
        self.favorites_changed.emit()
        return state

    def reload_config(self) -> None:
        self.load_warnings = self.cfg.load()
        self.config_reloaded.emit()
        self.ui_changed.emit()
        self.hotkeys_changed.emit()
        self.favorites_changed.emit()
