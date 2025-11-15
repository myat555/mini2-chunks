#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

BASE_CONFIG="configs/two_hosts_config.json"
ACTIVE_CONFIG="logs/active_two_hosts_config.json"

# Parse command-line arguments
PROFILE="${1:-baseline}"
NUM_REQUESTS="${2:-400}"
CONCURRENCY="${3:-20}"

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
    echo "Usage: $0 [baseline|parallel|weighted|hybrid] [num_requests] [concurrency]"
    echo "  baseline: round_robin / blocking / fixed / strict (default)"
    echo "  parallel: parallel / async / adaptive / strict"
    echo "  weighted: round_robin / blocking / fixed / weighted"
    echo "  hybrid: round_robin / blocking / fixed / hybrid"
    echo ""
    echo "  num_requests: Number of requests (default: 400)"
    echo "  concurrency: Concurrent requests (default: 20)"
    exit 1
    ;;
esac

prepare_config() {
  mkdir -p logs
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

prepare_config

mkdir -p logs/two_hosts
echo "Running benchmark with profile ${PROFILE}..."
echo "Requests: ${NUM_REQUESTS}, Concurrency: ${CONCURRENCY}"
python3 benchmark_unified.py --config "${ACTIVE_CONFIG}" --leader-host 192.168.1.2 --leader-port 60051 --num-requests "${NUM_REQUESTS}" --concurrency "${CONCURRENCY}" --log-dir logs/two_hosts --output-dir logs/two_hosts

rm -f "${ACTIVE_CONFIG}"
