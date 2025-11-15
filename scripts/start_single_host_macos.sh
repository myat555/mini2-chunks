#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BASE_CONFIG="${ROOT_DIR}/configs/one_host_config.json"
ACTIVE_CONFIG="${ROOT_DIR}/logs/active_one_host_config.json"
PID_DIR="${SCRIPT_DIR}/pids"

choose_profile() {
  echo "Choose a strategy profile:"
  echo "  [1] Baseline  - round_robin / blocking / fixed / strict"
  echo "  [2] Parallel  - parallel    / async    / adaptive / strict"
  echo "  [3] Balanced  - capacity    / async    / query_based / weighted"
  read -rp "Select profile [1-3, default 1]: " choice
  [[ -z "${choice}" ]] && choice=1
  case "${choice}" in
    1) PROFILE="baseline"; FORWARDING="round_robin"; ASYNC="false"; CHUNKING="fixed";      FAIRNESS="strict";   CHUNK_SIZE="200" ;;
    2) PROFILE="parallel"; FORWARDING="parallel";    ASYNC="true";  CHUNKING="adaptive";   FAIRNESS="strict";   CHUNK_SIZE="200" ;;
    3) PROFILE="balanced"; FORWARDING="capacity";    ASYNC="true";  CHUNKING="query_based"; FAIRNESS="weighted"; CHUNK_SIZE="200" ;;
    *) echo "Invalid choice."; choose_profile ;;
  esac
}

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
  local log_file="${ROOT_DIR}/logs/macos/node_${proc_id,,}.log"
  echo "Starting Process ${proc_id} (${label})..."
  (cd "${ROOT_DIR}" && python3 -u node.py "${ACTIVE_CONFIG}" "${proc_id}" > "${log_file}" 2>&1) &
  local pid=$!
  echo "${pid}" > "${PID_DIR}/process_${proc_id}.pid"
  echo "  PID=${pid}, log=${log_file}"
  sleep 2
}

cleanup() {
  echo
  echo "Stopping all processes..."
  find "${PID_DIR}" -name 'process_*.pid' -print 2>/dev/null | while read -r pidfile; do
    if [[ -f "${pidfile}" ]]; then
      kill "$(cat "${pidfile}")" 2>/dev/null || true
      rm -f "${pidfile}"
    fi
  done
  rm -f "${ACTIVE_CONFIG}"
  echo "All processes stopped."
  exit 0
}

choose_profile
prepare_config

mkdir -p "${ROOT_DIR}/logs/macos" "${PID_DIR}"

trap cleanup SIGINT SIGTERM

start_process A "Leader"
start_process B "Team Leader"
start_process C "Worker"
start_process D "Worker"
start_process E "Team Leader"
start_process F "Worker"

echo
echo "============================================================"
echo "All single-host processes started (profile: ${PROFILE})"
echo "Press Ctrl+C to stop them."
echo "============================================================"

while true; do
  sleep 1
done