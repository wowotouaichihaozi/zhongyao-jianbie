@echo off
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8765 --reload
