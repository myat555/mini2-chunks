@echo off
cd /d %~dp0\..
python benchmark_unified.py --config two_hosts_config.json --leader-host 192.168.1.2 --leader-port 60051 --log-dir logs\two_hosts --output-dir logs\two_hosts %*

