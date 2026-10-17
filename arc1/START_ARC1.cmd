@echo off
setlocal
cd /d "%~dp0"
title ARC-1 Workbench - Adaptive RISC-V Console
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m workbench.app
) else (
  python -m workbench.app
)
if errorlevel 1 (
 echo.
 echo Workbench could not start. Install Python 3.11+ from python.org with Tkinter.
 echo You can still use START_ARC1_TEXT.cmd for the text development menu.
 pause
)
exit /b %ERRORLEVEL%
