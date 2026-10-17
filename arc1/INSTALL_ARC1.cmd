@echo off
rem ARC-1 Workbench installer - double-click this file after extracting the ZIP.
rem Finds Python 3.11+ (offers to install it for you), then runs the guided setup:
rem copies Workbench, installs Qt, checks for a C compiler, creates shortcuts and
rem an Apps & Features entry. No administrator rights are needed.
rem If Windows shows "Windows protected your PC", click "More info" then "Run anyway":
rem this file is not signed. Read it first if you like; it only runs setup_arc1.py.
setlocal
cd /d "%~dp0"
title Install ARC-1 Workbench

if not exist "%~dp0workbench\setup_arc1.py" (
  echo.
  echo  This file was started from inside the ZIP.
  echo  Right-click the ZIP, choose "Extract All...", then run INSTALL_ARC1.cmd
  echo  from the extracted folder.
  echo.
  pause
  exit /b 1
)

call :find_python
if defined PY goto have_python

echo.
echo  ARC-1 Workbench needs Python 3.11 or newer, and it is not installed.
where winget >nul 2>nul
if errorlevel 1 goto no_python
choice /C YN /M " Install Python 3.12 for your user account now (about 30 MB)"
if errorlevel 2 goto no_python
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
call :find_python
if defined PY goto have_python

:no_python
echo.
echo  Please install Python 3.12 from https://www.python.org/downloads/windows/
echo  (keep "tcl/tk" ticked), then double-click INSTALL_ARC1.cmd again.
echo.
pause
exit /b 1

:have_python
%PY% -I "%~dp0workbench\setup_arc1.py" install --source "%~dp0." %*
set "RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %RESULT%

:find_python
rem Prefer the py launcher, then known per-user locations (useful right after
rem winget, before PATH is refreshed), then "python". Microsoft Store Python
rem (under WindowsApps) is skipped: it hides files it writes in AppData.
rem 3.13 and older first: the pinned Qt has no wheels for newer Python yet.
set "PY="
for %%V in (3.13 3.12 3.11 3.14) do (
  if not defined PY (
    py -%%V -c "import sys; sys.exit('windowsapps' in sys.executable.lower())" >nul 2>nul && set "PY=py -%%V"
  )
)
if defined PY exit /b 0
for %%V in (313 312 311) do (
  if not defined PY (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe""
  )
)
if defined PY exit /b 0
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) and 'windowsapps' not in sys.executable.lower() else 1)" >nul 2>nul && set "PY=python"
exit /b 0
