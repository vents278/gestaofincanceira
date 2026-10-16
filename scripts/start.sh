#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Development-only fallback. Production must inject a persistent JWT_SECRET.
if [[ -z "${JWT_SECRET:-}" ]]; then
  mkdir -p .local
  .venv/bin/python - <<'PY'
import os
import secrets
from pathlib import Path
path = Path('.local/jwt-secret')
try:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    pass
else:
    with os.fdopen(fd, 'w') as f:
        f.write(secrets.token_urlsafe(48))
PY
  JWT_SECRET="$(cat .local/jwt-secret)"
  export JWT_SECRET
fi
.venv/bin/alembic upgrade head
exec .venv/bin/uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
