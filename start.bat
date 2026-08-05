@echo off
echo.
echo ============================================
echo   Vinaval AI - Launcher
echo ============================================
echo.
echo   Starting servers and waiting for health checks...
echo   (Browser will open automatically when ready)
echo.
"%~dp0backend\venv\Scripts\python.exe" "%~dp0launch.py"
