@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "BASE_DIR=%~dp0"
set "BACKEND_DIR=%BASE_DIR%backend"
set "FRONTEND_DIR=%BASE_DIR%frontend"
set "PPTH5_BACKEND_DIR=%BASE_DIR%ppth5\backend"
if not defined ADMIN_DIR set "ADMIN_DIR=%BASE_DIR%admin"
set "ORIGINAL_DIR=%BASE_DIR%..\demo\app\code"
set "ORIGINAL_FRONTEND_NODE_MODULES=%ORIGINAL_DIR%\frontend\node_modules"

set "BACKEND_PORT=3000"
set "FRONTEND_PORT=3000"
set "PPTH5_PORT=8765"

set "BACKEND_URL=http://localhost:%BACKEND_PORT%/api/health"
set "FRONTEND_URL=http://localhost:%BACKEND_PORT%"
set "ADMIN_URL=http://localhost:%BACKEND_PORT%/admin/"
set "PPT_URL=http://localhost:%FRONTEND_PORT%/ppt/"
set "PPT_API_URL=http://localhost:%BACKEND_PORT%/api/ppt-h5/health"
set "OHMYPPT_API_URL=http://127.0.0.1:%PPTH5_PORT%/api/health"

set "VENV_PYTHON=%BACKEND_DIR%\venv\Scripts\python.exe"
set "PPTH5_VENV_PYTHON=%PPTH5_BACKEND_DIR%\.venv\Scripts\python.exe"
set "BACKEND_PYTHON="
set "PPTH5_PYTHON="
set "NPM_CMD="
set "PNPM_CMD="
set "FAILED=0"

title FeishengWangying Start All

echo ========================================
echo   FeishengWangying - Start All
echo ========================================
echo.
echo Project directory:
echo   %BASE_DIR%
echo Admin directory:
echo   %ADMIN_DIR%
echo.

call :CheckFile "%BACKEND_DIR%\app.py" "Backend entry"
if errorlevel 1 goto :Fail
call :CheckFile "%FRONTEND_DIR%\package.json" "Frontend package.json"
if errorlevel 1 goto :Fail
call :CheckFile "%PPTH5_BACKEND_DIR%\main.py" "OhMyPPT backend entry"
if errorlevel 1 goto :Fail
call :CheckFile "%ADMIN_DIR%\package.json" "Admin package.json"
if errorlevel 1 goto :Fail

call :FindCommand npm.cmd NPM_CMD "npm was not found. Please install Node.js 18+."
if errorlevel 1 goto :Fail
call :FindCommand pnpm.cmd PNPM_CMD "pnpm was not found. Install it once with: npm install -g pnpm"
if errorlevel 1 goto :Fail

echo [1/5] Checking backend runtime...
if exist "%VENV_PYTHON%" (
  "%VENV_PYTHON%" -c "import flask, flask_cors, bcrypt, requests" >nul 2>nul
  if not errorlevel 1 (
    set "BACKEND_PYTHON=%VENV_PYTHON%"
    echo   Backend will use local venv.
  ) else (
    echo   Local backend venv exists but dependencies are incomplete.
  )
)

if not defined BACKEND_PYTHON (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import flask, flask_cors, bcrypt, requests" >nul 2>nul
    if not errorlevel 1 (
      set "BACKEND_PYTHON=python"
      echo   Backend will use global Python.
    )
  )
)

if not defined BACKEND_PYTHON (
  echo [ERROR] No usable backend Python environment was found.
  echo   cd /d "%BACKEND_DIR%"
  echo   python -m venv venv
  echo   venv\Scripts\python.exe -m pip install -r requirements.txt
  goto :Fail
)
echo   Backend runtime is ready.
echo.

echo [2/5] Checking OhMyPPT runtime...
if exist "%PPTH5_VENV_PYTHON%" (
  "%PPTH5_VENV_PYTHON%" -c "import fastapi, uvicorn, pydantic" >nul 2>nul
  if not errorlevel 1 (
    set "PPTH5_PYTHON=%PPTH5_VENV_PYTHON%"
    echo   OhMyPPT will use its local venv.
  )
)
if not defined PPTH5_PYTHON (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import fastapi, uvicorn, pydantic" >nul 2>nul
    if not errorlevel 1 set "PPTH5_PYTHON=python"
  )
)
if not defined PPTH5_PYTHON (
  echo [ERROR] No usable OhMyPPT Python environment was found.
  echo   cd /d "%PPTH5_BACKEND_DIR%"
  echo   python -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  goto :Fail
)
echo   OhMyPPT runtime is ready.
echo.

echo [3/5] Checking frontend runtime...
if not exist "%FRONTEND_DIR%\node_modules\.bin\vite.cmd" (
  if exist "%ORIGINAL_FRONTEND_NODE_MODULES%\.bin\vite.cmd" (
    echo   Reusing frontend node_modules from original project.
    if not exist "%FRONTEND_DIR%\node_modules" (
      mklink /J "%FRONTEND_DIR%\node_modules" "%ORIGINAL_FRONTEND_NODE_MODULES%" >nul
      if errorlevel 1 (
        echo [ERROR] Failed to create frontend node_modules junction.
        goto :Fail
      )
    )
  )
)
if not exist "%FRONTEND_DIR%\node_modules\.bin\vite.cmd" (
  echo [ERROR] Frontend dependencies were not found.
  echo   cd /d "%FRONTEND_DIR%"
  echo   npm install
  goto :Fail
)
echo   Frontend runtime is ready.
echo   Building frontend bundle for the unified backend entry...
pushd "%FRONTEND_DIR%"
call "%NPM_CMD%" run build
set "FRONTEND_BUILD_RESULT=%errorlevel%"
popd
if not "%FRONTEND_BUILD_RESULT%"=="0" goto :Fail
echo.

echo [4/5] Checking admin runtime...
if not exist "%ADMIN_DIR%\node_modules\.bin\vite.cmd" (
  echo [ERROR] Admin dependencies were not found.
  echo   cd /d "%ADMIN_DIR%"
  echo   pnpm install
  goto :Fail
)
echo   Admin runtime is ready.
echo   Building admin bundle for the unified backend entry...
pushd "%ADMIN_DIR%"
set "VITE_BASE_URL=/admin/"
call "%PNPM_CMD%" run build
set "ADMIN_BUILD_RESULT=%errorlevel%"
popd
if not "%ADMIN_BUILD_RESULT%"=="0" goto :Fail
echo.

echo [5/5] Starting or reusing services...
call :EnsureService "OhMyPPT API" "%PPTH5_PORT%" "%OHMYPPT_API_URL%" "FSWY OhMyPPT %PPTH5_PORT%" "%PPTH5_BACKEND_DIR%" "call ""%PPTH5_PYTHON%"" -m uvicorn main:app --host 127.0.0.1 --port %PPTH5_PORT%"
if errorlevel 1 set "FAILED=1"
call :EnsureService "Backend" "%BACKEND_PORT%" "%BACKEND_URL%" "FSWY Backend %BACKEND_PORT%" "%BACKEND_DIR%" "call ""%BACKEND_PYTHON%"" app.py"
if errorlevel 1 set "FAILED=1"

echo.
echo Waiting for services to become ready...
call :WaitHttp "Backend" "%BACKEND_URL%" 30
if errorlevel 1 set "FAILED=1"
call :WaitHttp "OhMyPPT API" "%OHMYPPT_API_URL%" 30
if errorlevel 1 set "FAILED=1"
call :WaitHttp "PPT H5 API" "%PPT_API_URL%" 15
if errorlevel 1 set "FAILED=1"

echo.
echo ========================================
if "%FAILED%"=="0" (
  echo   All services are available.
) else (
  echo   Some services failed to start or failed health checks.
)
echo ========================================
echo.
echo Main app:
echo   %FRONTEND_URL%
echo Admin app (unified):
echo   %ADMIN_URL%
echo Backend health:
echo   %BACKEND_URL%
echo PPT H5:
echo   %PPT_URL%
echo PPT H5 API health:
echo   %PPT_API_URL%
echo OhMyPPT direct health:
echo   %OHMYPPT_API_URL%
echo.
echo Notes:
echo   If a port is already occupied by a healthy service, this script reuses it.
echo   If a port is occupied but the health check fails, close that process and run again.
echo.

if "%NO_PAUSE%"=="1" goto :ExitWithStatus
pause

:ExitWithStatus
if "%FAILED%"=="0" exit /b 0
exit /b 1

:Fail
set "FAILED=1"
echo.
echo ========================================
echo   Startup failed before services were ready.
echo ========================================
echo.
if "%NO_PAUSE%"=="1" exit /b 1
pause
exit /b 1

:CheckFile
if exist "%~1" exit /b 0
echo [ERROR] %~2 not found:
echo   %~1
exit /b 1

:FindCommand
set "%~2="
where %~1 >nul 2>nul
if errorlevel 1 (
  echo [ERROR] %~3
  exit /b 1
)
for /f "delims=" %%I in ('where %~1 2^>nul') do if not defined %~2 set "%~2=%%I"
exit /b 0

:ShowPortOwner
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%~1 .*LISTENING"') do (
  echo   Port %~1 is owned by PID %%P
  tasklist /FI "PID eq %%P" /FO LIST 2>nul | findstr /B /C:"Image Name" /C:"PID"
  goto :eof
)
goto :eof

:CheckHttp
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%~1' -TimeoutSec 5; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } exit 1 } catch { exit 1 }"
exit /b %errorlevel%

:WaitHttp
set "WAIT_NAME=%~1"
set "WAIT_URL=%~2"
set /a WAIT_LIMIT=%~3
if %WAIT_LIMIT% LEQ 0 set /a WAIT_LIMIT=20
for /L %%S in (1,1,%WAIT_LIMIT%) do (
  call :CheckHttp "%WAIT_URL%"
  if not errorlevel 1 (
    echo [OK] %WAIT_NAME% is ready: %WAIT_URL%
    exit /b 0
  )
  timeout /t 1 /nobreak >nul
)
echo [ERROR] %WAIT_NAME% did not become ready: %WAIT_URL%
exit /b 1

:EnsureService
set "SVC_NAME=%~1"
set "SVC_PORT=%~2"
set "SVC_URL=%~3"
set "SVC_TITLE=%~4"
set "SVC_DIR=%~5"
set "SVC_CMD=%~6"

netstat -ano | findstr /R /C:":%SVC_PORT% .*LISTENING" >nul 2>nul
if not errorlevel 1 (
  call :CheckHttp "%SVC_URL%"
  if not errorlevel 1 (
    echo [OK] %SVC_NAME% already running and healthy on port %SVC_PORT%.
    exit /b 0
  )
  echo [ERROR] %SVC_NAME% port %SVC_PORT% is occupied, but health check failed.
  call :ShowPortOwner "%SVC_PORT%"
  exit /b 1
)

echo [START] %SVC_NAME% on port %SVC_PORT%...
start "%SVC_TITLE%" /D "%SVC_DIR%" cmd /k "%SVC_CMD%"
exit /b 0
