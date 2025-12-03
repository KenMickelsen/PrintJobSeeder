@echo off
title Stopping Print Job Seeder
echo ==================================================
echo        Stopping Print Job Seeder
echo ==================================================
echo.

REM Kill all Python processes running app.py
set FOUND=0
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /fo list 2^>nul ^| find "PID:"') do (
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | find "app.py" >nul
    if not errorlevel 1 (
        echo Stopping Print Job Seeder instance (PID: %%a)...
        taskkill /PID %%a /F >nul 2>&1
        set FOUND=1
    )
)

if "%FOUND%"=="0" (
    echo No Print Job Seeder instances found running.
) else (
    echo.
    echo Print Job Seeder stopped successfully.
)

echo.
pause
