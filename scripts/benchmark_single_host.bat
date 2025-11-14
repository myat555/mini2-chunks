@echo off
cd /d %~dp0\..

set PROFILE=%1
if "%PROFILE%"=="" set PROFILE=baseline

if "%PROFILE%"=="baseline" (
    set CONFIG=one_host_config_baseline.json
) else if "%PROFILE%"=="parallel" (
    set CONFIG=one_host_config_parallel.json
) else if "%PROFILE%"=="balanced" (
    set CONFIG=one_host_config_balanced.json
) else (
    echo Error: Unknown profile "%PROFILE%". Use: baseline, parallel, or balanced
    exit /b 1
)

echo Using strategy profile: %PROFILE%
python benchmark_unified.py --config %CONFIG% --leader-host 127.0.0.1 --leader-port 60051 --log-dir logs\windows --output-dir logs\windows

