@echo off
setlocal

set HOST=192.168.1.2
set PORT=60051
set REQUESTS=200
set CONCURRENCY=20

if not "%1"=="" set HOST=%1
if not "%2"=="" set PORT=%2
if not "%3"=="" set REQUESTS=%3
if not "%4"=="" set CONCURRENCY=%4

cd /d "%~dp0\.."

python scripts\benchmark_two_hosts.py --host %HOST% --port %PORT% --requests %REQUESTS% --concurrency %CONCURRENCY%

exit /b %errorlevel%

