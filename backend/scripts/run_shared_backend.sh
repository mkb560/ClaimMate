#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"
NGROK_API_URL="${NGROK_API_URL:-http://127.0.0.1:4040/api/tunnels}"
PYTHON_BIN="${PYTHON_BIN:-}"
UVICORN_BIN="${UVICORN_BIN:-}"
NGROK_LOG="${NGROK_LOG:-$(mktemp -t claimmate-ngrok.XXXXXX.log)}"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is required."
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required."
  exit 1
fi

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok is required. Install it first or use another public tunnel."
  exit 1
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
  elif [[ -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
    PYTHON_BIN="${BACKEND_DIR}/.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3 || true)"
  fi
fi

if [[ -z "${PYTHON_BIN}" || ! -x "${PYTHON_BIN}" ]]; then
  echo "Could not find a usable Python interpreter. Set PYTHON_BIN explicitly."
  exit 1
fi

declare -a UVICORN_CMD
if [[ -n "${UVICORN_BIN}" ]]; then
  if [[ ! -x "${UVICORN_BIN}" ]]; then
    echo "UVICORN_BIN is set but not executable: ${UVICORN_BIN}"
    exit 1
  fi
  UVICORN_CMD=("${UVICORN_BIN}")
elif "${PYTHON_BIN}" -c 'import importlib.util, sys; sys.exit(0 if importlib.util.find_spec("uvicorn") else 1)' >/dev/null 2>&1; then
  UVICORN_CMD=("${PYTHON_BIN}" -m uvicorn)
elif command -v uvicorn >/dev/null 2>&1; then
  UVICORN_CMD=("$(command -v uvicorn)")
else
  echo "Could not find uvicorn. Install it in your environment or set UVICORN_BIN explicitly."
  exit 1
fi

cd "${BACKEND_DIR}"

UVICORN_PID=""
NGROK_PID=""

cleanup() {
  if [[ -n "${NGROK_PID}" ]] && kill -0 "${NGROK_PID}" 2>/dev/null; then
    kill "${NGROK_PID}" 2>/dev/null || true
    wait "${NGROK_PID}" 2>/dev/null || true
  fi
  if [[ -n "${UVICORN_PID}" ]] && kill -0 "${UVICORN_PID}" 2>/dev/null; then
    kill "${UVICORN_PID}" 2>/dev/null || true
    wait "${UVICORN_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

"${UVICORN_CMD[@]}" main:app --host "${APP_HOST}" --port "${APP_PORT}" &
UVICORN_PID=$!

HEALTH_JSON=""
for _ in {1..30}; do
  HEALTH_JSON="$(curl -sf "http://127.0.0.1:${APP_PORT}/health" || true)"
  if [[ -n "${HEALTH_JSON}" ]]; then
    break
  fi
  sleep 1
done

if [[ -z "${HEALTH_JSON}" ]]; then
  echo "Backend did not become healthy on http://127.0.0.1:${APP_PORT}/health"
  exit 1
fi

AI_READY="$(
  printf '%s' "${HEALTH_JSON}" | "${PYTHON_BIN}" -c 'import json, sys; print("true" if json.load(sys.stdin).get("ai_ready") else "false")'
)"

if [[ "${AI_READY}" != "true" ]]; then
  echo "Backend responded, but ai_ready is false:"
  printf '%s\n' "${HEALTH_JSON}"
  exit 1
fi

ngrok http "http://127.0.0.1:${APP_PORT}" --log=stdout >"${NGROK_LOG}" 2>&1 &
NGROK_PID=$!

PUBLIC_URL=""
for _ in {1..30}; do
  PUBLIC_URL="$("${PYTHON_BIN}" - "${NGROK_API_URL}" <<'PY'
import json
import sys
import urllib.request

api_url = sys.argv[1]
try:
    with urllib.request.urlopen(api_url, timeout=2) as response:
        payload = json.load(response)
except Exception:
    print("")
else:
    urls = [item.get("public_url", "") for item in payload.get("tunnels", [])]
    https_urls = [url for url in urls if url.startswith("https://")]
    print(https_urls[0] if https_urls else (urls[0] if urls else ""))
PY
)"
  if [[ -n "${PUBLIC_URL}" ]]; then
    break
  fi
  sleep 1
done

if [[ -z "${PUBLIC_URL}" ]]; then
  echo "ngrok started, but no public URL was discovered."
  echo "Check ngrok logs at: ${NGROK_LOG}"
  exit 1
fi

cat <<EOF
ClaimMate shared backend is live.

Public API base URL:
  ${PUBLIC_URL}

Local health URL:
  http://127.0.0.1:${APP_PORT}/health

Share these endpoints with teammates:
  ${PUBLIC_URL}/health
  ${PUBLIC_URL}/cases/{case_id}/policy
  ${PUBLIC_URL}/cases/{case_id}/ask

Keep this terminal open. Press Ctrl+C to stop sharing.
EOF

wait "${NGROK_PID}"
