@echo off
setlocal
cd /d "%~dp0"
title ARC-1 Workbench - Qt Preview
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import PySide6" >nul 2>nul
  if not errorlevel 1 (
    py -3 -m workbench.qt_app
    exit /b %errorlevel%
  )
) else (
  python -c "import PySide6" >nul 2>nul
  if not errorlevel 1 (
    python -m workbench.qt_app
    exit /b %errorlevel%
  )
)
echo.
echo Qt 6 / PySide6 is not installed for this Python interpreter.
echo Install:  py -3 -m pip install PySide6
echo Then run START_ARC1_QT.cmd again.
echo The existing classic desktop remains available via START_ARC1.cmd.
pause
exit /b 1
