@echo off
cd /d "%~dp0"
set ARC_LEDGER_EDITION=office
if not defined ARC_LEDGER_OPEN set ARC_LEDGER_OPEN=office
if exist .venv\Scripts\python.exe (.venv\Scripts\python.exe -m workbench.launch %*) else (py -3 -m workbench.launch %*)
