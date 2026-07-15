@echo off
echo Building the Frontend (Vite + React)...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo Error building frontend.
    exit /b %errorlevel%
)
cd ..

echo Starting the Backend with served static files...
cd backend
call venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
cd ..
