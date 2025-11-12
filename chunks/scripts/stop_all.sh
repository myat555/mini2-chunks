#!/bin/bash

# Stop all running processes

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR"

if [ -d "pids" ]; then
    echo "Stopping all processes..."
    for pidfile in pids/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            process=$(basename "$pidfile" .pid)
            if kill -0 "$pid" 2>/dev/null; then
                echo "Stopping process $process (PID: $pid)..."
                kill "$pid"
            else
                echo "Process $process (PID: $pid) not running"
            fi
            rm "$pidfile"
        fi
    done
    echo "All processes stopped"
else
    echo "No pids directory found - no processes to stop"
fi

