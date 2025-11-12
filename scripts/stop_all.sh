#!/bin/bash

echo "Stopping all processes..."

# Stop macOS processes from PID files
if [ -d "pids" ]; then
    for pid_file in pids/*.pid; do
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if ps -p $pid > /dev/null 2>&1; then
                echo "Stopping process with PID: $pid"
                kill $pid
            fi
            rm "$pid_file"
        fi
    done
fi

# Clean up empty directories
rmdir pids 2>/dev/null
rmdir logs 2>/dev/null

echo "All processes stopped."
