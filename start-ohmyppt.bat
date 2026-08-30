@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "BASE_DIR=%~dp0"
set "PPT_DIR=%BASE_DIR%ppth5\backend"
if not defined PPTH5_PORT set "PPTH5_PORT=8765"
set "HEALTH_URL=http://127.0.0.1:%PPTH5_PORT%/api/health"
set "VENV_PYTHON=%PPT_DIR%\.venv\Scripts\python.exe"
set "PPT_PYTHON="

if not exist "%PPT_DIR%\main.py" (
  echo [ERROR] OhMyPPT backend entry was not found.
  exit /b 1
)

call :CheckHttp "%HEALTH_URL%"
if not errorlevel 1 (
  echo [OK] OhMyPPT is already running: %HEALTH_URL%
  exit /b 0
)

netstat -ano | findstr /R /C:":%PPTH5_PORT% .*LISTENING" >nul 2>nul
if not errorlevel 1 (
  echo [ERROR] Port %PPTH5_PORT% is occupied, but OhMyPPT is not healthy.
  exit /b 1
)

if exist "%VENV_PYTHON%" (
  "%VENV_PYTHON%" -c "import fastapi, uvicorn, pydantic" >nul 2>nul
  if not errorlevel 1 set "PPT_PYTHON=%VENV_PYTHON%"
)

if not defined PPT_PYTHON (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import fastapi, uvicorn, pydantic" >nul 2>nul
    if not errorlevel 1 set "PPT_PYTHON=python"
  )
)

if not defined PPT_PYTHON (
  echo [ERROR] No Python runtime with the OhMyPPT dependencies was found.
  echo   Install them with: python -m pip install -r "%PPT_DIR%\requirements.txt"
  exit /b 1
)

echo [START] Starting OhMyPPT on port %PPTH5_PORT%...
start "QianZhiXueHang OhMyPPT %PPTH5_PORT%" /D "%PPT_DIR%" /MIN cmd /c ""%PPT_PYTHON%" -m uvicorn main:app --host 127.0.0.1 --port %PPTH5_PORT%"
call :WaitHttp "%HEALTH_URL%" 30
if errorlevel 1 (
  echo [ERROR] OhMyPPT did not become ready: %HEALTH_URL%
  exit /b 1
)

echo [OK] OhMyPPT is ready: %HEALTH_URL%
exit /b 0

:CheckHttp
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%~1' -TimeoutSec 3; if ($r.StatusCode -eq 200 -and ($r.Content | ConvertFrom-Json).ok) { exit 0 } exit 1 } catch { exit 1 }"
exit /b %errorlevel%

:WaitHttp
set "WAIT_URL=%~1"
set /a WAIT_LIMIT=%~2
for /L %%S in (1,1,%WAIT_LIMIT%) do (
  call :CheckHttp "%WAIT_URL%"
  if not errorlevel 1 exit /b 0
  timeout /t 1 /nobreak >nul
)
exit /b 1
