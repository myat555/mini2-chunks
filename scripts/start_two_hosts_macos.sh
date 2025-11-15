#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BASE_CONFIG="${ROOT_DIR}/configs/two_hosts_config.json"
ACTIVE_CONFIG="${ROOT_DIR}/logs/active_two_hosts_config.json"
PID_DIR="${SCRIPT_DIR}/pids"

# Parse command-line arguments
PROFILE="${1:-baseline}"
FORWARDING="round_robin"
ASYNC="false"
CHUNKING="fixed"
FAIRNESS="strict"
CHUNK_SIZE="500"

case "${PROFILE}" in
  parallel)
    FORWARDING="parallel"
    ASYNC="true"
    CHUNKING="adaptive"
    FAIRNESS="strict"
    ;;
  weighted)
    FORWARDING="round_robin"
    ASYNC="false"
    CHUNKING="fixed"
    FAIRNESS="weighted"
    ;;
  hybrid)
    FORWARDING="round_robin"
    ASYNC="false"
    CHUNKING="fixed"
    FAIRNESS="hybrid"
    ;;
  baseline)
    # Default values already set
    ;;
  *)
    echo "Usage: $0 [baseline|parallel|weighted|hybrid]"
    echo "  baseline: round_robin / blocking / fixed / strict (default)"
    echo "  parallel: parallel / async / adaptive / strict"
    echo "  weighted: round_robin / blocking / fixed / weighted"
    echo "  hybrid: round_robin / blocking / fixed / hybrid"
    exit 1
    ;;
esac

prepare_config() {
  mkdir -p "${ROOT_DIR}/logs"
  python3 - <<'PY' "${BASE_CONFIG}" "${ACTIVE_CONFIG}" "${FORWARDING}" "${ASYNC}" "${CHUNKING}" "${FAIRNESS}" "${CHUNK_SIZE}"
import json, sys
base, out = sys.argv[1], sys.argv[2]
fwd, async_flag, chunk, fair, size = sys.argv[3:]
data = json.loads(open(base, "r", encoding="utf-8").read())
data.setdefault("strategies", {})
data["strategies"]["forwarding_strategy"] = fwd
data["strategies"]["async_forwarding"] = async_flag.lower() == "true"
data["strategies"]["chunking_strategy"] = chunk
data["strategies"]["fairness_strategy"] = fair
data["strategies"]["chunk_size"] = int(size)
with open(out, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
PY
}

start_process() {
  local proc_id="$1"
  local label="$2"
  local host_ip="192.168.1.1"
  local lower_id
  lower_id="$(echo "${proc_id}" | tr '[:upper:]' '[:lower:]')"
  local log_file="${ROOT_DIR}/logs/two_hosts/macos_${host_ip}_node_${lower_id}.log"
  echo "Starting ${proc_id} (${label})..."
  (cd "${ROOT_DIR}" && python3 -u node.py "${ACTIVE_CONFIG}" "${proc_id}" > "${log_file}" 2>&1) &
  local pid=$!
  echo "${pid}" > "${PID_DIR}/process_${proc_id}.pid"
  echo "  PID=${pid}, log=${log_file}"
  sleep 2
}

cleanup() {
  echo
  echo "Stopping macOS-side processes..."
  find "${PID_DIR}" -name 'process_*.pid' -print 2>/dev/null | while read -r pidfile; do
    if [[ -f "${pidfile}" ]]; then
      kill "$(cat "${pidfile}")" >/dev/null 2>&1 || true
      rm -f "${pidfile}"
    fi
  done
  rm -f "${ACTIVE_CONFIG}"
  echo "All processes stopped."
  exit 0
}

prepare_config

mkdir -p "${ROOT_DIR}/logs/two_hosts" "${PID_DIR}"

trap cleanup SIGINT SIGTERM

start_process C "Worker"
start_process E "Team Leader"
start_process F "Worker"

echo
echo "============================================================"
echo "macOS-side processes started (profile: ${PROFILE})"
echo "Press Ctrl+C to stop them."
echo "============================================================"

while true; do
  sleep 1
done
