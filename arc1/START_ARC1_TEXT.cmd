@echo off
cd /d "%~dp0"
title ARC-1 Adaptive RISC-V Console - Developer Workbench
:MENU
cls
echo =================================================
echo ARC-1  ADAPTIVE RISC-V CONSOLE  DEVELOPER WORKBENCH
echo =================================================
echo   1  Firmware status
 echo   2  Build LCD firmware object (host)
 echo   3  Test firmware modules (host)
 echo   4  Verify official ARC-1 branding
 echo   5  SDK system check
 echo   6  Show all SDK commands
 echo   0  Exit
 echo.
set /p choose=ARC1^> 
if "%choose%"=="1" call "%~dp0arc1.cmd" firmware status
if "%choose%"=="2" call "%~dp0arc1.cmd" firmware build --target status-lcd
if "%choose%"=="3" call "%~dp0arc1.cmd" firmware test
if "%choose%"=="4" call "%~dp0arc1.cmd" brand
if "%choose%"=="5" call "%~dp0arc1.cmd" doctor
if "%choose%"=="6" call "%~dp0arc1.cmd" --help
if "%choose%"=="0" exit /b 0
echo.
pause
goto MENU
