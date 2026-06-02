@echo off
echo Stopping Apex Industrial ERP Demo...

REM Kill any Python process running app_erp.py
for /f "tokens=2" %%i in ('tasklist /fi "IMAGENAME eq pythonw.exe" /fo list ^| find "PID:"') do (
    wmic process %%i get CommandLine 2>nul | find "app_erp.py" >nul 2>&1
    if not errorlevel 1 (
        taskkill /PID %%i /F >nul 2>&1
    )
)

REM Also try python.exe
for /f "tokens=2" %%i in ('tasklist /fi "IMAGENAME eq python.exe" /fo list ^| find "PID:"') do (
    wmic process %%i get CommandLine 2>nul | find "app_erp.py" >nul 2>&1
    if not errorlevel 1 (
        taskkill /PID %%i /F >nul 2>&1
    )
)

echo ERP Demo stopped.
