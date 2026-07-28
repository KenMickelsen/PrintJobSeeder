#!/usr/bin/env bash
# Start-PrintJobSeeder.sh — Launch the Print Job Seeder in the background (Mac/Linux)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "         Print Job Seeder - Vasion Output"
echo "=================================================="
echo

PID_FILE="printjobseeder.pid"
LOG_FILE="printjobseeder.log"
PORT=5757
URL="http://127.0.0.1:${PORT}"

# Check if Python is installed
if ! command -v python3 &>/dev/null; then
  echo "ERROR: Python 3 is not installed or not in PATH."
  echo "Please install Python from https://www.python.org/downloads/"
  exit 1
fi

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment."
    exit 1
  fi
  echo "Virtual environment created."
  echo
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if ! python3 -c "import flask; import requests; import requests_toolbelt; import reportlab" &>/dev/null; then
  echo "Installing dependencies..."
  pip3 install -r requirements.txt
  if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies."
    exit 1
  fi
  echo "Dependencies installed."
  echo
fi

_port_listening() {
  python3 -c "import socket; s=socket.socket(); s.settimeout(0.5); s.connect(('127.0.0.1', $PORT)); s.close()" 2>/dev/null
}

# Already running via pid file
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Print Job Seeder is already running (PID $OLD_PID) on $URL"
    open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null || true
    exit 0
  fi
  rm -f "$PID_FILE"
fi

# Port already in use (e.g. started another way)
if _port_listening; then
  echo "Print Job Seeder is already listening on port $PORT."
  open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null || true
  exit 0
fi

# Clean up leftover processes from older foreground start scripts
EXISTING=$(pgrep -f "python.*app\.py" 2>/dev/null || true)
if [ -n "$EXISTING" ]; then
  echo "Stopping leftover instance(s) (PID: $EXISTING)..."
  kill $EXISTING 2>/dev/null || true
  sleep 1
fi

echo "Starting Print Job Seeder on $URL..."
nohup python3 app.py --no-browser >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
PID=$(cat "$PID_FILE")

# Wait until the server accepts connections
READY=0
for _ in $(seq 1 40); do
  if _port_listening; then
    READY=1
    break
  fi
  # Bail early if the process died
  if ! kill -0 "$PID" 2>/dev/null; then
    break
  fi
  sleep 0.25
done

if [ "$READY" -ne 1 ]; then
  echo "ERROR: Server failed to start. Check $LOG_FILE for details."
  rm -f "$PID_FILE"
  exit 1
fi

open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null || true

echo
echo "Print Job Seeder is running in the background (PID $PID)."
echo "  URL:  $URL"
echo "  Log:  $LOG_FILE"
echo "  Stop: ./Stop-PrintJobSeeder.sh"
echo "=================================================="
