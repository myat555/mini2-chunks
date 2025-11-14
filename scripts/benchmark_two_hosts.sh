#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

HOST="${1:-192.168.1.2}"
PORT="${2:-60051}"
REQUESTS="${3:-200}"
CONCURRENCY="${4:-20}"

cd "${ROOT_DIR}"

python3 "${SCRIPT_DIR}/benchmark_two_hosts.py" --host "${HOST}" --port "${PORT}" --requests "${REQUESTS}" --concurrency "${CONCURRENCY}"

