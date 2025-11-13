#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_FILE="${ROOT_DIR}/one_host_config.json"
LOG_DIR="${SCRIPT_DIR}/logs"
PID_DIR="${SCRIPT_DIR}/pids"

REQUESTS="${1:-200}"
CONCURRENCY="${2:-20}"

cd "${ROOT_DIR}"

echo "Starting single-host servers..."
echo

# Generate proto if needed
if [[ ! -f "${ROOT_DIR}/overlay_pb2.py" ]]; then
    echo "Generating proto stubs..."
    python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. overlay.proto
fi

mkdir -p "${LOG_DIR}" "${PID_DIR}"

start_process() {
    local proc_id="$1"
    local role="$2"
    local log_file="${LOG_DIR}/process_${proc_id}.log"
    echo "Starting Process ${proc_id} (${role})..."
    python3 -u "${ROOT_DIR}/node.py" "${CONFIG_FILE}" "${proc_id}" >"${log_file}" 2>&1 &
    local pid=$!
    echo "${pid}" > "${PID_DIR}/process_${proc_id}.pid"
    sleep 2
}

start_process A "Leader"
start_process B "Team Leader"
start_process C "Worker"
start_process D "Worker"
start_process E "Team Leader"
start_process F "Worker"

echo "Waiting for servers to be ready..."
sleep 10

# Wait for leader to be ready
for i in {1..30}; do
    if python3 -c "
import grpc
import overlay_pb2
import overlay_pb2_grpc

try:
    channel = grpc.insecure_channel('127.0.0.1:60051')
    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
    metrics = stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
    channel.close()
    if metrics.process_id and metrics.role == 'leader':
        exit(0)
except:
    exit(1)
" 2>/dev/null; then
        echo "Servers ready!"
        break
    fi
    sleep 1
done

echo
echo "Running single-host benchmark..."
echo

python3 benchmark.py 127.0.0.1 60051 "${REQUESTS}" "${CONCURRENCY}"

echo
echo "Stopping servers..."

# Kill all processes from PID files
if [[ -d "${PID_DIR}" ]]; then
    while IFS= read -r pid_file; do
        if [[ -f "${pid_file}" ]]; then
            kill "$(cat "${pid_file}")" 2>/dev/null || true
            rm -f "${pid_file}"
        fi
    done < <(find "${PID_DIR}" -name 'process_*.pid' -print 2>/dev/null || true)
fi

echo "Benchmark complete. Results saved to benchmark_results.json"

