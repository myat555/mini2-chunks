@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\.."

set BASE_CONFIG=configs\one_host_config.json
set ACTIVE_CONFIG=logs\active_one_host_config.json

REM Parse command-line arguments
set PROFILE=baseline
set FORWARDING=round_robin
set ASYNC=false
set CHUNKING=fixed
set FAIRNESS=strict
set CHUNK_SIZE=200

if "%1"=="parallel" (
    set PROFILE=parallel
    set FORWARDING=parallel
    set ASYNC=true
    set CHUNKING=adaptive
    set FAIRNESS=strict
) else if "%1"=="weighted" (
    set PROFILE=weighted
    set FORWARDING=round_robin
    set ASYNC=false
    set CHUNKING=fixed
    set FAIRNESS=weighted
) else if "%1"=="hybrid" (
    set PROFILE=hybrid
    set FORWARDING=round_robin
    set ASYNC=false
    set CHUNKING=fixed
    set FAIRNESS=hybrid
) else if "%1"=="" (
    REM Default to baseline
) else (
    echo Usage: %~nx0 [baseline^|parallel^|weighted^|hybrid]
    echo   baseline: round_robin / blocking / fixed / strict (default)
    echo   parallel: parallel / async / adaptive / strict
    echo   weighted: round_robin / blocking / fixed / weighted
    echo   hybrid: round_robin / blocking / fixed / hybrid
    exit /b 1
)

call :ensure_python
call :ensure_proto
call :prepare_config

if not exist "logs" mkdir "logs"
if not exist "logs\windows" mkdir "logs\windows"

echo.
echo Using profile: !PROFILE!
echo Active config: !ACTIVE_CONFIG!
echo.

call :launch_node "Node A (Leader)" A logs\windows\node_a.log
call :launch_node "Node B (Team Leader)" B logs\windows\node_b.log
call :launch_node "Node C (Worker)" C logs\windows\node_c.log
call :launch_node "Node D (Worker)" D logs\windows\node_d.log
call :launch_node "Node E (Team Leader)" E logs\windows\node_e.log
call :launch_node "Node F (Worker)" F logs\windows\node_f.log

echo ============================================================
echo All single-host processes started (A-F on localhost)
echo Press any key to stop them...
echo ============================================================
pause >nul

echo Stopping all processes...
for %%W in ("Node A (Leader)" "Node B (Team Leader)" "Node C (Worker)" "Node D (Worker)" "Node E (Team Leader)" "Node F (Worker)") do (
    taskkill /fi "WINDOWTITLE eq %%~W" /f >nul 2>&1
)

if exist "!ACTIVE_CONFIG!" del /q "!ACTIVE_CONFIG!" >nul 2>&1
echo Done.
exit /b 0

:ensure_python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is required on PATH.
    exit /b 1
)
goto :eof

:ensure_proto
if exist "overlay_pb2.py" goto :eof
echo Generating proto stubs...
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. overlay.proto || (
    echo Failed to generate gRPC stubs.
    exit /b 1
)
goto :eof

:prepare_config
if not exist "!BASE_CONFIG!" (
    echo Error: !BASE_CONFIG! not found.
    exit /b 1
)
if not exist "logs" mkdir "logs"
python -c "import json,sys; data=json.load(open(sys.argv[1])); data.setdefault('strategies', {}); data['strategies']['forwarding_strategy']=sys.argv[3]; data['strategies']['async_forwarding']=sys.argv[4].lower()=='true'; data['strategies']['chunking_strategy']=sys.argv[5]; data['strategies']['fairness_strategy']=sys.argv[6]; data['strategies']['chunk_size']=int(sys.argv[7]); json.dump(data, open(sys.argv[2],'w'), indent=2)" "!BASE_CONFIG!" "!ACTIVE_CONFIG!" "!FORWARDING!" "!ASYNC!" "!CHUNKING!" "!FAIRNESS!" "!CHUNK_SIZE!" || (
    echo Failed to build active config.
    exit /b 1
)
goto :eof

:launch_node
echo Starting %2...
start "%~1" cmd /c "cd /d %~dp0\.. && python -u node.py "!ACTIVE_CONFIG!" %2 > %3 2>&1 && pause"
timeout /t 2 /nobreak >nul
goto :eof
