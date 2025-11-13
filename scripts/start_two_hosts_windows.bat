@echo off
setlocal

echo Starting Windows-side processes for two-host configuration...
echo This will start: A (Leader), B (Team Leader), D (Worker) on 192.168.1.2
echo.

set CONFIG=..\two_hosts_config.json

python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found.
    exit /b 1
)

if not exist "%CONFIG%" (
    echo Error: two_hosts_config.json not found.
    exit /b 1
)

:: Create logs directory structure
if not exist "..\logs" mkdir ..\logs
if not exist "..\logs\windows" mkdir ..\logs\windows

if not exist "..\overlay_pb2.py" (
    echo Generating proto stubs...
    cd ..
    python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. overlay.proto
    cd scripts
    if errorlevel 1 (
        echo Failed to generate proto files.
        exit /b 1
    )
)

echo Starting Process A (Leader) on 192.168.1.2:60051...
start "Node A (Leader)" cmd /c "cd /d .. && python -u node.py %CONFIG% A > logs\windows\node_a.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process B (Team Leader) on 192.168.1.2:60052...
start "Node B (Team Leader)" cmd /c "cd /d .. && python -u node.py %CONFIG% B > logs\windows\node_b.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process D (Worker) on 192.168.1.2:60054...
start "Node D (Worker)" cmd /c "cd /d .. && python -u node.py %CONFIG% D > logs\windows\node_d.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo.
echo Windows-side processes started: A, B, D
echo Make sure macOS-side processes (C, E, F) are started on 192.168.1.1
echo Close this window or press any key to stop Windows processes...
pause >nul

echo Stopping Windows-side processes...
taskkill /fi "WINDOWTITLE eq Node A (Leader)" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node B (Team Leader)" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node D (Worker)" /f >nul 2>&1

echo Windows processes stopped.

