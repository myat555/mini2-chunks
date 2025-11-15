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
set NUM_REQUESTS=400
set CONCURRENCY=20

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
    echo Usage: %~nx0 [baseline^|parallel^|weighted^|hybrid] [num_requests] [concurrency]
    echo   baseline: round_robin / blocking / fixed / strict (default)
    echo   parallel: parallel / async / adaptive / strict
    echo   weighted: round_robin / blocking / fixed / weighted
    echo   hybrid: round_robin / blocking / fixed / hybrid
    echo.
    echo   num_requests: Number of requests (default: 400)
    echo   concurrency: Concurrent requests (default: 20)
    exit /b 1
)

if not "%2"=="" set NUM_REQUESTS=%2
if not "%3"=="" set CONCURRENCY=%3

call :prepare_config

if not exist "logs\windows" mkdir "logs\windows"

echo Running benchmark with profile !PROFILE! ...
echo Requests: !NUM_REQUESTS!, Concurrency: !CONCURRENCY!
python benchmark_unified.py --config "!ACTIVE_CONFIG!" --leader-host 127.0.0.1 --leader-port 60051 --num-requests !NUM_REQUESTS! --concurrency !CONCURRENCY! --log-dir logs\windows --output-dir logs\windows

del /q "!ACTIVE_CONFIG!" >nul 2>&1
exit /b 0

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
