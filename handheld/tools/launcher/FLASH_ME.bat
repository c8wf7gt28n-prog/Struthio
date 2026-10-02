@echo off
rem ==========================================================================
rem  STRUTHIO - put the game on the board. Double-click this file.
rem
rem  It does everything itself:
rem    1. finds Python (installs it with winget if it is missing)
rem    2. installs esptool, Espressif's flashing tool, the first time
rem    3. finds the board on USB by itself (Espressif's USB ID 303A)
rem    4. writes the game, its pictures and its music, and checks every byte
rem  Nothing here needs ESP-IDF. To build the firmware yourself, use STRUTHIO.bat.
rem ==========================================================================
setlocal EnableExtensions EnableDelayedExpansion
title STRUTHIO - flash the game
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PRE=%ROOT%\prebuilt"

echo.
echo  ===============================================================
echo    STRUTHIO  -  put the game on the board
echo  ===============================================================
echo.
if not exist "%PRE%\flash_args.txt" (
  echo  This file must stay in the STRUTHIO folder, next to the "prebuilt" folder.
  echo  Unzip the whole package first, then double-click FLASH_ME.bat inside it.
  goto fail
)

rem ---- 1. Python ------------------------------------------------------------
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY="%LocalAppData%\Programs\Python\Python312\python.exe""
if not defined PY (
  echo  [1/4] Python is not installed. Installing it now with winget ^(Windows' own installer^)...
  winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
  if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY="%LocalAppData%\Programs\Python\Python312\python.exe""
)
if not defined PY (
  echo.
  echo  Python could not be installed automatically.
  echo  Install it from https://www.python.org/downloads/  ^(tick "Add python.exe to PATH"^),
  echo  then double-click FLASH_ME.bat again.
  start "" https://www.python.org/downloads/
  goto fail
)
echo  [1/4] Python: ok

rem ---- 2. esptool -----------------------------------------------------------
%PY% -m esptool version >nul 2>&1
if errorlevel 1 (
  echo  [2/4] Installing esptool ^(once, about 30 s^)...
  %PY% -m pip install --user --quiet --disable-pip-version-check "esptool>=5"
  %PY% -m esptool version >nul 2>&1
  if errorlevel 1 (
    echo  esptool could not be installed. Check the internet connection and try again.
    goto fail
  )
)
echo  [2/4] esptool: ok

rem ---- 3. the board ---------------------------------------------------------
:find_board
set "PORT="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$d = Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPDeviceID -match 'VID_303A' -and $_.Name -match '\(COM\d+\)' } | Select-Object -First 1; if ($d) { [regex]::Match($d.Name, 'COM\d+').Value }"`) do set "PORT=%%P"
if not defined PORT (
  echo.
  echo  [3/4] No board found on USB.
  echo        - Plug the Waveshare board into this computer with a USB-C DATA cable
  echo          ^(many cables only charge: if nothing happens, try another one^).
  echo        - Still nothing? Put it in download mode: hold BOOT, press and release RESET,
  echo          release BOOT ^(in a finished case: the two small pin holes on the left side^).
  echo.
  echo  Press a key to look again, or close this window to stop.
  pause >nul
  goto find_board
)
echo  [3/4] Board found on %PORT%

rem ---- 4. flash -------------------------------------------------------------
echo  [4/4] Writing the game, its pictures and its music ^(about 2 minutes^)...
echo.
pushd "%PRE%"
%PY% -m esptool --chip esp32s3 -p %PORT% -b 460800 write-flash @flash_args.txt
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" (
  echo.
  echo  Flashing stopped. Put the board in download mode and try once more:
  echo    hold BOOT, press and release RESET, release BOOT, then press a key here.
  pause >nul
  pushd "%PRE%"
  %PY% -m esptool --chip esp32s3 -p %PORT% -b 115200 write-flash @flash_args.txt
  set "RC=!ERRORLEVEL!"
  popd
)
if not "%RC%"=="0" goto fail

echo.
echo  ===============================================================
echo    DONE. Every file was written and checked ^("Hash of data verified"^).
echo    Unplug the board, or press RESET: the first power-on check starts.
echo  ===============================================================
echo.
pause
exit /b 0

:fail
echo.
echo  Nothing was changed on the board. The manual's "Flashing" faults table has more help.
echo.
pause
exit /b 1
