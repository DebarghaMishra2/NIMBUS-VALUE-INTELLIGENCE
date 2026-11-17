#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [[ "${ENABLE_DENSE_EMBEDDINGS:-0}" == "1" ]]; then
  python -m pip install -r requirements-semantic.txt
fi

HOST="${HOST:-127.0.0.1}"
PORT_WAS_EXPLICIT="${PORT+x}"
PORT="${PORT:-8000}"

port_in_use() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
  else
    python - "$1" <<'PY'
import socket, sys
sock = socket.socket()
try:
    sock.bind(("127.0.0.1", int(sys.argv[1])))
    busy = False
except OSError:
    busy = True
finally:
    sock.close()
raise SystemExit(0 if busy else 1)
PY
  fi
}

if port_in_use "$PORT"; then
  if [[ -z "$PORT_WAS_EXPLICIT" ]]; then
    ORIGINAL_PORT="$PORT"
    for candidate in $(seq $((PORT + 1)) $((PORT + 10))); do
      if ! port_in_use "$candidate"; then
        PORT="$candidate"
        echo "Port $ORIGINAL_PORT is occupied; using available port $PORT instead."
        break
      fi
    done
  fi
fi

if port_in_use "$PORT"; then
  echo "ERROR: Port $PORT is already in use." >&2
  echo "Find the process with: lsof -nP -iTCP:$PORT -sTCP:LISTEN" >&2
  echo "Stop it with: kill <PID>" >&2
  echo "Or choose another port: PORT=8002 ./scripts/run.sh" >&2
  exit 1
fi

echo "Starting Nimbus at http://$HOST:$PORT"
exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
