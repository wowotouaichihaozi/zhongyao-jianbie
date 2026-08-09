@echo off
setlocal
cd /d "%~dp0"
start "Oh My PPT Web Full Backend" cmd /k "pnpm web:backend"
timeout /t 3 /nobreak >nul
start "Oh My PPT Web Frontend" cmd /k "pnpm web:dev"
echo.
echo Full Web mode is starting.
echo Frontend: http://127.0.0.1:5188
echo Backend:  http://127.0.0.1:8765
echo.
