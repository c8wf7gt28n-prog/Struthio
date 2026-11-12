@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (.venv\Scripts\python.exe -m workbench.launch %*) else (py -3 -m workbench.launch %*)
