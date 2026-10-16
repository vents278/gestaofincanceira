#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
args=()
if [[ -f .env ]]; then args+=(--env-file .env); fi
exec .venv/bin/uvicorn app.main:app "${args[@]}" --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
