@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\.."

set BASE_CONFIG=configs\two_hosts_config.json
set ACTIVE_CONFIG=logs\active_two_hosts_config.json

call :choose_profile
call :prepare_config

if not exist "logs\two_hosts" mkdir "logs\two_hosts"

echo Running benchmark with profile !PROFILE! ...
python benchmark_unified.py --config "!ACTIVE_CONFIG!" --leader-host 192.168.1.2 --leader-port 60051 --log-dir logs\two_hosts --output-dir logs\two_hosts

del /q "!ACTIVE_CONFIG!" >nul 2>&1
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