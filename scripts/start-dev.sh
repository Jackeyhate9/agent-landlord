#!/usr/bin/env sh
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_ROOT"
[ -f .env ] || cp .env.example .env
python -m pip install -e '.[test]'
npm --prefix apps/web install
export POSTGRES_URL=""
export REDIS_URL=""
export VITE_API_URL="http://localhost:8080"
export VITE_WS_URL="ws://localhost:8080"
python -m uvicorn server.app.main:app --reload --port 8080 &
API_PID=$!
npm --prefix apps/web run dev -- --host 0.0.0.0 &
WEB_PID=$!
trap 'kill "$API_PID" "$WEB_PID" 2>/dev/null || true' INT TERM EXIT
wait

