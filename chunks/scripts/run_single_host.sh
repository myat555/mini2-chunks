#!/bin/bash

# Run all 6 processes (A-F) on single host (localhost)
# Each process runs in background

CONFIG_FILE="config/single_host.json"
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$BASE_DIR"

# Use virtual environment Python if available
VENV_DIR="$(cd "$BASE_DIR/.." && pwd)/.venv"
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/python3" ]; then
    PYTHON_CMD="$VENV_DIR/bin/python3"
    echo "Using virtual environment: $PYTHON_CMD"
else
    echo "Warning: Virtual environment not found at $VENV_DIR, using system python3"
    PYTHON_CMD="python3"
fi

# Create directories if they don't exist
mkdir -p logs pids

echo "Starting all 6 processes on localhost..."
echo "Config: $CONFIG_FILE"
echo ""

# Start process A (Leader)
echo "Starting A (leader, green)..."
$PYTHON_CMD node.py "$CONFIG_FILE" A > logs/A.log 2>&1 &
echo $! > pids/A.pid
sleep 1

# Start process B (Team Leader, Green)
echo "Starting B (team_leader, green)..."
$PYTHON_CMD node.py "$CONFIG_FILE" B > logs/B.log 2>&1 &
echo $! > pids/B.pid
sleep 1

# Start process C (Worker, Green)
echo "Starting C (worker, green)..."
$PYTHON_CMD node.py "$CONFIG_FILE" C > logs/C.log 2>&1 &
echo $! > pids/C.pid
sleep 1

# Start process D (Worker, Pink)
echo "Starting D (worker, pink)..."
$PYTHON_CMD node.py "$CONFIG_FILE" D > logs/D.log 2>&1 &
echo $! > pids/D.pid
sleep 1

# Start process E (Team Leader, Pink)
echo "Starting E (team_leader, pink)..."
$PYTHON_CMD node.py "$CONFIG_FILE" E > logs/E.log 2>&1 &
echo $! > pids/E.pid
sleep 1

# Start process F (Worker, Pink)
echo "Starting F (worker, pink)..."
$PYTHON_CMD node.py "$CONFIG_FILE" F > logs/F.log 2>&1 &
echo $! > pids/F.pid
sleep 1

echo ""
echo "All processes started!"
echo "Process IDs saved in pids/ directory"
echo "Logs in logs/ directory"
echo ""
echo "To stop all processes: ./scripts/stop_all.sh"
echo "To test: python3 client_chunks.py localhost 50051"

