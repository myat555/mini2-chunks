#!/bin/bash

# Run processes on two hosts
# Host 1: A, B, D
# Host 2: C, E, F

CONFIG_FILE="config/two_host.json"
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$BASE_DIR"

# Create directories if they don't exist
mkdir -p logs pids

if [ -z "$HOST_NUM" ]; then
    echo "Usage: HOST_NUM=1 ./scripts/run_two_host.sh  (on host 1)"
    echo "       HOST_NUM=2 ./scripts/run_two_host.sh  (on host 2)"
    echo ""
    echo "Host 1 runs: A, B, D"
    echo "Host 2 runs: C, E, F"
    exit 1
fi

if [ "$HOST_NUM" = "1" ]; then
    echo "Starting processes on Host 1 (A, B, D)..."
    
    python3 node.py "$CONFIG_FILE" A > logs/A.log 2>&1 &
    echo $! > pids/A.pid
    sleep 1
    
    python3 node.py "$CONFIG_FILE" B > logs/B.log 2>&1 &
    echo $! > pids/B.pid
    sleep 1
    
    python3 node.py "$CONFIG_FILE" D > logs/D.log 2>&1 &
    echo $! > pids/D.pid
    
    echo "Host 1 processes started: A, B, D"
    
elif [ "$HOST_NUM" = "2" ]; then
    echo "Starting processes on Host 2 (C, E, F)..."
    
    python3 node.py "$CONFIG_FILE" C > logs/C.log 2>&1 &
    echo $! > pids/C.pid
    sleep 1
    
    python3 node.py "$CONFIG_FILE" E > logs/E.log 2>&1 &
    echo $! > pids/E.pid
    sleep 1
    
    python3 node.py "$CONFIG_FILE" F > logs/F.log 2>&1 &
    echo $! > pids/F.pid
    
    echo "Host 2 processes started: C, E, F"
fi

echo "To stop: ./scripts/stop_all.sh"

