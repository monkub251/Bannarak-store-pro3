@echo off
REM Reproducible Windows build. Needs Python 3.10+ on PATH. Output: dist\FiveMControlCenter.exe
setlocal
cd /d "%~dp0"
if not exist .venv ( python -m venv .venv || goto :fail )
call .venv\Scripts\activate.bat || goto :fail
python -m pip install --upgrade pip || goto :fail
pip install -r requirements.txt -r requirements-dev.txt || goto :fail
set QT_QPA_PLATFORM=offscreen
python -m pytest || goto :fail
pyinstaller fmcc.spec --noconfirm --clean || goto :fail
echo.
echo Built dist\FiveMControlCenter.exe
exit /b 0
:fail
echo.
echo Build failed. Read the message above.
exit /b 1
