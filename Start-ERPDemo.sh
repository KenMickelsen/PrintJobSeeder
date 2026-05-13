#!/usr/bin/env bash
# Start-ERPDemo.sh — Launch the Apex Industrial ERP Demo (Mac/Linux)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "         Apex Industrial ERP Demo"
echo "=================================================="
echo

# Check if Python 3 is installed
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

# Check if already running
if lsof -i :5758 -sTCP:LISTEN -t &>/dev/null; then
  echo "ERP Demo is already running on port 5758."
  open "http://localhost:5758" 2>/dev/null || xdg-open "http://localhost:5758" 2>/dev/null || true
  exit 0
fi

echo "Starting Apex Industrial ERP Demo on http://localhost:5758..."
echo "Press Ctrl+C to stop the server."
echo "=================================================="
echo

python3 app_erp.py

