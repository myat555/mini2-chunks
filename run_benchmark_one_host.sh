#!/bin/bash
# Benchmark script for single-host setup (macOS/Linux)
# Usage: ./run_benchmark_one_host.sh [--num-requests N] [--concurrency N]

DEFAULT_REQUESTS=100
DEFAULT_CONCURRENCY=10
CONFIG_FILE="configs/one_host_config.json"
LEADER_HOST="127.0.0.1"
LEADER_PORT=60051
LOG_DIR="logs/macos"
OUTPUT_DIR="logs/macos"

# Parse optional arguments
NUM_REQUESTS=$DEFAULT_REQUESTS
CONCURRENCY=$DEFAULT_CONCURRENCY

while [[ $# -gt 0 ]]; do
    case $1 in
        --num-requests)
            NUM_REQUESTS="$2"
            shift 2
            ;;
        --concurrency)
            CONCURRENCY="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--num-requests N] [--concurrency N]"
            exit 1
            ;;
    esac
done

echo "================================================================================"
echo "Running Benchmark - Single Host Setup"
echo "================================================================================"
echo "Config: $CONFIG_FILE"
echo "Leader: $LEADER_HOST:$LEADER_PORT"
echo "Requests: $NUM_REQUESTS"
echo "Concurrency: $CONCURRENCY"
echo "================================================================================"
echo ""

python3 benchmark_unified.py \
    --config "$CONFIG_FILE" \
    --leader-host "$LEADER_HOST" \
    --leader-port "$LEADER_PORT" \
    --num-requests "$NUM_REQUESTS" \
    --concurrency "$CONCURRENCY" \
    --log-dir "$LOG_DIR" \
    --output-dir "$OUTPUT_DIR"

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================================================"
    echo "Benchmark completed successfully!"
    echo "Results saved to: $OUTPUT_DIR/benchmark_fairness_*.txt"
    echo "================================================================================"
else
    echo ""
    echo "================================================================================"
    echo "Benchmark failed!"
    echo "Make sure all nodes are running before running benchmark"
    echo "================================================================================"
    exit 1
fi

