@echo off
echo ============================================
echo   Vinaval AI — Starting Application
echo ============================================
echo.

echo [1/2] Starting FastAPI Backend...
start "Vinaval Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak > nul

echo [2/2] Starting Streamlit Frontend...
start "Vinaval Frontend" cmd /k "cd /d %~dp0frontend && ..\backend\venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address localhost"

echo.
echo ============================================
echo   Application Running:
echo   Backend  : http://localhost:8000
echo   Frontend : http://localhost:8501
echo ============================================
echo.
pause
