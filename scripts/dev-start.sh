#!/usr/bin/env bash
# Starts plan-engine (port 8000) and frontend (port 5173) in the background,
# skipping any server whose port is already in use. Logs go to logs/*.log.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"

port_in_use() {
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && exec 3>&- 3<&-
}

if port_in_use 8000; then
  echo "plan-engine: port 8000 already in use, skipping"
else
  echo "plan-engine: starting on port 8000 (log: $LOG_DIR/plan-engine.log)"
  (
    cd "$REPO_ROOT/plan-engine"
    nohup .venv/bin/uvicorn app.main:app --reload --port 8000 \
      > "$LOG_DIR/plan-engine.log" 2>&1 &
    disown
  )
fi

if port_in_use 5173; then
  echo "frontend: port 5173 already in use, skipping"
else
  echo "frontend: starting on port 5173 (log: $LOG_DIR/frontend.log)"
  (
    cd "$REPO_ROOT/frontend"
    nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    disown
  )
fi
