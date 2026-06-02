#!/usr/bin/env bash
# Stop-ERPDemo.sh — Stop the Apex Industrial ERP Demo (Mac/Linux)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f erp_demo.pid ]; then
  PID=$(cat erp_demo.pid)
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "ERP Demo stopped (PID $PID)."
  else
    echo "ERP Demo is not running (stale PID file)."
  fi
  rm -f erp_demo.pid
else
  # Fallback: kill by matching process
  pkill -f "app_erp.py" 2>/dev/null && echo "ERP Demo stopped." || echo "ERP Demo was not running."
fi
