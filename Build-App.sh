#!/bin/bash
# Build-App.sh — Build PrinterLogic Output Demo as a macOS .app bundle
#
# Prerequisites:
#   - Python 3.8+ installed (python3 / python3.x in PATH)
#   - Run from the repo root, or double-click in Finder (it cd's here first)
#
# Output:
#   dist/PrinterLogic Output Demo.app
#
# Distribution tips:
#   1. Zip the .app for sharing:
#        ditto -c -k --keepParent "dist/PrinterLogic Output Demo.app" \
#              "PrinterLogicOutputDemo.zip"
#   2. For Gatekeeper-clean distribution, sign + notarise:
#        codesign --deep --force --options runtime \
#                 -s "Developer ID Application: Your Name (TEAMID)" \
#                 "dist/PrinterLogic Output Demo.app"

set -e
cd "$(dirname "$0")"

echo "=================================================="
echo "  Building PrinterLogic Output Demo (.app)"
echo "=================================================="
echo ""

# Use project venv if available, otherwise fall back to system Python 3.
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "No venv found; using system Python 3."
    # Try to create a venv so dependencies stay isolated.
    python3 -m venv venv
    source venv/bin/activate
fi

echo ""
echo "Installing runtime dependencies..."
pip install -r requirements.txt

echo ""
echo "Installing build dependencies..."
pip install -r requirements-dev.txt

echo ""
echo "Running PyInstaller..."
pyinstaller --noconfirm --clean PrinterLogicOutputDemo-Mac.spec

echo ""
echo "=================================================="
echo " Build complete."
echo " App bundle: dist/PrinterLogic Output Demo.app"
echo ""
echo " To run directly:"
echo "   open \"dist/PrinterLogic Output Demo.app\""
echo ""
echo " To allow on another Mac (unsigned):"
echo "   Right-click the app → Open → Open"
echo "=================================================="
