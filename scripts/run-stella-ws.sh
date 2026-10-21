#!/bin/sh
# launchd entrypoint for the Bulbasaur WebSocket bridge.
# Loads stella/.env (STELLA_WS_TOKEN lives there, never in the plist) and execs
# the bridge under the http venv. See stella_ws.py for the architecture.
set -eu
STELLA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$STELLA_DIR"
if [ ! -f .env ]; then
  echo "run-stella-ws: $STELLA_DIR/.env missing; refusing to start" >&2
  exit 78  # EX_CONFIG
fi
set -a
. ./.env
set +a
exec "$STELLA_DIR/.venv-http/bin/python" "$STELLA_DIR/stella_ws.py"
