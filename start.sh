#!/bin/bash

# Get the project root directory
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT_DIR/venv/bin/python"

echo "============================================"
echo "  Vinaval AI — Starting Application"
echo "============================================"
echo ""

# Check virtual environment
if [ ! -x "$PYTHON" ]; then
    echo "ERROR: Virtual environment not found at:"
    echo "$ROOT_DIR/venv"
    echo ""
    echo "Create it with:"
    echo "python3 -m venv venv"
    exit 1
fi

if [ -f "$ROOT_DIR/.env" ]; then
    echo "Loading environment variables from .env"
    set -a
    source "$ROOT_DIR/.env"
    set +a
fi

echo "[1/2] Starting FastAPI Backend..."

cd "$ROOT_DIR/backend"

"$PYTHON" -m uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 &

BACKEND_PID=$!

sleep 3

echo "[2/2] Starting Streamlit Frontend..."

cd "$ROOT_DIR/frontend"

"$PYTHON" -m streamlit run app.py \
    --server.port 8501 \
    --server.address localhost &

FRONTEND_PID=$!

echo ""
echo "============================================"
echo "  Application Running:"
echo "  Backend  : http://localhost:8000"
echo "  Frontend : http://localhost:8501"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop all services."

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo "Stopped."' EXIT

wait