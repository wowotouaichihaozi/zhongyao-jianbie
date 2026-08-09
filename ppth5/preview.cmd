@echo off
cd /d "%~dp0"
set NO_PROXY=127.0.0.1,localhost
pnpm start
