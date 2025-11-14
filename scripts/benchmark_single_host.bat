@echo off
cd /d %~dp0\..
python benchmark_unified.py --config one_host_config.json --leader-host 127.0.0.1 --leader-port 60051 --log-dir logs\windows --output-dir logs\windows %*

