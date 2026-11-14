@echo off
setlocal
cd /d "%~dp0"
set "LOCAL_BACKEND_URL="
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-remote.ps1"
