# Start Study Companion at http://127.0.0.1:8000 (builds the frontend first if needed).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating Python environment..."
    python -m venv .venv
    .\.venv\Scripts\python -m pip install -r backend\requirements.txt
    .\.venv\Scripts\python -m pip install -e D:\Y26\work_dir\LLM_Bridge
}
if (-not (Test-Path "frontend\dist\index.html")) {
    Write-Host "Building the frontend..."
    Push-Location frontend
    npm install
    npm run build
    Pop-Location
}

Start-Process "http://127.0.0.1:8000"
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
