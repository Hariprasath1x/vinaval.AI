@echo off
echo.
echo ============================================
echo   Vinaval AI - Full Stack Launcher
echo ============================================
echo.
echo   Starting Backend (FastAPI) + Frontend (Vite)...
echo.

:: ── Start Backend in a new terminal window ──
start "Vinaval AI - Backend" cmd /k "cd /d "%~dp0backend" && ".\venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

:: ── Wait a moment for backend to begin starting ──
timeout /t 3 /nobreak >nul

:: ── Start Frontend in a new terminal window ──
start "Vinaval AI - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ============================================
echo   Both servers are starting!
echo.
echo   Backend  : http://127.0.0.1:8000
echo   Frontend : http://localhost:5173
echo.
echo   Each server runs in its own terminal window.
echo   Close those windows to stop the servers.
echo ============================================
echo.
