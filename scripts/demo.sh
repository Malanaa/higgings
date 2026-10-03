#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
MODE="${1:-synthetic}"
if [[ ! -x .venv/bin/neurostreamlab || ! -d frontend/node_modules ]]; then
  echo "Run ./scripts/bootstrap.sh first."
  exit 1
fi
cleanup() {
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap "exit 130" INT TERM
.venv/bin/neurostreamlab server --mode "$MODE" &
BACKEND_PID=$!
npm run dev --prefix frontend -- --port 5173 --strictPort &
FRONTEND_PID=$!
echo "NeuroStreamLab: http://127.0.0.1:5173 | API http://127.0.0.1:8000/docs"
echo "Source mode: $MODE. Ctrl-C shuts down both processes."
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do sleep 1; done
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  wait "$BACKEND_PID"
else
  wait "$FRONTEND_PID"
fi
