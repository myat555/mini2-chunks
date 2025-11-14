@echo off
cd /d %~dp0\..
python scripts/benchmark_with_monitoring.py %*

