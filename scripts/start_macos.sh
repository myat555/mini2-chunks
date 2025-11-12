#!/bin/bash

echo "Starting macOS processes for 2-host leader-queue test..."
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 not found. Please install Python and try again."
    exit 1
fi

# Check if config file exists
if [ ! -f "../two_hosts_config.json" ]; then
    echo "Error: two_hosts_config.json not found."
    exit 1
fi

# Check if proto files are generated
if [ ! -f "../overlay_pb2.py" ]; then
    echo "Generating proto files..."
    python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. overlay.proto
    if [ $? -ne 0 ]; then
        echo "Error: Failed to generate proto files."
        exit 1
    fi
fi

# Create logs directory
mkdir -p logs

echo "Starting Process C (Worker) on port 50053..."
python3 node.py two_hosts_config.json C > logs/process_c.log 2>&1 &
C_PID=$!
echo $C_PID > pids/process_c.pid
sleep 2

echo "Starting Process E (Team Leader) on port 50055..."
python3 node.py two_hosts_config.json E > logs/process_e.log 2>&1 &
E_PID=$!
echo $E_PID > pids/process_e.pid
sleep 2

echo "Starting Process F (Worker) on port 50056..."
python3 node.py two_hosts_config.json F > logs/process_f.log 2>&1 &
F_PID=$!
echo $F_PID > pids/process_f.pid
sleep 2

echo
echo "All macOS processes started:"
echo "  - Process C (Worker): port 50053 (PID: $C_PID)"
echo "  - Process E (Team Leader): port 50055 (PID: $E_PID)"
echo "  - Process F (Worker): port 50056 (PID: $F_PID)"
echo
echo "Process logs are in logs/ directory"
echo "Press Ctrl+C to stop all processes..."

# Function to cleanup processes
cleanup() {
    echo
    echo "Stopping all macOS processes..."
    kill $C_PID $E_PID $F_PID 2>/dev/null
    echo "All processes stopped."
    exit 0
}

# Set trap for Ctrl+C
trap cleanup SIGINT

# Wait indefinitely
while true; do
    sleep 1
done
