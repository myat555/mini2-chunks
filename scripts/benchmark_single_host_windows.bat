@echo off
setlocal

set REQUESTS=200
set CONCURRENCY=20

if not "%1"=="" set REQUESTS=%1
if not "%2"=="" set CONCURRENCY=%2

cd /d "%~dp0\.."

set CONFIG=one_host_config.json

echo Starting single-host servers...
echo.

:: Create logs directory structure
if not exist "logs" mkdir logs
if not exist "logs\windows" mkdir logs\windows

:: Check and generate proto if needed
if not exist "overlay_pb2.py" (
    echo Generating proto stubs...
    python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. overlay.proto
)

:: Start all servers with logging to logs/windows folder
echo Starting Process A (Leader)...
start "Node A" cmd /c "python -u node.py %CONFIG% A > logs\windows\node_a.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process B (Team Leader)...
start "Node B" cmd /c "python -u node.py %CONFIG% B > logs\windows\node_b.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process C (Worker)...
start "Node C" cmd /c "python -u node.py %CONFIG% C > logs\windows\node_c.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process D (Worker)...
start "Node D" cmd /c "python -u node.py %CONFIG% D > logs\windows\node_d.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process E (Team Leader)...
start "Node E" cmd /c "python -u node.py %CONFIG% E > logs\windows\node_e.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process F (Worker)...
start "Node F" cmd /c "python -u node.py %CONFIG% F > logs\windows\node_f.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Waiting for servers to be ready...
timeout /t 10 /nobreak >nul

echo Checking leader readiness...
python "scripts\wait_for_leader.py" 127.0.0.1:60051 30
if errorlevel 1 (
    echo.
    echo ERROR: Leader did not become ready.
    echo Check the "Node A" window for error messages.
    echo.
    echo Stopping any started processes...
    taskkill /fi "WINDOWTITLE eq Node A" /f >nul 2>&1
    taskkill /fi "WINDOWTITLE eq Node B" /f >nul 2>&1
    taskkill /fi "WINDOWTITLE eq Node C" /f >nul 2>&1
    taskkill /fi "WINDOWTITLE eq Node D" /f >nul 2>&1
    taskkill /fi "WINDOWTITLE eq Node E" /f >nul 2>&1
    taskkill /fi "WINDOWTITLE eq Node F" /f >nul 2>&1
    exit /b 1
)

echo.
echo Running single-host benchmark...
echo.

python benchmark.py 127.0.0.1 60051 %REQUESTS% %CONCURRENCY% logs\windows

echo.
echo Stopping servers...
taskkill /fi "WINDOWTITLE eq Node A" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node B" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node C" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node D" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node E" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node F" /f >nul 2>&1

echo.
echo Benchmark complete.
echo Results saved to logs\windows\benchmark_results.json
echo Process logs saved to logs\windows\node_*.log

