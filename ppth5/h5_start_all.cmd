@echo off
cd /d "%~dp0"
set NO_PROXY=127.0.0.1,localhost
start "ppth5-backend-lite" cmd /k backend.cmd
timeout /t 3 /nobreak >nul
start "ppth5-web-lite" cmd /k web.cmd
echo.
echo Lite backend: http://127.0.0.1:8765/api/health
echo Lite web:     http://127.0.0.1:5188
echo Note: this is the limited H5 adapter, not the full Electron app.
