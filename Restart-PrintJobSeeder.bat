@echo off
title Restarting Print Job Seeder
echo ==================================================
echo       Restarting Print Job Seeder
echo ==================================================
echo.

REM Kill ALL Python processes to ensure clean restart
echo Stopping all Python processes...
taskkill /IM python.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

REM Clear the request log for fresh debugging
echo Clearing request log...
del "%~dp0request_log.txt" >nul 2>&1

REM Change to script directory
cd /d "%~dp0"

REM Activate virtual environment and start
echo Starting Print Job Seeder...
echo.
call venv\Scripts\activate.bat
python app.py

pause
