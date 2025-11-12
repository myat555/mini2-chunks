#!/bin/bash

# Run all 6 processes (A-F) on single host (localhost)
# Each process runs in background

CONFIG_FILE="config/single_host.json"
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$BASE_DIR"

# Create directories if they don't exist
mkdir -p logs pids

echo "Starting all 6 processes on localhost..."
echo "Config: $CONFIG_FILE"
echo ""

# Start process A (Leader)
echo "Starting A (leader, green)..."
python3 node.py "$CONFIG_FILE" A > logs/A.log 2>&1 &
echo $! > pids/A.pid
sleep 1

# Start process B (Team Leader, Green)
echo "Starting B (team_leader, green)..."
python3 node.py "$CONFIG_FILE" B > logs/B.log 2>&1 &
echo $! > pids/B.pid
sleep 1

# Start process C (Worker, Green)
echo "Starting C (worker, green)..."
python3 node.py "$CONFIG_FILE" C > logs/C.log 2>&1 &
echo $! > pids/C.pid
sleep 1

# Start process D (Worker, Pink)
echo "Starting D (worker, pink)..."
python3 node.py "$CONFIG_FILE" D > logs/D.log 2>&1 &
echo $! > pids/D.pid
sleep 1

# Start process E (Team Leader, Pink)
echo "Starting E (team_leader, pink)..."
python3 node.py "$CONFIG_FILE" E > logs/E.log 2>&1 &
echo $! > pids/E.pid
sleep 1

# Start process F (Worker, Pink)
echo "Starting F (worker, pink)..."
python3 node.py "$CONFIG_FILE" F > logs/F.log 2>&1 &
echo $! > pids/F.pid
sleep 1

echo ""
echo "All processes started!"
echo "Process IDs saved in pids/ directory"
echo "Logs in logs/ directory"
echo ""
echo "To stop all processes: ./scripts/stop_all.sh"
echo "To test: python3 client_chunks.py localhost 50051"

