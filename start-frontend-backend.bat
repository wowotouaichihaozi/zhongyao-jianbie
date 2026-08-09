@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "BASE_DIR=%~dp0"
set "FRONTEND_DIR=%BASE_DIR%frontend"
set "ADMIN_DIR=%BASE_DIR%admin"
if not defined BACKEND_PORT set "BACKEND_PORT=3000"
set "APP_URL=http://localhost:%BACKEND_PORT%"
set "HEALTH_URL=%APP_URL%/api/health"

if not exist "%BASE_DIR%start-backend.bat" (
  echo [ERROR] start-backend.bat was not found.
  exit /b 1
)
if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] frontend\package.json was not found.
  exit /b 1
)

where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js/npm was not found. Please install Node.js 18+.
  exit /b 1
)

echo [1/3] Building frontend bundle for the unified entry...
pushd "%FRONTEND_DIR%"
call npm.cmd run build
if errorlevel 1 (
  popd
  exit /b 1
)
popd

echo [2/3] Building admin bundle for the unified entry...
pushd "%ADMIN_DIR%"
set "VITE_BASE_URL=/admin/"
call pnpm.cmd run build
if errorlevel 1 (
  popd
  exit /b 1
)
popd

echo [3/3] Starting or reusing the unified Flask entry...
call :CheckHttp "%HEALTH_URL%"
if errorlevel 1 (
  start "QianZhiXueHang Unified %BACKEND_PORT%" /D "%BASE_DIR%" cmd /k "set BACKEND_PORT=%BACKEND_PORT%&& call start-backend.bat"
)

call :WaitHttp "%HEALTH_URL%" 60
if errorlevel 1 exit /b 1

echo.
echo Unified application:
echo   %APP_URL%
echo Admin: 
echo   %APP_URL%/admin/
echo API health:
echo   %HEALTH_URL%
exit /b 0

:CheckHttp
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%~1' -TimeoutSec 3; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } exit 1 } catch { exit 1 }"
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