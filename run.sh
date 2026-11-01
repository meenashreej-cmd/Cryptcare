#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "========================================================"
echo "             Starting CryptCare System                  "
echo "========================================================"

# Determine Python binary
if [ -f "$DIR/venv/Scripts/python.exe" ]; then
    PYTHON="$DIR/venv/Scripts/python.exe"
elif [ -f "$DIR/venv/bin/python" ]; then
    PYTHON="$DIR/venv/bin/python"
else
    PYTHON="python3"
fi

# Frontend node_modules check
if [ ! -d "$DIR/cryptcare-ai-frontend/node_modules" ]; then
    echo "[INFO] Installing frontend dependencies..."
    (cd "$DIR/cryptcare-ai-frontend" && npm install)
fi

echo "[1/2] Starting FastAPI Backend on http://127.0.0.1:8000..."
$PYTHON -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "[2/2] Starting Vite Frontend on http://localhost:5173..."
(cd "$DIR/cryptcare-ai-frontend" && npm run dev) &
FRONTEND_PID=$!

cleanup() {
    echo ""
    echo "Shutting down CryptCare servers..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM

echo ""
echo "========================================================"
echo "  CryptCare is running:"
echo "   - Frontend: http://localhost:5173"
echo "   - Backend:  http://127.0.0.1:8000"
echo "   - API Docs: http://127.0.0.1:8000/docs"
echo "========================================================"
echo "Press Ctrl+C to terminate both servers."

wait

