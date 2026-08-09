@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "BASE_DIR=%~dp0"
set "FRONTEND_DIR=%BASE_DIR%frontend"
if not defined FRONTEND_PORT set "FRONTEND_PORT=5088"
set "FRONTEND_URL=http://localhost:%FRONTEND_PORT%"
set "NPM_CMD="

title QianZhiXueHang Frontend %FRONTEND_PORT%

echo ========================================
echo   QianZhiXueHang Frontend
echo ========================================
echo.
echo Frontend directory:
echo   %FRONTEND_DIR%
echo Frontend URL:
echo   %FRONTEND_URL%
echo.

if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] frontend\package.json was not found.
  goto :Fail
)

call :CheckPort "%FRONTEND_PORT%" "%FRONTEND_URL%"
if errorlevel 2 goto :Fail
if errorlevel 1 goto :AlreadyRunning

call :FindCommand npm.cmd NPM_CMD "Node.js/npm was not found. Please install Node.js 18+."
if errorlevel 1 goto :Fail

cd /d "%FRONTEND_DIR%"

if not exist "%FRONTEND_DIR%\node_modules\.bin\vite.cmd" (
  echo [SETUP] Installing frontend dependencies. This may take a while on first run...
  call "%NPM_CMD%" install
  if errorlevel 1 goto :Fail
) else (
  echo [OK] Frontend dependencies are ready.
)

echo.
echo [START] Starting frontend on port %FRONTEND_PORT%...
echo.
call "%NPM_CMD%" run dev -- --host 0.0.0.0 --port %FRONTEND_PORT% --strictPort
exit /b %errorlevel%

:AlreadyRunning
echo [OK] Frontend is already running:
echo   %FRONTEND_URL%
exit /b 0

:Fail
echo.
echo Frontend startup failed.
if not "%NO_PAUSE%"=="1" pause
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
