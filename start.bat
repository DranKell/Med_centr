@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "PYTHON=%BACKEND%\venv\Scripts\python.exe"
set "PORT_BACKEND=9090"
set "PORT_FRONTEND=3000"
set "URL=http://127.0.0.1:%PORT_FRONTEND%/?restart=%RANDOM%%RANDOM%"

title Dental Clinic Documents - Restart
color 0A

echo.
echo  Dental Clinic Documents - перезапуск
echo  Backend:  http://127.0.0.1:%PORT_BACKEND%
echo  Frontend: http://127.0.0.1:%PORT_FRONTEND%
echo.

if not exist "%PYTHON%" (
    echo [ОШИБКА] Не найден Python проекта:
    echo "%PYTHON%"
    echo Создайте backend\venv и установите backend\requirements.txt.
    pause
    exit /b 1
)

if not exist "%FRONTEND%\index.html" (
    echo [ОШИБКА] Не найден frontend\index.html в:
    echo "%FRONTEND%"
    pause
    exit /b 1
)

echo [1/4] Остановка предыдущих серверов этого проекта...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=[IO.Path]::GetFullPath($env:ROOT).TrimEnd('\'); $procs=Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0 -and (($_.CommandLine -match 'uvicorn main:app.*--port 9090') -or ($_.CommandLine -match 'http.server 3000')) }; $ids=@($procs | Select-Object -ExpandProperty ProcessId); foreach($id in $ids){ Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }; foreach($p in $procs){ if($p.ParentProcessId){ Stop-Process -Id $p.ParentProcessId -Force -ErrorAction SilentlyContinue } }; if($ids.Count -gt 0){ 'Stopped project process(es): ' + ($ids -join ', ') } else { 'No previous project server processes found.' }"

for %%P in (%PORT_BACKEND% %PORT_FRONTEND%) do (
    powershell -NoProfile -Command "$c=Get-NetTCPConnection -State Listen -LocalPort %%P -ErrorAction SilentlyContinue | Select-Object -First 1; if($c){ exit 1 } else { exit 0 }"
    if errorlevel 1 (
        echo [ОШИБКА] Порт %%P занят процессом, который не удалось определить как сервер этого проекта.
        echo Скрипт не будет останавливать чужой процесс. Освободите порт %%P и запустите снова.
        pause
        exit /b 1
    )
)

echo [2/4] Запуск backend без autoreload...
start "Dental Backend 9090" /D "%BACKEND%" "%PYTHON%" -m uvicorn main:app --host 127.0.0.1 --port %PORT_BACKEND%

set "BACKEND_READY=0"
for /L %%I in (1,1,30) do (
    powershell -NoProfile -Command "try { $r=Invoke-RestMethod 'http://127.0.0.1:%PORT_BACKEND%/health' -TimeoutSec 2; if($r.status -eq 'ok'){ exit 0 } else { exit 1 } } catch { exit 1 }"
    if not errorlevel 1 (
        set "BACKEND_READY=1"
        goto backend_ready
    )
    >nul 2>&1 ping 127.0.0.1 -n 2
)

:backend_ready
if "%BACKEND_READY%"=="0" (
    echo [ОШИБКА] Backend не ответил на /health за 60 секунд.
    echo Проверьте консоль "Dental Backend 9090" и файл backend\.env.
    pause
    exit /b 1
)

echo [3/4] Запуск frontend на localhost...
start "Dental Frontend 3000" /D "%FRONTEND%" "%PYTHON%" -m http.server %PORT_FRONTEND% --bind 127.0.0.1

set "FRONTEND_READY=0"
for /L %%I in (1,1,15) do (
    powershell -NoProfile -Command "try { $r=Invoke-WebRequest 'http://127.0.0.1:%PORT_FRONTEND%/' -TimeoutSec 2; if($r.StatusCode -eq 200){ exit 0 } else { exit 1 } } catch { exit 1 }"
    if not errorlevel 1 (
        set "FRONTEND_READY=1"
        goto frontend_ready
    )
    >nul 2>&1 ping 127.0.0.1 -n 2
)

:frontend_ready
if "%FRONTEND_READY%"=="0" (
    echo [ОШИБКА] Frontend не ответил на порту %PORT_FRONTEND%.
    echo Проверьте консоль "Dental Frontend 3000".
    pause
    exit /b 1
)

echo [4/4] Открытие приложения с обходом кэша...
start "" "%URL%"

echo.
echo Backend и frontend отвечают.
echo После отключения VPN нажмите кнопку ИИ и смотрите статус рядом с кнопкой.
echo Логи доступны в окнах "Dental Backend 9090" и "Dental Frontend 3000".
echo Для следующего перезапуска закройте это окно и снова запустите start.bat.
echo.
pause
endlocal
