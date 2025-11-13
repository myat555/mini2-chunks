@echo off
setlocal

echo Starting all single-host processes on Windows...
echo.

set CONFIG=..\one_host_config.json

python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found.
    exit /b 1
)

if not exist "%CONFIG%" (
    echo Error: one_host_config.json not found.
    exit /b 1
)

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

:: Create logs directory structure
if not exist "..\logs" mkdir ..\logs
if not exist "..\logs\windows" mkdir ..\logs\windows

echo Starting Process A (Leader)...
start "Node A" cmd /c "cd /d .. && python -u node.py %CONFIG% A > logs\windows\node_a.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process B (Team Leader)...
start "Node B" cmd /c "cd /d .. && python -u node.py %CONFIG% B > logs\windows\node_b.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process C (Worker)...
start "Node C" cmd /c "cd /d .. && python -u node.py %CONFIG% C > logs\windows\node_c.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process D (Worker)...
start "Node D" cmd /c "cd /d .. && python -u node.py %CONFIG% D > logs\windows\node_d.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process E (Team Leader)...
start "Node E" cmd /c "cd /d .. && python -u node.py %CONFIG% E > logs\windows\node_e.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo Starting Process F (Worker)...
start "Node F" cmd /c "cd /d .. && python -u node.py %CONFIG% F > logs\windows\node_f.log 2>&1 && pause"
timeout /t 2 /nobreak >nul

echo.
echo All single-host processes started (A-F on localhost).
echo Close this window or press any key to stop them...
pause >nul

echo Stopping all processes...
taskkill /fi "WINDOWTITLE eq Node A" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node B" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node C" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node D" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node E" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Node F" /f >nul 2>&1

echo All processes stopped.

