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

echo Starting Process A (Leader)...
start "Node A" python -u ..\node.py %CONFIG% A
timeout /t 2 /nobreak >nul

echo Starting Process B (Team Leader)...
start "Node B" python -u ..\node.py %CONFIG% B
timeout /t 2 /nobreak >nul

echo Starting Process C (Worker)...
start "Node C" python -u ..\node.py %CONFIG% C
timeout /t 2 /nobreak >nul

echo Starting Process D (Worker)...
start "Node D" python -u ..\node.py %CONFIG% D
timeout /t 2 /nobreak >nul

echo Starting Process E (Team Leader)...
start "Node E" python -u ..\node.py %CONFIG% E
timeout /t 2 /nobreak >nul

echo Starting Process F (Worker)...
start "Node F" python -u ..\node.py %CONFIG% F
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

