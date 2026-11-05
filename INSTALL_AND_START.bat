@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
TITLE LTA // UPLOAD
ECHO.
ECHO    LTA // UPLOAD  ^|  LISTENTOAARXN
ECHO    --------------------------------
ECHO.
IF NOT EXIST ".venv\Scripts\python.exe" (
  ECHO [1/3] Creating Python virtual environment...
  py -3.11 -m venv .venv 2>nul
  IF ERRORLEVEL 1 py -3.12 -m venv .venv 2>nul
  IF NOT EXIST ".venv\Scripts\python.exe" python -m venv .venv 2>nul
  IF NOT EXIST ".venv\Scripts\python.exe" (
    ECHO ERROR: Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/
    ECHO Tick "Add Python to PATH" during setup, then run this file again.
    PAUSE
    EXIT /B 1
  )
)
IF NOT EXIST ".venv\deps_installed.txt" (
  ECHO [2/3] Installing app dependencies. This can take a few minutes the first time...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  IF ERRORLEVEL 1 GOTO :fail
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  IF ERRORLEVEL 1 GOTO :fail
  ECHO Installed > ".venv\deps_installed.txt"
)
where ffmpeg >nul 2>&1
IF ERRORLEVEL 1 (
 ECHO WARNING: FFmpeg not detected. Rendering requires FFmpeg on PATH.
 ECHO See README_FIRST.md for setup instructions.
)
ECHO [3/3] Starting LTA // UPLOAD...
".venv\Scripts\python.exe" gui.py
IF ERRORLEVEL 1 GOTO :fail
EXIT /B 0
:fail
ECHO.
ECHO ERROR: Installation or app startup failed. Read README_FIRST.md.
PAUSE
EXIT /B 1
