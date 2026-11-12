@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m workbench.baseline %*
) else (
  python -m workbench.baseline %*
)
