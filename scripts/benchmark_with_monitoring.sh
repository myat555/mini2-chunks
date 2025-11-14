#!/bin/bash
cd "$(dirname "$0")/.."
python scripts/benchmark_with_monitoring.py "$@"

