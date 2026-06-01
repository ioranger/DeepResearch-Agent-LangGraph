#!/usr/bin/env bash
# One-shot local development launcher.
# Usage: ./scripts/dev.sh [--no-frontend] [--no-backend]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_BACKEND=1
RUN_FRONTEND=1

for arg in "$@"; do
  case "$arg" in
    --no-backend)  RUN_BACKEND=0 ;;
    --no-frontend) RUN_FRONTEND=0 ;;
    -h|--help)
      sed -n '2,4p' "$0"
      exit 0
      ;;
  esac
done

ensure_env_file() {
  local example="$ROOT_DIR/backend/.env.example"
  local target="$ROOT_DIR/backend/.env"
  if [[ ! -f "$target" && -f "$example" ]]; then
    echo "==> Creating backend/.env from .env.example"
    cp "$example" "$target"
    echo "    Edit backend/.env to set LLM_PROVIDER / LLM_MODEL_ID / LLM_BASE_URL"
    echo "    (DuckDuckGo default search needs no extra keys.)"
  fi
}

start_backend() {
  ensure_env_file
  echo "==> Syncing backend (uv)"
  (cd "$ROOT_DIR/backend" && uv sync)
  echo "==> Starting backend on http://localhost:${PORT:-8000}"
  (cd "$ROOT_DIR/backend" && uv run uvicorn main:app --reload --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}")
}

start_frontend() {
  echo "==> Installing frontend deps (npm)"
  (cd "$ROOT_DIR/frontend" && [[ -d node_modules ]] || npm install)
  echo "==> Starting frontend on http://localhost:5173"
  (cd "$ROOT_DIR/frontend" && npm run dev)
}

pids=()
cleanup() {
  for pid in "${pids[@]:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

if [[ "$RUN_BACKEND" -eq 1 && "$RUN_FRONTEND" -eq 1 ]]; then
  start_backend  &
  pids+=($!)
  start_frontend
elif [[ "$RUN_BACKEND" -eq 1 ]]; then
  start_backend
elif [[ "$RUN_FRONTEND" -eq 1 ]]; then
  start_frontend
else
  echo "Nothing to do. Use --no-backend or --no-frontend to disable a side." >&2
  exit 1
fi
