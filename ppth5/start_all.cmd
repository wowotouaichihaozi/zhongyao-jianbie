@echo off
cd /d "%~dp0"
set NO_PROXY=127.0.0.1,localhost
start "ppth5-web-full" cmd /k web_full.cmd
echo.
echo Full Web app: browser frontend with original IPC capabilities through local backend
