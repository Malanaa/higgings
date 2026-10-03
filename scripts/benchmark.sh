#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/neurostreamlab benchmark run "${1:-configs/benchmarks/smoke.yaml}"
