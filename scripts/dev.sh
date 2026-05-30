#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required to auto-start RabbitMQ. Start RabbitMQ manually or install Docker Desktop."
  exit 1
fi

echo "Starting RabbitMQ..."
docker compose up -d rabbitmq

echo "Starting FastAPI backend on http://127.0.0.1:8000 ..."
RABBITMQ_ENABLED=true \
RABBITMQ_URL="${RABBITMQ_URL:-amqp://guest:guest@localhost:5672/%2F}" \
backend/venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cleanup() {
  echo
  echo "Stopping backend..."
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting Vite frontend on http://127.0.0.1:5173 ..."
cd "$ROOT_DIR/frontend"
npm run dev -- --host 127.0.0.1 --port 5173
