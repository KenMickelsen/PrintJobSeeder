#!/bin/bash
echo "=================================================="
echo "        Stopping Print Job Seeder"
echo "=================================================="
echo

EXISTING=$(pgrep -f "python.*app.py" 2>/dev/null)
if [ -n "$EXISTING" ]; then
    echo "Stopping Print Job Seeder (PID: $EXISTING)..."
    kill $EXISTING 2>/dev/null
    echo
    echo "Print Job Seeder stopped successfully."
else
    echo "No Print Job Seeder instances found running."
fi
