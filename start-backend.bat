@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "BASE_DIR=%~dp0"
set "BACKEND_DIR=%BASE_DIR%backend"
if not defined BACKEND_PORT set "BACKEND_PORT=3000"
set "BACKEND_URL=http://localhost:%BACKEND_PORT%/api/health"
set "VENV_DIR=%BACKEND_DIR%\venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "SYSTEM_PYTHON="

title QianZhiXueHang Backend %BACKEND_PORT%

echo ========================================
echo   QianZhiXueHang Backend
echo ========================================
echo.
echo Backend directory:
echo   %BACKEND_DIR%
echo Backend URL:
echo   %BACKEND_URL%
echo.

if not exist "%BACKEND_DIR%\app.py" (
  echo [ERROR] backend\app.py was not found.
  goto :Fail
)

if not exist "%BASE_DIR%start-ohmyppt.bat" (
  echo [ERROR] start-ohmyppt.bat was not found.
  goto :Fail
)

echo [DEPENDENCY] Checking OhMyPPT...
call "%BASE_DIR%start-ohmyppt.bat"
if errorlevel 1 goto :Fail
echo.

call :CheckPort "%BACKEND_PORT%" "%BACKEND_URL%"
if errorlevel 2 goto :Fail
if errorlevel 1 goto :AlreadyRunning

if not exist "%VENV_PYTHON%" (
  call :FindSystemPython
  if errorlevel 1 goto :Fail
  echo [SETUP] Creating backend virtual environment...
  call !SYSTEM_PYTHON! -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [ERROR] Failed to create backend virtual environment.
    goto :Fail
  )
)

echo [SETUP] Checking backend dependencies...
"%VENV_PYTHON%" -c "import flask, flask_cors, bcrypt, requests" >nul 2>nul
if errorlevel 1 (
  echo [SETUP] Installing backend dependencies. This may take a while on first run...
  "%VENV_PYTHON%" -m pip install --upgrade pip
  if errorlevel 1 goto :Fail
  "%VENV_PYTHON%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
  if errorlevel 1 goto :Fail
) else (
  echo [OK] Backend dependencies are ready.
)

echo.
echo [START] Starting backend on port %BACKEND_PORT%...
echo.
cd /d "%BACKEND_DIR%"
set "PORT=%BACKEND_PORT%"
"%VENV_PYTHON%" app.py
exit /b %errorlevel%

:AlreadyRunning
echo [OK] Backend is already running:
echo   %BACKEND_URL%
exit /b 0

:Fail
echo.
echo Backend startup failed.
if not "%NO_PAUSE%"=="1" pause
exit /b 1

:FindSystemPython
where python >nul 2>nul
if not errorlevel 1 (
  set "SYSTEM_PYTHON=python"
  exit /b 0
)
where py >nul 2>nul
if not errorlevel 1 (
  set "SYSTEM_PYTHON=py -3"
  exit /b 0
)
echo [ERROR] Python was not found. Please install Python 3.10+.
exit /b 1

:CheckHttp
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%~1' -TimeoutSec 3; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } exit 1 } catch { exit 1 }"
exit /b %errorlevel%

:CheckPort
netstat -ano | findstr /R /C:":%~1 .*LISTENING" >nul 2>nul
if errorlevel 1 exit /b 0
call :CheckHttp "%~2"
if not errorlevel 1 exit /b 1
echo [ERROR] Port %~1 is occupied, but %~2 is not healthy.
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%~1 .*LISTENING"') do (
  echo   Port owner PID: %%P
  tasklist /FI "PID eq %%P" /FO LIST 2>nul | findstr /B /C:"Image Name" /C:"PID"
  goto :PortDone
)
:PortDone
exit /b 2
