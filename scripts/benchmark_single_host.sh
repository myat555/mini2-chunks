#!/bin/bash
cd "$(dirname "$0")/.."

PROFILE="${1:-baseline}"

case "$PROFILE" in
    baseline)
        CONFIG="one_host_config_baseline.json"
        ;;
    parallel)
        CONFIG="one_host_config_parallel.json"
        ;;
    balanced)
        CONFIG="one_host_config_balanced.json"
        ;;
    *)
        echo "Error: Unknown profile '$PROFILE'. Use: baseline, parallel, or balanced"
        exit 1
        ;;
esac

echo "Using strategy profile: $PROFILE"
python3 benchmark_unified.py --config "$CONFIG" --leader-host 127.0.0.1 --leader-port 60051 --log-dir logs/macos --output-dir logs/macos

