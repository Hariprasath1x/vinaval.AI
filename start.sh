#!/bin/bash
echo "============================================"
echo "  Vinaval AI — Starting Application"
echo "============================================"
echo ""

echo "[1/2] Starting FastAPI Backend..."
cd "$(dirname "$0")/backend"
venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

sleep 3

echo "[2/2] Starting Streamlit Frontend..."
cd "$(dirname "$0")/frontend"
../backend/venv/bin/python -m streamlit run app.py --server.port 8501 --server.address localhost &
FRONTEND_PID=$!

echo ""
echo "============================================"
echo "  Application Running:"
echo "  Backend  : http://localhost:8000"
echo "  Frontend : http://localhost:8501"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop all services."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
