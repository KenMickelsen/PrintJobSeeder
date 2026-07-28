#!/usr/bin/env bash
# Stop-PrintJobSeeder.sh — Stop the Print Job Seeder (Mac/Linux)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "        Stopping Print Job Seeder"
echo "=================================================="
echo

PID_FILE="printjobseeder.pid"

if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null
    # Wait briefly for clean shutdown
    for _ in $(seq 1 20); do
      if ! kill -0 "$PID" 2>/dev/null; then
        break
      fi
      sleep 0.1
    done
    if kill -0 "$PID" 2>/dev/null; then
      kill -9 "$PID" 2>/dev/null || true
    fi
    echo "Print Job Seeder stopped (PID $PID)."
  else
    echo "Print Job Seeder is not running (stale PID file)."
  fi
  rm -f "$PID_FILE"
else
  # Fallback: kill by matching process (older foreground starts)
  if pkill -f "python.*app\.py" 2>/dev/null; then
    echo "Print Job Seeder stopped."
  else
    echo "No Print Job Seeder instances found running."
  fi
fi
