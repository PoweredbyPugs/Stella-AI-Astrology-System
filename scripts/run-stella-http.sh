#!/bin/sh
# launchd entrypoint for the remote Stella endpoint.
# Loads stella/.env (secrets live there, never in the plist) and execs the HTTP
# proxy under its own venv. See stella_http.py for the architecture.
set -eu
STELLA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$STELLA_DIR"
if [ ! -f .env ]; then
  echo "run-stella-http: $STELLA_DIR/.env missing; refusing to start" >&2
  exit 78  # EX_CONFIG
fi
set -a
. ./.env
set +a
exec "$STELLA_DIR/.venv-http/bin/python" "$STELLA_DIR/stella_http.py"
