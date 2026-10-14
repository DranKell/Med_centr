@echo off
setlocal EnableExtensions

rem Supported Python: 3.11 or 3.12 (pinned packages have no wheels for 3.13+).
rem If no supported Python is found, Python 3.12.8 is downloaded and installed for the current user.
rem Keep this file ASCII-only: cmd.exe parses it in the OEM code page.

set "PY_VER=3.12.8"
set "PY_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
set "PY_INSTALLER=%TEMP%\python-3.12.8-amd64.exe"
set "PY_INSTALL_DIR=%LOCALAPPDATA%\Programs\Python\Python312"

cd /d "%~dp0backend" || goto :err_nobackend

set "PYTHON="
set "BASE="
set "PYTHONUTF8=1"

if exist "venv\Scripts\python.exe" goto :check_venv
goto :find_python

:check_venv
"venv\Scripts\python.exe" -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,12) else 1)" >nul 2>&1
if errorlevel 1 goto :broken_venv
set "PYTHON=%CD%\venv\Scripts\python.exe"
goto :after_python

:broken_venv
echo [INFO] backend\venv is broken or uses an unsupported Python. Renaming it and creating a new one.
ren "venv" "venv_old_%RANDOM%" || goto :err_rename
goto :find_python

:find_python
call :probe py -3.12
if not defined BASE call :probe py -3.11
if not defined BASE call :probe py -3
if not defined BASE call :probe python
if not defined BASE call :use_installed
if not defined BASE goto :install_python
goto :create_venv

:install_python
echo [SETUP] Python 3.11 or 3.12 was not found. Downloading Python %PY_VER% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_INSTALLER%' -UseBasicParsing" || goto :err_download
echo [SETUP] Installing Python %PY_VER% for the current user. Please wait...
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 || goto :err_pyinstall
del /q "%PY_INSTALLER%" >nul 2>&1
call :use_installed
if not defined BASE goto :err_pyinstall
goto :create_venv

:create_venv
echo [SETUP] Creating backend\venv with: %BASE%
"%BASE%" -m venv "venv" || goto :err_venv
set "PYTHON=%CD%\venv\Scripts\python.exe"

:after_python
echo [CHECK] Checking dependencies...
"%PYTHON%" -c "import fastapi, uvicorn, sqlalchemy, pydantic, pydantic_settings, dotenv, httpx, multipart, docxtpl, docx, jinja2" >nul 2>&1
if not errorlevel 1 goto :deps_ok
echo [INSTALL] Installing requirements.txt ...
"%PYTHON%" -m pip install --disable-pip-version-check -r "requirements.txt" || goto :err_pip
goto :after_deps

:deps_ok
echo [OK] Dependencies are already installed.

:after_deps
if exist ".env" goto :after_env
if not exist ".env.example" goto :after_env
copy /y ".env.example" ".env" >nul
echo [INFO] Created backend\.env from .env.example. Fill in AI keys if needed.

:after_env
echo [DB] Checking SOP catalogue...
"%PYTHON%" seed_sops.py || goto :err_seed

echo.
echo Frontend + Backend: http://127.0.0.1:9090/
echo Swagger:            http://127.0.0.1:9090/docs
echo The browser will open automatically when the server is ready.
echo Stop: Ctrl+C
echo.
"%PYTHON%" run.py
if errorlevel 1 pause
endlocal
exit /b 0

:err_nobackend
echo [ERROR] Folder backend was not found next to start.bat.
goto :fail

:err_rename
echo [ERROR] Could not rename backend\venv. Close programs that use it and retry.
goto :fail

:err_download
echo [ERROR] Could not download Python from %PY_URL%
echo Check the internet connection and run start.bat again.
goto :fail

:err_pyinstall
echo [ERROR] Python installation failed or Python was not found after installation.
echo Install Python 3.12 from https://www.python.org/downloads/ , tick "Add python.exe to PATH",
echo then run start.bat again. Python 3.13 and newer are not supported by this project.
goto :fail

:err_venv
echo [ERROR] Failed to create the virtual environment.
goto :fail

:err_pip
echo [ERROR] Failed to install requirements. Check the internet connection.
goto :fail

:err_seed
echo [ERROR] Failed to create the SOP catalogue.
goto :fail

:fail
pause
endlocal
exit /b 1

rem Usage: call :probe <python launcher and args>
rem Sets BASE to the executable path only if it is Python 3.11 or 3.12.
:probe
set "BASE="
for /f "delims=" %%P in ('%* -c "import sys;print(sys.executable)" 2^>nul') do set "BASE=%%P"
if not defined BASE exit /b 0
"%BASE%" -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,12) else 1)" >nul 2>&1
if errorlevel 1 set "BASE="
exit /b 0

rem Sets BASE to the Python installed by this script (default per-user path) if it is 3.11 or 3.12.
:use_installed
set "BASE="
if not exist "%PY_INSTALL_DIR%\python.exe" exit /b 0
set "BASE=%PY_INSTALL_DIR%\python.exe"
"%BASE%" -c "import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,12) else 1)" >nul 2>&1
if errorlevel 1 set "BASE="
exit /b 0
