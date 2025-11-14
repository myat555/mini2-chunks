#!/bin/bash
cd "$(dirname "$0")/.."

PROFILE="${1:-baseline}"

case "$PROFILE" in
    baseline)
        CONFIG="two_hosts_config_baseline.json"
        ;;
    parallel)
        CONFIG="two_hosts_config_parallel.json"
        ;;
    balanced)
        CONFIG="two_hosts_config_balanced.json"
        ;;
    *)
        echo "Error: Unknown profile '$PROFILE'. Use: baseline, parallel, or balanced"
        exit 1
        ;;
esac

echo "Using strategy profile: $PROFILE"
python3 benchmark_unified.py --config "$CONFIG" --leader-host 192.168.1.2 --leader-port 60051 --log-dir logs/two_hosts --output-dir logs/two_hosts

