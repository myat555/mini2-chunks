#!/bin/bash
cd "$(dirname "$0")/.."
python scripts/monitor_two_hosts.py "$@"

