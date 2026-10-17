@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m workbench.installer
) else (
  python -m workbench.installer
)
if errorlevel 1 (
  echo.
  echo Python 3.11+ with Tkinter is needed for the optional drag-to-install window.
  echo Workbench also runs portably: double-click START_ARC1.cmd in this folder.
  pause
)
