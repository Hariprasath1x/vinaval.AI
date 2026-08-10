#!/bin/bash
echo "============================================"
echo "  Vinaval AI — Starting Backend"
echo "============================================"
echo ""

cd "$(dirname "$0")/backend"
venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo ""
echo "============================================"
echo "  Backend Running:"
echo "  http://localhost:8000"
echo "============================================"
echo ""
echo "👉 TO START THE FRONTEND:"
echo "   Open a new terminal, and run:"
echo "   cd frontend"
echo "   npm install"
echo "   npm run dev"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop the backend."

trap "kill $BACKEND_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
