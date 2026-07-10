#!/usr/bin/env bash
set -euo pipefail

UVICORN_HOST="${UVICORN_HOST:-0.0.0.0}"
UVICORN_PORT="${UVICORN_PORT:-9000}"
export PYTHONUNBUFFERED=1

if [[ "${NEBIUS_ENDPOINT_MODE:-mock}" != "local_vllm" ]]; then
  echo "Endpoint startup: mode=${NEBIUS_ENDPOINT_MODE:-mock}; starting FastAPI only on ${UVICORN_HOST}:${UVICORN_PORT}"
  exec uvicorn app:app --host "${UVICORN_HOST}" --port "${UVICORN_PORT}"
fi

LOCAL_VLLM_MODEL="${LOCAL_VLLM_MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
LOCAL_VLLM_HOST="${LOCAL_VLLM_HOST:-127.0.0.1}"
LOCAL_VLLM_PORT="${LOCAL_VLLM_PORT:-8001}"
LOCAL_VLLM_BASE_URL="${LOCAL_VLLM_BASE_URL:-}"
if [[ -z "${LOCAL_VLLM_BASE_URL}" ]]; then
  LOCAL_VLLM_BASE_URL="http://${LOCAL_VLLM_HOST}:${LOCAL_VLLM_PORT}/v1"
fi
LOCAL_VLLM_GPU_MEMORY_UTILIZATION="${LOCAL_VLLM_GPU_MEMORY_UTILIZATION:-0.85}"
LOCAL_VLLM_MAX_MODEL_LEN="${LOCAL_VLLM_MAX_MODEL_LEN:-4096}"
LOCAL_VLLM_READY_TIMEOUT_SECONDS="${LOCAL_VLLM_READY_TIMEOUT_SECONDS:-900}"
export LOCAL_VLLM_BASE_URL
export LOCAL_VLLM_MODEL
export LOCAL_VLLM_HOST
export LOCAL_VLLM_PORT
export LOCAL_VLLM_GPU_MEMORY_UTILIZATION
export LOCAL_VLLM_MAX_MODEL_LEN

echo "Endpoint startup: mode=local_vllm"
echo
echo "vLLM startup: model=${LOCAL_VLLM_MODEL} host=${LOCAL_VLLM_HOST} port=${LOCAL_VLLM_PORT}"
echo
echo "vLLM readiness..."

python -m vllm.entrypoints.openai.api_server \
  --model "${LOCAL_VLLM_MODEL}" \
  --host "${LOCAL_VLLM_HOST}" \
  --port "${LOCAL_VLLM_PORT}" \
  --gpu-memory-utilization "${LOCAL_VLLM_GPU_MEMORY_UTILIZATION}" \
  --max-model-len "${LOCAL_VLLM_MAX_MODEL_LEN}" &

VLLM_PID="$!"
UVICORN_PID=""

cleanup() {
  if [[ -n "${UVICORN_PID}" ]] && kill -0 "${UVICORN_PID}" >/dev/null 2>&1; then
    echo "Endpoint shutdown: stopping uvicorn pid=${UVICORN_PID}"
    kill "${UVICORN_PID}" >/dev/null 2>&1 || true
    wait "${UVICORN_PID}" >/dev/null 2>&1 || true
  fi
  if kill -0 "${VLLM_PID}" >/dev/null 2>&1; then
    echo "Endpoint shutdown: stopping vLLM pid=${VLLM_PID}"
    kill "${VLLM_PID}" >/dev/null 2>&1 || true
    wait "${VLLM_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "vLLM readiness: waiting for ${LOCAL_VLLM_BASE_URL}/models timeout_seconds=${LOCAL_VLLM_READY_TIMEOUT_SECONDS}"

LOCAL_VLLM_BASE_URL="${LOCAL_VLLM_BASE_URL}" \
LOCAL_VLLM_READY_TIMEOUT_SECONDS="${LOCAL_VLLM_READY_TIMEOUT_SECONDS}" \
VLLM_PID="${VLLM_PID}" \
python - <<'PY'
import os
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

base_url = os.environ["LOCAL_VLLM_BASE_URL"].rstrip("/")
timeout_seconds = float(os.environ["LOCAL_VLLM_READY_TIMEOUT_SECONDS"])
pid = int(os.environ["VLLM_PID"])
deadline = time.monotonic() + timeout_seconds
url = f"{base_url}/models"
attempt = 0

while time.monotonic() < deadline:
    attempt += 1
    try:
        with urlopen(url, timeout=5) as response:
            if 200 <= response.status < 300:
                print(f"vLLM readiness: ready url={url} attempts={attempt}", flush=True)
                sys.exit(0)
    except Exception as ex:
        if attempt == 1 or attempt % 10 == 0:
            print(f"vLLM readiness: waiting url={url} attempt={attempt} error={type(ex).__name__}: {ex}", flush=True)

    try:
        os.kill(pid, 0)
    except OSError:
        print(f"vLLM readiness: process exited before ready pid={pid}", flush=True)
        sys.exit(1)

    time.sleep(5)

print(f"vLLM readiness: timed out url={url} timeout_seconds={timeout_seconds}", flush=True)
sys.exit(1)
PY

echo "vLLM ready"
echo "Uvicorn running on http://${UVICORN_HOST}:${UVICORN_PORT}"
uvicorn app:app --host "${UVICORN_HOST}" --port "${UVICORN_PORT}" &
UVICORN_PID="$!"

set +e
wait -n "${UVICORN_PID}" "${VLLM_PID}"
EXIT_CODE="$?"
set -e

echo "Endpoint supervisor: one service exited exit_code=${EXIT_CODE}; shutting down remaining services"
exit "${EXIT_CODE}"
