#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROFILE="${1:-baseline}"
LOG_DIR="${SCRIPT_DIR}/logs"
PID_DIR="${SCRIPT_DIR}/pids"

case "$PROFILE" in
    baseline)
        CONFIG_FILE="${ROOT_DIR}/one_host_config_baseline.json"
        ;;
    parallel)
        CONFIG_FILE="${ROOT_DIR}/one_host_config_parallel.json"
        ;;
    balanced)
        CONFIG_FILE="${ROOT_DIR}/one_host_config_balanced.json"
        ;;
    *)
        echo "Error: Unknown profile '$PROFILE'. Use: baseline, parallel, or balanced"
        exit 1
        ;;
esac

echo "Starting all single-host processes on macOS..."
echo "Using strategy profile: $PROFILE"
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 not found."
    exit 1
fi

if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "Error: one_host_config.json not found."
    exit 1
fi

if [[ ! -f "${ROOT_DIR}/overlay_pb2.py" ]]; then
    echo "Generating proto stubs..."
    cd "${ROOT_DIR}"
    python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. overlay.proto
    cd "${SCRIPT_DIR}"
fi

mkdir -p "${ROOT_DIR}/logs/macos" "${PID_DIR}"

cd "${ROOT_DIR}"

start_process() {
    local proc_id="$1"
    local role="$2"
    local log_file="${ROOT_DIR}/logs/macos/node_$(echo ${proc_id} | tr '[:upper:]' '[:lower:]').log"
    echo "Starting Process ${proc_id} (${role})..."
    (cd "${ROOT_DIR}" && python3 -u "${ROOT_DIR}/node.py" "${CONFIG_FILE}" "${proc_id}" >"${log_file}" 2>&1) &
    local pid=$!
    echo "${pid}" > "${PID_DIR}/process_${proc_id}.pid"
    echo "  PID=${pid}, log: ${log_file}"
    sleep 2
}

start_process A "Leader"
start_process B "Team Leader"
start_process C "Worker"
start_process D "Worker"
start_process E "Team Leader"
start_process F "Worker"

cleanup() {
    echo
    echo "Stopping all processes..."
    while IFS= read -r pid_file; do
        if [[ -f "${pid_file}" ]]; then
            kill "$(cat "${pid_file}")" 2>/dev/null || true
            rm -f "${pid_file}"
        fi
    done < <(find "${PID_DIR}" -name 'process_*.pid' -print 2>/dev/null || true)
    echo "All processes stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

echo
echo "============================================================"
echo "All single-host processes started (A-F on localhost)"
echo "============================================================"
echo
echo "To run benchmark:"
echo "  scripts/benchmark_single_host.sh $PROFILE"
echo
echo "Press Ctrl+C to stop them."
while true; do
    sleep 1
done

