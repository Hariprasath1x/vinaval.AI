#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "============================================"
echo "  🚀 Starting Vinaval AI Platform"
echo "============================================"

# Kill any orphaned processes on port 8000 or 5173
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true

# Start backend
cd "$DIR/backend"
"$DIR/backend/venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!
echo "  ✓ Backend started on http://127.0.0.1:8000 (PID: $BACKEND_PID)"

# Start frontend
cd "$DIR/frontend"
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!
echo "  ✓ Frontend started on http://127.0.0.1:5173 (PID: $FRONTEND_PID)"

echo ""
echo "============================================"
echo "  🎓 Vinaval AI is Ready for Testing!"
echo "  Frontend UI : http://localhost:5173"
echo "  Backend API : http://localhost:8000/docs"
echo "============================================"
echo "  Press Ctrl+C to stop all servers."
echo ""

cleanup() {
    echo ""
    echo "Stopping all servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "All servers stopped."
    exit 0
}

trap cleanup INT TERM EXIT
wait
