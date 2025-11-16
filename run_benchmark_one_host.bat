@echo off
REM Benchmark script for single-host setup (Windows)
REM Usage: run_benchmark_one_host.bat [--num-requests N] [--concurrency N]

set DEFAULT_REQUESTS=100
set DEFAULT_CONCURRENCY=10
set CONFIG_FILE=configs\one_host_config.json
set LEADER_HOST=127.0.0.1
set LEADER_PORT=60051
set LOG_DIR=logs\windows
set OUTPUT_DIR=logs\windows

REM Parse optional arguments
set NUM_REQUESTS=%DEFAULT_REQUESTS%
set CONCURRENCY=%DEFAULT_CONCURRENCY%

if "%1"=="--num-requests" (
    set NUM_REQUESTS=%2
    shift
    shift
)
if "%1"=="--concurrency" (
    set CONCURRENCY=%2
    shift
    shift
)

echo ================================================================================
echo Running Benchmark - Single Host Setup
echo ================================================================================
echo Config: %CONFIG_FILE%
echo Leader: %LEADER_HOST%:%LEADER_PORT%
echo Requests: %NUM_REQUESTS%
echo Concurrency: %CONCURRENCY%
echo ================================================================================
echo.

python benchmark_unified.py ^
    --config %CONFIG_FILE% ^
    --leader-host %LEADER_HOST% ^
    --leader-port %LEADER_PORT% ^
    --num-requests %NUM_REQUESTS% ^
    --concurrency %CONCURRENCY% ^
    --log-dir %LOG_DIR% ^
    --output-dir %OUTPUT_DIR%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================================================
    echo Benchmark completed successfully!
    echo Results saved to: %OUTPUT_DIR%\benchmark_fairness_*.txt
    echo ================================================================================
) else (
    echo.
    echo ================================================================================
    echo Benchmark failed with error code: %ERRORLEVEL%
    echo Make sure all nodes are running before running benchmark
    echo ================================================================================
)

pause

