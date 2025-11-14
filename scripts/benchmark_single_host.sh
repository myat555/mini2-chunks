#!/bin/bash
cd "$(dirname "$0")/.."
python3 benchmark_unified.py --config one_host_config.json --leader-host 127.0.0.1 --leader-port 60051 --log-dir logs/macos --output-dir logs/macos "$@"

