#!/bin/bash
cd "$(dirname "$0")/.."
python scripts/benchmark_strategy_comparison.py "$@"

