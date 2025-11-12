@echo off
echo Starting Windows processes for 2-host leader-queue test...
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python and try again.
    pause
    exit /b 1
)

:: Check if config file exists
if not exist "../two_hosts_config.json" (
    echo Error: two_hosts_config.json not found.
    pause
    exit /b 1
)

:: Check if proto files are generated
if not exist "../overlay_pb2.py" (
    echo Generating proto files...
    cd ..
    python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. overlay.proto
    cd scripts
    if errorlevel 1 (
        echo Error: Failed to generate proto files.
        pause
        exit /b 1
    )
)

echo Starting Process A (Leader) on port 50051...
start "Process A - Leader" python ..\node.py ..\two_hosts_config.json A
timeout /t 2 /nobreak >nul

echo Starting Process B (Team Leader) on port 50052...
start "Process B - Team Leader" python ..\node.py ..\two_hosts_config.json B
timeout /t 2 /nobreak >nul

echo Starting Process D (Worker) on port 50054...
start "Process D - Worker" python ..\node.py ..\two_hosts_config.json D
timeout /t 2 /nobreak >nul

echo.
echo All Windows processes started:
echo   - Process A (Leader): port 50051
echo   - Process B (Team Leader): port 50052  
echo   - Process D (Worker): port 50054
echo.
echo Press any key to stop all processes...
pause >nul

echo Stopping all Windows processes...
taskkill /fi "windowtitle eq Process A - Leader" /f >nul 2>&1
taskkill /fi "windowtitle eq Process B - Team Leader" /f >nul 2>&1
taskkill /fi "windowtitle eq Process D - Worker" /f >nul 2>&1

echo All processes stopped.
