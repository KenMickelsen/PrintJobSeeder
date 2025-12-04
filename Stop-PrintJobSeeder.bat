@echo off
title Stopping Print Job Seeder
echo ==================================================
echo        Stopping Print Job Seeder
echo ==================================================
echo.

REM Use PowerShell for more reliable process detection and killing
powershell -Command "& { $procs = Get-WmiObject Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*app.py*' }; if ($procs) { $procs | ForEach-Object { Write-Host \"Stopping Print Job Seeder (PID: $($_.ProcessId))...\"; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Write-Host ''; Write-Host 'Print Job Seeder stopped successfully.' } else { Write-Host 'No Print Job Seeder instances found running.' } }"

echo.
echo Press any key to close this window...
pause >nul
