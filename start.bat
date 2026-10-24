@echo off
REM Inicia LiveVoice Studio desde el código fuente (crea el entorno la primera vez).
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Preparando LiveVoice Studio por primera vez...
    py -3.13 -m venv .venv || python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
start "" ".venv\Scripts\pythonw.exe" main.py
