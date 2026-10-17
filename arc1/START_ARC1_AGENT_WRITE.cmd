@echo off
setlocal
cd /d "%~dp0"
echo This session ALLOWS agent source edits, guarded by SHA-256 and path checks.
set /p CONFIRM=Type ALLOW to continue: 
if /I not "%CONFIRM%"=="ALLOW" exit /b 1
where py >nul 2>nul
if not errorlevel 1 (
  py -3 arc1 agent --allow-writes
) else (
  python arc1 agent --allow-writes
)
exit /b %ERRORLEVEL%
