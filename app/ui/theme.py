"""Monochrome theme: black and charcoal surfaces, white type, one muted red reserved for errors."""
from string import Template

PALETTE = dict(
    bg="#09090a", rail="#0d0d0f", surface="#131315", surface2="#1a1a1d", line="#232327", line2="#303036",
    text="#f4f4f5", muted="#8f8f98", faint="#5d5d65", danger="#ef6b60", hover="#161618", sel="#1f1f23",
)
FONT_STACK = '"Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", "DejaVu Sans", sans-serif'

_QSS = Template("""
QWidget { background: transparent; color: $text; font-family: $font; font-size: ${fs}px; }
QMainWindow, QWidget#root, QDialog, QMessageBox { background: $bg; }
QWidget#rail { background: $rail; border-right: 1px solid $line; }
QLabel#brand { font-size: ${fs_brand}px; font-weight: 600; }
QLabel#title { font-size: ${fs_title}px; font-weight: 600; }
QLabel#rowtitle { font-weight: 600; }
QLabel#muted, QLabel#subtitle { color: $muted; }
QLabel#faint { color: $faint; }
QLabel#error { color: $danger; }
QLabel#group { color: $faint; font-size: ${fs_small}px; padding: ${gp}px ${gh}px 2px ${gh}px; }
QLabel#small { color: $muted; font-size: ${fs_small}px; }
QPushButton { background: $surface2; border: 1px solid $line2; border-radius: 6px; padding: ${pv}px ${ph}px; }
QPushButton:hover { border-color: $faint; }
QPushButton:pressed { background: $surface; }
QPushButton:disabled { color: $faint; border-color: $line; }
QPushButton#primary { background: $text; color: $bg; border: 1px solid $text; font-weight: 600; }
QPushButton#primary:hover { background: #d4d4d7; border-color: #d4d4d7; }
QPushButton#primary:disabled { background: $line2; color: $faint; border-color: $line2; }
QPushButton#danger { color: $danger; }
QPushButton#nav { text-align: left; border: none; border-radius: 6px; color: $muted; background: transparent; padding: ${nv}px ${ph}px; }
QPushButton#nav:hover { background: $hover; color: $text; }
QPushButton#nav[active="true"] { background: $sel; color: $text; font-weight: 600; }
QPushButton#star { border: none; background: transparent; padding: 2px; }
QLineEdit, QComboBox, QPlainTextEdit, QTextEdit, QKeySequenceEdit { background: $surface; border: 1px solid $line2; border-radius: 6px; padding: ${ev}px 8px; selection-background-color: $faint; }
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QKeySequenceEdit:focus { border-color: $muted; }
QPlainTextEdit#output { font-family: "Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace; font-size: ${fs_small}px; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: $surface2; border: 1px solid $line2; selection-background-color: $sel; outline: 0; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid $faint; border-radius: 4px; background: $surface; }
QCheckBox::indicator:checked { background: $text; border-color: $text; }
QTabWidget::pane { border: none; border-top: 1px solid $line; top: -1px; }
QTabBar::tab { padding: ${pv}px 4px; margin-right: 22px; color: $muted; border-bottom: 2px solid transparent; background: transparent; }
QTabBar::tab:selected { color: $text; border-bottom: 2px solid $text; }
QTabBar::tab:hover { color: $text; }
QTableWidget, QListWidget { background: transparent; border: none; gridline-color: $line; outline: 0; }
QListWidget { background: $surface; border: 1px solid $line; border-radius: 6px; padding: 4px; }
QListWidget::item { padding: ${ev}px 8px; border-radius: 4px; }
QListWidget::item:selected, QTableWidget::item:selected { background: $sel; color: $text; }
QTableWidget::item { padding: 4px 6px; border-bottom: 1px solid $line; }
QHeaderView::section { background: transparent; color: $muted; border: none; border-bottom: 1px solid $line; padding: 6px; }
QFrame#row { border: none; border-bottom: 1px solid $line; }
QFrame#panel { background: $surface; border: 1px solid $line; border-radius: 8px; }
QScrollArea { border: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: $line2; border-radius: 5px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: $faint; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; }
QScrollBar::handle:horizontal { background: $line2; border-radius: 5px; min-width: 32px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QSplitter::handle { background: $line; }
QToolTip { background: $surface2; color: $text; border: 1px solid $line2; padding: 4px 6px; }
""")


def build_qss(scale: float = 1.0, compact: bool = False) -> str:
    px = lambda n: max(1, round(n * scale))  # noqa: E731
    return _QSS.substitute(
        PALETTE, font=FONT_STACK, fs=px(13), fs_small=px(12), fs_title=px(24), fs_brand=px(16),
        pv=px(5 if compact else 7), ph=px(12), nv=px(6 if compact else 8), ev=px(4 if compact else 6),
        gp=px(14), gh=px(12),
    )
