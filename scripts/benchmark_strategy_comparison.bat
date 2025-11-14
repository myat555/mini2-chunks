@echo off
cd /d %~dp0\..
python scripts/benchmark_strategy_comparison.py %*

