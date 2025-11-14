@echo off
setlocal

cd /d "%~dp0\.."

echo Viewing two-host process logs...
echo.

python scripts\view_two_hosts_logs.py

pause

