#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON_BIN="${NEUROSTREAMLAB_PYTHON:-python3.12}"
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install uv
.venv/bin/uv sync --frozen --extra dev
npm ci --prefix frontend
.venv/bin/neurostreamlab doctor
