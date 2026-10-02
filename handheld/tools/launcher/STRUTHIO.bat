@echo off
rem ==========================================================================
rem  STRUTHIO HANDHELD - build menu for Windows 10 / 11
rem  Double-click this file, or run it from "ESP-IDF 5.5 CMD".
rem  Every option prints the exact command it runs, so you learn the commands
rem  the build manual uses while the menu types them for you.
rem
rem  One-shot use, for shortcuts and scripts:   STRUTHIO.bat greybox
rem  (doctor, port, build, greybox, full, quick, monitor, desktop, bootmode)
rem ==========================================================================
setlocal EnableExtensions
title STRUTHIO HANDHELD
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "HH=%ROOT%\handheld"
set "FW=%HH%\firmware"
set "PORTFILE=%ROOT%\struthio_port.txt"
set "PORT="
if exist "%PORTFILE%" set /p PORT=<"%PORTFILE%"

if not exist "%FW%\CMakeLists.txt" (
  echo.
  echo  This file must stay in the STRUTHIO folder, next to the "handheld" folder.
  echo  Unzip the whole package to C:\ so you get C:\struthio\STRUTHIO.bat
  echo.
  pause
  exit /b 1
)
if not "%ROOT: =%"=="%ROOT%" (
  echo.
  echo  WARNING: the folder path contains a space:  %ROOT%
  echo  ESP-IDF builds can fail there. Move the folder to C:\struthio
  echo.
  pause
)

call :find_idf

set "ONESHOT="
if "%~1"=="" goto menu
set "ONESHOT=1"
if /i "%~1"=="doctor"   goto doctor
if /i "%~1"=="port"     goto choose_port
if /i "%~1"=="build"    goto build
if /i "%~1"=="greybox"  goto greybox
if /i "%~1"=="full"     goto fullart
if /i "%~1"=="quick"    goto quickflash
if /i "%~1"=="monitor"  goto monitor
if /i "%~1"=="desktop"  goto desktop
if /i "%~1"=="bootmode" goto bootmode
echo  Unknown option "%~1". Options: doctor port build greybox full quick monitor desktop bootmode
exit /b 1

:menu
cls
echo  ===============================================================
echo    STRUTHIO HANDHELD  -  build menu
echo  ===============================================================
if defined IDF_OK (echo    ESP-IDF : ready) else (echo    ESP-IDF : NOT FOUND - see option 1)
if defined PORT (echo    Board   : %PORT%) else (echo    Board   : not chosen yet - option 2)
echo  ---------------------------------------------------------------
echo    1  Check my setup              (doctor: package, ESP-IDF, port)
echo    2  Find / choose the board's port
echo    3  Build the firmware          (first time: sets the chip)
echo    4  GREYBOX test   - build, flash, watch the log   (Step 5)
echo    5  FULL ART       - build, flash, watch the log   (Step 5)
echo    6  Quick flash    - program only, keeps art + music
echo    7  Watch the log  (monitor)     leave with Ctrl + ]
echo    8  Download-mode help (BOOT + RESET)
echo    9  Erase the whole board        (clears high score + settings)
echo    D  Desktop checks (WSL)         (Step 3)
echo    M  Open the build manual
echo    F  Open the package folder
echo    0  Exit
echo  ---------------------------------------------------------------
set "CH="
set /p CH=  Choose:
if "%CH%"=="1" goto doctor
if "%CH%"=="2" goto choose_port
if "%CH%"=="3" goto build
if "%CH%"=="4" goto greybox
if "%CH%"=="5" goto fullart
if "%CH%"=="6" goto quickflash
if "%CH%"=="7" goto monitor
if "%CH%"=="8" goto bootmode
if "%CH%"=="9" goto erase
if /i "%CH%"=="D" goto desktop
if /i "%CH%"=="M" goto manual
if /i "%CH%"=="F" goto folder
if "%CH%"=="0" goto end
goto menu

rem --------------------------------------------------------------------------
:doctor
call :need_python
if errorlevel 1 goto pause_menu
echo.
echo  ^> python "%HH%\tools\struthio_doctor.py"
"%PY%" "%HH%\tools\struthio_doctor.py"
goto pause_menu

:choose_port
call :need_python
if errorlevel 1 goto pause_menu
echo.
echo  Looking for the board (ESP32-S3 USB port)...
set "FOUND="
for /f "delims=" %%P in ('call "%PY%" "%HH%\tools\struthio_doctor.py" --port 2^>nul') do set "FOUND=%%P"
if not defined FOUND goto port_by_hand
echo  Found the board on %FOUND%.
set "PORT=%FOUND%"
>"%PORTFILE%" echo %FOUND%
goto pause_menu
:port_by_hand
echo  The board was not recognised automatically. Ports Windows can see:
powershell -NoProfile -Command "Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match '\(COM\d+\)' } | ForEach-Object { '   ' + $_.Name }"
echo.
echo  Tip: unplug the board, look at the list, plug it in again: the new COM
echo  port is the board. No new port = try another USB-C DATA cable.
echo.
set "NEWPORT="
set /p NEWPORT=  Type the port (for example COM5), or press Enter to skip:
if not defined NEWPORT goto pause_menu
set "PORT=%NEWPORT%"
>"%PORTFILE%" echo %NEWPORT%
goto pause_menu

:build
call :need_idf
if errorlevel 1 goto pause_menu
call :ensure_target
if errorlevel 1 goto pause_menu
echo.
echo  ^> idf.py -C "%FW%" build
call idf.py -C "%FW%" build
call :result Build
goto pause_menu

:greybox
call :need_idf
if errorlevel 1 goto pause_menu
call :need_port
if errorlevel 1 goto pause_menu
call :ensure_target
if errorlevel 1 goto pause_menu
echo.
echo  GREYBOX TEST: flat colours on purpose. The log line "assets: greybox marker"
echo  is expected. Leave the log with Ctrl + ].
echo  ^> idf.py -C "%FW%" -p %PORT% -D STRUTHIO_ART=greybox build flash monitor
call idf.py -C "%FW%" -p %PORT% -D STRUTHIO_ART=greybox build flash monitor
goto pause_menu

:fullart
call :need_idf
if errorlevel 1 goto pause_menu
call :need_port
if errorlevel 1 goto pause_menu
call :ensure_target
if errorlevel 1 goto pause_menu
echo.
echo  FULL ART: writes the program, the 8.3 MB art pack and the 1.9 MB soundtrack.
echo  The first full flash takes a few minutes. Leave the log with Ctrl + ].
echo  ^> idf.py -C "%FW%" -p %PORT% -D STRUTHIO_ART=full build flash monitor
call idf.py -C "%FW%" -p %PORT% -D STRUTHIO_ART=full build flash monitor
goto pause_menu

:quickflash
call :need_idf
if errorlevel 1 goto pause_menu
call :need_port
if errorlevel 1 goto pause_menu
call :ensure_target
if errorlevel 1 goto pause_menu
echo.
echo  ^> idf.py -C "%FW%" -p %PORT% app-flash monitor
call idf.py -C "%FW%" -p %PORT% app-flash monitor
goto pause_menu

:monitor
call :need_idf
if errorlevel 1 goto pause_menu
call :need_port
if errorlevel 1 goto pause_menu
echo.
echo  Monitor keys:  Ctrl + ]  leave      Ctrl + T then Y  pause / resume
echo                 Ctrl + T then L  start / stop a log file in this folder
echo                 Ctrl + T then R  reset the board
echo  ^> idf.py -C "%FW%" -p %PORT% monitor
call idf.py -C "%FW%" -p %PORT% monitor
goto pause_menu

:bootmode
echo.
echo  If flashing says it cannot connect, put the ESP32-S3 in download mode:
echo    1. Hold the BOOT button on the board.
echo    2. Press and release RESET (RST) once.
echo    3. Release BOOT.
echo    4. Choose the flash option again.
echo    5. After flashing, press RESET once to run STRUTHIO.
echo  The COM number can change in download mode: run option 2 again if needed.
goto pause_menu

:erase
call :need_idf
if errorlevel 1 goto pause_menu
call :need_port
if errorlevel 1 goto pause_menu
echo.
echo  This erases EVERYTHING on the board: program, art, music, high score,
echo  DART mode and volume. You then need option 5 again.
set "SURE="
set /p SURE=  Type ERASE to continue:
if not "%SURE%"=="ERASE" goto menu
echo  ^> idf.py -C "%FW%" -p %PORT% erase-flash
call idf.py -C "%FW%" -p %PORT% erase-flash
goto pause_menu

:desktop
where wsl >nul 2>nul
if not errorlevel 1 goto desktop_run
echo.
echo  The desktop checks run in WSL (Ubuntu). Install it once from an
echo  Administrator PowerShell:   wsl --install
echo  then in Ubuntu:             sudo apt update ^&^& sudo apt install -y build-essential
goto pause_menu
:desktop_run
echo.
echo  ^> wsl --cd "%HH%" make -C host test
wsl --cd "%HH%" make -C host test
echo.
echo  ^> wsl --cd "%HH%" make -C firmware/host_test run
wsl --cd "%HH%" make -C firmware/host_test run
echo.
echo  PASS means: 5 lines starting "PASS", then "GOLDEN REPLAY: all 5 traces bit-exact",
echo  then "PASS: wing buttons (...)". The manual, Step 3, shows the exact lines.
goto pause_menu

:manual
if exist "%ROOT%\manual\STRUTHIO_Build_Manual.pdf" start "" "%ROOT%\manual\STRUTHIO_Build_Manual.pdf"
goto menu

:folder
start "" explorer "%ROOT%"
goto menu

rem --------------------------------------------------------------------------
:pause_menu
if defined ONESHOT goto end
echo.
pause
goto menu

:result
if errorlevel 1 goto result_fail
echo.
echo  %~1 OK.
exit /b 0
:result_fail
echo.
echo  %~1 FAILED - read the first "error:" line above, then see Step 12 of the manual.
exit /b 1

:need_idf
if defined IDF_OK exit /b 0
call :find_idf
if defined IDF_OK exit /b 0
echo.
echo  ESP-IDF was not found in this window.
echo  Fix: open the Start menu, run "ESP-IDF 5.5 CMD", then type:
echo       cd /d "%ROOT%"
echo       STRUTHIO.bat
echo  (Install ESP-IDF 5.5.x first if you have not: manual, Step 3.)
exit /b 1

:need_python
set "PY="
for %%X in (python.exe py.exe) do if not defined PY for /f "delims=" %%Q in ('where %%X 2^>nul') do if not defined PY call :try_python "%%Q"
if defined PY exit /b 0
echo.
echo  Python was not found. Run this menu from "ESP-IDF 5.5 CMD" (it includes Python).
exit /b 1

:try_python
rem the Microsoft Store "python" stub (WindowsApps) only opens the Store: skip it
echo %~1 | find /i "WindowsApps" >nul
if not errorlevel 1 exit /b 0
set "PY=%~1"
exit /b 0

:need_port
if defined PORT exit /b 0
echo.
echo  Choose the board's port first (option 2).
exit /b 1

:ensure_target
if exist "%FW%\sdkconfig" exit /b 0
echo.
echo  First build in this folder: choosing the chip.
echo  ^> idf.py -C "%FW%" set-target esp32s3
call idf.py -C "%FW%" set-target esp32s3
if errorlevel 1 goto ensure_target_fail
exit /b 0
:ensure_target_fail
echo  set-target failed: read the message above.
exit /b 1

:find_idf
set "IDF_OK="
where idf.py >nul 2>nul
if not errorlevel 1 (
  set "IDF_OK=1"
  exit /b 0
)
set "EXPORT="
if defined IDF_PATH if exist "%IDF_PATH%\export.bat" set "EXPORT=%IDF_PATH%\export.bat"
if not defined EXPORT for /d %%D in ("C:\Espressif\frameworks\esp-idf-v5.5*") do if exist "%%D\export.bat" set "EXPORT=%%D\export.bat"
if not defined EXPORT if exist "%USERPROFILE%\Desktop\esp-idf\export.bat" set "EXPORT=%USERPROFILE%\Desktop\esp-idf\export.bat"
if not defined EXPORT if exist "%USERPROFILE%\esp\esp-idf\export.bat" set "EXPORT=%USERPROFILE%\esp\esp-idf\export.bat"
if not defined EXPORT exit /b 0
echo  Activating ESP-IDF: "%EXPORT%"
call "%EXPORT%" >nul
where idf.py >nul 2>nul
if not errorlevel 1 set "IDF_OK=1"
exit /b 0

:end
endlocal
exit /b 0
