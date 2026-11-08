@echo off
rem Trophy Hunter Dashboard - double-click launcher (Windows).
rem Starts the backend (:8001) + frontend (:5174) in two windows and opens the browser.
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
  echo(
  echo   Backend not set up yet. Do the one-time setup first ^(see README.md^):
  echo     cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.lock
  echo     cd ..\frontend ^&^& npm install
  echo(
  pause
  exit /b 1
)

pushd frontend
call npm ls --depth=0 >nul 2>&1
if errorlevel 1 (
  echo Frontend dependencies changed; syncing packages...
  call npm install --no-audit --no-fund
  if errorlevel 1 (
    echo(
    echo   Failed to install frontend dependencies.
    popd
    pause
    exit /b 1
  )
)
popd

start "Trophy Hunter - backend"  cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app --port 8001"
start "Trophy Hunter - frontend" cmd /k "cd frontend && npm run dev -- --force"

echo Starting servers... a browser tab will open in a few seconds.
echo (Close the two windows that opened to stop the app.)
timeout /t 6 >nul
start "" "http://localhost:5174/"
