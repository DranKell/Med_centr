@echo off
setlocal EnableExtensions
cd /d "%~dp0backend"
set "PYTHON=%~dp0backend\venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
echo Frontend + Backend: http://127.0.0.1:9090/
echo Stop: Ctrl+C
"%PYTHON%" run.py
if errorlevel 1 pause
endlocal
