#!/bin/bash
echo "=================================================="
echo "         Print Job Seeder - Vasion Output"
echo "=================================================="
echo

# Change to script directory
cd "$(dirname "$0")"

# Kill any existing Python processes running app.py to avoid conflicts
echo "Checking for existing instances..."
EXISTING=$(pgrep -f "python.*app.py" 2>/dev/null)
if [ -n "$EXISTING" ]; then
    echo "Stopping existing instance(s) (PID: $EXISTING)..."
    kill $EXISTING 2>/dev/null
fi
echo

# Check if Python is installed
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH."
    echo "Please install Python from https://www.python.org/downloads/"
    exit 1
fi

# Check if virtual environment exists, create if not
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

# Check if dependencies are installed
python3 -c "import flask; import requests; import requests_toolbelt; import reportlab" &>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies."
        exit 1
    fi
    echo "Dependencies installed."
    echo
fi

echo
echo "Starting Print Job Seeder..."
echo "The web interface will open automatically in your browser."
echo
echo "Press Ctrl+C to stop the server."
echo "=================================================="
echo

python3 app.py
