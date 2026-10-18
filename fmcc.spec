# PyInstaller spec: builds dist/FiveMControlCenter.exe (one file, no console window).
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ["run.py"],
    pathex=["."],
    datas=[("compat_profiles", "compat_profiles")],
    hiddenimports=collect_submodules("app"),
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
              "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="FiveMControlCenter",
    console=False,
    upx=False,
)
