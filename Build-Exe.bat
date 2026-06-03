@echo off
title Build PrinterLogic Output Demo EXE
echo ==================================================
echo  Building PrinterLogic Output Demo (single EXE)
echo ==================================================
echo.

cd /d "%~dp0"

REM Use the project venv if present, otherwise system Python.
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo No venv found; using system Python.
)

echo.
echo Ensuring build dependencies are installed...
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Running PyInstaller...
pyinstaller --noconfirm --clean PrinterLogicOutputDemo.spec
if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo  Build complete.
echo  Executable: dist\PrinterLogicOutputDemo.exe
echo ==================================================
echo.
pause
