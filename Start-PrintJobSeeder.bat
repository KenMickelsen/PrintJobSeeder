@echo off
title Print Job Seeder - Vasion Output
echo ==================================================
echo          Print Job Seeder - Vasion Output
echo ==================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Kill any existing Python processes running app.py to avoid conflicts
echo Checking for existing instances...
powershell -Command "& { $procs = Get-WmiObject Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*app.py*' }; if ($procs) { $procs | ForEach-Object { Write-Host \"Stopping existing instance (PID: $($_.ProcessId))...\"; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } } }"
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Check if virtual environment exists, create if not
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created.
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed (including reportlab)
python -c "import flask; import requests; import requests_toolbelt; import reportlab" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
    echo Dependencies installed.
    echo.
)

echo.
echo Starting Print Job Seeder...
echo The web interface will open automatically in your browser.
echo.
echo Press Ctrl+C to stop the server.
echo ==================================================
echo.

python app.py

pause
