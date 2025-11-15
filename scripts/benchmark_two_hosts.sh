#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

BASE_CONFIG="configs/two_hosts_config.json"
ACTIVE_CONFIG="logs/active_two_hosts_config.json"

choose_profile() {
  echo "Choose a strategy profile:"
  echo "  [1] Baseline  - round_robin / blocking / fixed / strict
  echo "  [2] Parallel  - parallel    / async    / adaptive / strict
  echo "  [3] Balanced  - capacity    / async    / query_based / weighted"
  read -rp "Select profile [1-3, default 1]: " choice
  [[ -z "${choice}" ]] && choice=1
  case "${choice}" in
    1) PROFILE="baseline"; FORWARDING="round_robin"; ASYNC="false"; CHUNKING="fixed";      FAIRNESS="strict";   CHUNK_SIZE="500" ;;
    2) PROFILE="parallel"; FORWARDING="parallel";    ASYNC="true";  CHUNKING="adaptive";   FAIRNESS="strict";   CHUNK_SIZE="500" ;;
    3) PROFILE="balanced"; FORWARDING="capacity";    ASYNC="true";  CHUNKING="query_based"; FAIRNESS="weighted"; CHUNK_SIZE="500" ;;
    *) echo "Invalid choice."; choose_profile ;;
  esac
}

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

choose_profile
prepare_config

mkdir -p logs/two_hosts
echo "Running benchmark with profile ${PROFILE}..."
python3 benchmark_unified.py --config "${ACTIVE_CONFIG}" --leader-host 192.168.1.2 --leader-port 60051 --log-dir logs/two_hosts --output-dir logs/two_hosts

rm -f "${ACTIVE_CONFIG}"