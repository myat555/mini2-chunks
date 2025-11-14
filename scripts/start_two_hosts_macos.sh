#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_FILE="${ROOT_DIR}/two_hosts_config.json"
LOG_DIR="${SCRIPT_DIR}/logs"
PID_DIR="${SCRIPT_DIR}/pids"

echo "Starting macOS-side processes for two-host configuration..."
echo "This will start: C (Worker), E (Team Leader), F (Worker) on 192.168.1.1"
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 not found."
    exit 1
fi

if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "Error: two_hosts_config.json not found."
    exit 1
fi

if [[ ! -f "${ROOT_DIR}/overlay_pb2.py" ]]; then
    echo "Generating proto stubs..."
    cd "${ROOT_DIR}"
    python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. overlay.proto
    cd "${SCRIPT_DIR}"
fi

mkdir -p "${LOG_DIR}" "${PID_DIR}"
mkdir -p "${ROOT_DIR}/logs/two_hosts"

start_process() {
    local proc_id="$1"
    local role="$2"
    local host_ip="192.168.1.1"
    local log_file="${ROOT_DIR}/logs/two_hosts/macos_${host_ip}_node_$(echo ${proc_id} | tr '[:upper:]' '[:lower:]').log"
    echo "Starting Process ${proc_id} (${role})..."
    python3 -u "${ROOT_DIR}/node.py" "${CONFIG_FILE}" "${proc_id}" >"${log_file}" 2>&1 &
    local pid=$!
    echo "${pid}" > "${PID_DIR}/process_${proc_id}.pid"
    echo "  PID=${pid}, log: ${log_file}"
    sleep 2
}

start_process C "Worker"
start_process E "Team Leader"
start_process F "Worker"

cleanup() {
    echo
    echo "Stopping all macOS-side processes..."
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
echo "macOS-side processes started: C, E, F"
echo "============================================================"
echo
echo "Process information:"
echo "  - Process C (Worker):     192.168.1.1:60053"
echo "  - Process E (Team Leader): 192.168.1.1:60055"
echo "  - Process F (Worker):     192.168.1.1:60056"
echo
echo "Log files location: logs/two_hosts/"
echo "  - macos_192.168.1.1_node_c.log"
echo "  - macos_192.168.1.1_node_e.log"
echo "  - macos_192.168.1.1_node_f.log"
echo
echo "View logs: scripts/view_two_hosts_logs.sh"
echo
echo "Press Ctrl+C to stop macOS processes..."
while true; do
    sleep 1
done

