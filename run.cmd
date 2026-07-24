@echo off
rem Trophy Hunter Dashboard - double-click launcher (Windows).
rem Starts the backend (:8000) + frontend (:5173) in two windows and opens the browser.
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
  echo(
  echo   Backend not set up yet. Do the one-time setup first ^(see README.md^):
  echo     cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
  echo     cd ..\frontend ^&^& npm install
  echo(
  pause
  exit /b 1
)

start "Trophy Hunter - backend"  cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
start "Trophy Hunter - frontend" cmd /k "cd frontend && npm run dev"

echo Starting servers... a browser tab will open in a few seconds.
echo (Close the two windows that opened to stop the app.)
timeout /t 6 >nul
start "" "http://localhost:5173/u/dakinwu20"
