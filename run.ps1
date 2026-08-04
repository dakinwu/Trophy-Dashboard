# Trophy Hunter Dashboard - dev launcher (Windows).
# Starts the FastAPI backend (:8000) and the Vite frontend (:5173) in two windows.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if (-not (Test-Path "$root\backend\.venv\Scripts\python.exe")) {
    Write-Host "Backend venv not found. Run first-time setup (see README.md)." -ForegroundColor Yellow
    exit 1
}

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$root\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8000"
)

Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$root\frontend'; npm run dev"
)

Write-Host "Backend  -> http://localhost:8000/api/health"
Write-Host "Frontend -> http://localhost:5173"
