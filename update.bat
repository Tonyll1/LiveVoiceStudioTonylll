@echo off
REM Actualiza las librerias (por ejemplo cuando Microsoft o TikTok cambian algo y la voz deja de funcionar).
cd /d "%~dp0"
".venv\Scripts\python.exe" -m pip install --upgrade -r requirements.txt
".venv\Scripts\python.exe" -m pip install --upgrade edge-tts
echo.
echo Listo. Vuelve a abrir LiveVoice Studio.
pause
