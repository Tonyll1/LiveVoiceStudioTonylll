$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    py -3.13 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean LiveVoiceStudio.spec

Write-Host ""
Write-Host "EXE creado en: dist\LiveVoiceStudio.exe" -ForegroundColor Green
