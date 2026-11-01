#!/usr/bin/env bash
# Runs the POS-MOBILE end-to-end browser tests.
#   E2E_PORT       static server port (default 8801)
#   E2E_CACHE_DIR  cache for SheetJS/Chart.js fetched with `npm pack` (default $TMPDIR/pos-e2e-cache)
#   E2E_ONLY       run only tests whose name contains this text
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PORT="${E2E_PORT:-8801}"
export E2E_PORT="$PORT"
export E2E_BASE_URL="http://127.0.0.1:${PORT}/"

if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
  echo "port $PORT is already in use — set E2E_PORT to a free port" >&2
  exit 2
fi

python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$ROOT" >/dev/null 2>&1 &
SERVER_PID=$!
cleanup() { kill "$SERVER_PID" 2>/dev/null; wait "$SERVER_PID" 2>/dev/null; }
trap cleanup EXIT INT TERM

for _ in $(seq 1 50); do
  (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then echo "static server failed to start" >&2; exit 2; fi
  sleep 0.1
done

node "$HERE/frontend.spec.js"
CODE=$?
exit $CODE
