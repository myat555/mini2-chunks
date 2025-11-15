@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\.."

set BASE_CONFIG=configs\two_hosts_config.json
set ACTIVE_CONFIG=logs\active_two_hosts_config.json

call :choose_profile
call :ensure_python
call :ensure_proto
call :prepare_config

if not exist "logs" mkdir "logs"
if not exist "logs\two_hosts" mkdir "logs\two_hosts"

echo.
echo Using profile: !PROFILE!
echo Active config: !ACTIVE_CONFIG!
echo.

call :launch_node "Node A (Leader)" A logs\two_hosts\windows_192.168.1.2_node_a.log
call :launch_node "Node B (Team Leader)" B logs\two_hosts\windows_192.168.1.2_node_b.log
call :launch_node "Node D (Worker)" D logs\two_hosts\windows_192.168.1.2_node_d.log

echo ============================================================
echo Windows-side processes started (A, B, D). Press any key to stop.
echo ============================================================
pause >nul

echo Stopping Windows-side processes...
for %%W in ("Node A (Leader)" "Node B (Team Leader)" "Node D (Worker)") do (
    taskkill /fi "WINDOWTITLE eq %%~W" /f >nul 2>&1
)

if exist "!ACTIVE_CONFIG!" del /q "!ACTIVE_CONFIG!" >nul 2>&1
echo Done.
exit /b 0

:choose_profile
echo Choose a strategy profile:
echo   [1] Baseline  - round_robin / blocking / fixed / strict
echo   [2] Parallel  - parallel    / async    / adaptive / strict
echo   [3] Balanced  - capacity    / async    / query_based / weighted
set /p _choice=Select profile [1-3, default 1]: 
if "%_choice%"=="" set _choice=1
if "%_choice%"=="1" (
    call :set_profile baseline round_robin false fixed strict 500
) else if "%_choice%"=="2" (
    call :set_profile parallel parallel true adaptive strict 500
) else if "%_choice%"=="3" (
    call :set_profile balanced capacity true query_based weighted 500
) else (
    echo Invalid choice. Try again.
    goto :choose_profile
)
goto :eof

:set_profile
set PROFILE=%1
set FORWARDING=%2
set ASYNC=%3
set CHUNKING=%4
set FAIRNESS=%5
set CHUNK_SIZE=%6
goto :eof

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