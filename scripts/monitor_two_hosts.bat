@echo off
cd /d %~dp0\..
python scripts/monitor_two_hosts.py %*

