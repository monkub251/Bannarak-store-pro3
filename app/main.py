"""Entry point. `python -m app.main` or the packaged FiveMControlCenter.exe."""
import logging
import sys

from PySide6.QtWidgets import QApplication

from .core import logging_setup
from .core.audit import AuditLog
from .core.config import ConfigManager
from .ui.controller import Controller
from .ui.main_window import MainWindow


def build(app: QApplication | None = None, config_path=None):
    cfg = ConfigManager(config_path)
    warnings = cfg.load()
    ring = logging_setup.setup(cfg.dir / "logs")
    if cfg.path.exists():
        cfg.backup("startup")
    audit = AuditLog(cfg.dir / "audit.jsonl")
    ctl = Controller(cfg, warnings, audit, ring)
    log = logging.getLogger("fmcc")
    log.info("Control Center started; config %s", cfg.path)
    for w in warnings:
        log.warning("config: %s", w)
    return ctl, MainWindow(ctl)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("FIVE M Control Center")
    ctl, window = build(app)
    window.show()
    if "--smoke" in sys.argv:  # build the window and exit; used by CI
        return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
