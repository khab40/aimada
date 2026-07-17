#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/lob-arena-grader.XXXXXX")"
ARTIFACT_DIR="${TMP_DIR}/artifacts"
BACKEND_LOG="${TMP_DIR}/backend.log"
FRONTEND_LOG="${TMP_DIR}/frontend.log"
BACKEND_PID=""
FRONTEND_PID=""
export UV_CACHE_DIR="${UV_CACHE_DIR:-${TMP_DIR}/uv-cache}"
export PNPM_HOME="${PNPM_HOME:-${TMP_DIR}/pnpm-home}"
export PNPM_STORE_DIR="${PNPM_STORE_DIR:-${TMP_DIR}/pnpm-store}"
export PATH="${PNPM_HOME}:${PATH}"

cleanup() {
  local status=$?
  trap - EXIT INT TERM
  if [[ -n "${FRONTEND_PID}" ]]; then kill "${FRONTEND_PID}" 2>/dev/null || true; fi
  if [[ -n "${BACKEND_PID}" ]]; then kill "${BACKEND_PID}" 2>/dev/null || true; fi
  if [[ -n "${FRONTEND_PID}" ]]; then wait "${FRONTEND_PID}" 2>/dev/null || true; fi
  if [[ -n "${BACKEND_PID}" ]]; then wait "${BACKEND_PID}" 2>/dev/null || true; fi
  if (( status != 0 )); then
    printf '%s\n' "grader smoke failed; backend log follows" >&2
    tail -n 80 "${BACKEND_LOG}" 2>/dev/null >&2 || true
    printf '%s\n' "grader smoke failed; frontend log follows" >&2
    tail -n 80 "${FRONTEND_LOG}" 2>/dev/null >&2 || true
  fi
  if [[ "${KEEP_GRADER_OUTPUT:-0}" == "1" ]]; then
    printf 'grader artifacts retained at %s\n' "${TMP_DIR}" >&2
  else
    rm -rf "${TMP_DIR}"
  fi
  exit "${status}"
}
trap cleanup EXIT INT TERM

for command_name in uv corepack curl; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    printf 'required command not found: %s\n' "${command_name}" >&2
    exit 1
  fi
done
corepack enable
if ! command -v pnpm >/dev/null 2>&1; then
  printf '%s\n' 'required command not found: pnpm' >&2
  exit 1
fi

mkdir -p "${ARTIFACT_DIR}"
uv sync --project "${ROOT_DIR}/backend" --dev --frozen >/dev/null
if [[ ! -x "${ROOT_DIR}/frontend/node_modules/.bin/vite" ]]; then
  pnpm --dir "${ROOT_DIR}/frontend" install --frozen-lockfile --ignore-scripts >/dev/null
fi

free_port() {
  uv run --project "${ROOT_DIR}/backend" python -c \
    'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
}

BACKEND_PORT="$(free_port)"
FRONTEND_PORT="$(free_port)"
while [[ "${FRONTEND_PORT}" == "${BACKEND_PORT}" ]]; do FRONTEND_PORT="$(free_port)"; done
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}"

env \
  ARENA_OUTPUT_DIR="${ARTIFACT_DIR}" \
  ARENA_AGENT_COUNT=3 \
  ARENA_REMOTE_AGENT_URLS= \
  ENDPOINT_TOKEN= \
  NEBIUS_ENDPOINT_TOKEN= \
  NEBIUS_ENDPOINT_MODE=mock \
  NEBIUS_ENDPOINT_BASE_URL= \
  NEBIUS_INCIDENT_EXPLAINER_URL= \
  NEBIUS_SCENARIO_GENERATOR_URL= \
  NEBIUS_MARKET_ABUSE_SCENARIO_URL= \
  NEBIUS_ORDERBOOK_ALERT_URL= \
  NEBIUS_INVESTIGATION_REPORT_URL= \
  NEBIUS_INVESTIGATION_TEAM_URL= \
  NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE= \
  NEBIUS_JOB_STATUS_COMMAND_TEMPLATE= \
  NEBIUS_JOB_LOGS_COMMAND_TEMPLATE= \
  NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE= \
  NEBIUS_JOB_OUTPUT_URI= \
  NEBIUS_OBJECT_STORAGE_ENDPOINT_URL= \
  NEBIUS_EVIDENCE_ARCHIVE_ENABLED=false \
  uv run --project "${ROOT_DIR}/backend" uvicorn app.main:app \
    --app-dir "${ROOT_DIR}/backend" --host 127.0.0.1 --port "${BACKEND_PORT}" \
    >"${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!

env \
  VITE_API_BASE_URL="${BACKEND_URL}" \
  VITE_ARENA_WS_URL="ws://127.0.0.1:${BACKEND_PORT}/ws/arena" \
  pnpm --dir "${ROOT_DIR}/frontend" run dev -- --host 127.0.0.1 --port "${FRONTEND_PORT}" \
    >"${FRONTEND_LOG}" 2>&1 &
FRONTEND_PID=$!

wait_for_url() {
  local url=$1
  local process_id=$2
  for _attempt in {1..120}; do
    if ! kill -0 "${process_id}" 2>/dev/null; then return 1; fi
    if curl -fsS --max-time 2 "${url}" >/dev/null 2>&1; then return 0; fi
    sleep 0.25
  done
  return 1
}

wait_for_url "${BACKEND_URL}/health" "${BACKEND_PID}"
wait_for_url "${FRONTEND_URL}/" "${FRONTEND_PID}"

curl -fsS --max-time 5 "${BACKEND_URL}/health" >"${TMP_DIR}/backend-health.json"
curl -fsS --max-time 5 "${FRONTEND_URL}/" >"${TMP_DIR}/frontend.html"
curl -fsS --max-time 10 "${FRONTEND_URL}/src/main.tsx" >"${TMP_DIR}/frontend-entry.js"
curl -fsS --max-time 120 \
  -H 'Content-Type: application/json' \
  -d '{"execution_mode":"local"}' \
  "${BACKEND_URL}/api/nebius/serverless-smoke/run" >"${TMP_DIR}/smoke-response.json"

uv run --project "${ROOT_DIR}/backend" python "${ROOT_DIR}/scripts/validate_grader_smoke.py" \
  --health "${TMP_DIR}/backend-health.json" \
  --frontend "${TMP_DIR}/frontend.html" \
  --frontend-entry "${TMP_DIR}/frontend-entry.js" \
  --response "${TMP_DIR}/smoke-response.json" \
  --artifact-root "${ARTIFACT_DIR}"

uv run --project "${ROOT_DIR}/backend" python "${ROOT_DIR}/scripts/check_markdown_links.py" \
  "${ROOT_DIR}/README.md" "${ROOT_DIR}/docs" >/dev/null

printf '%s\n' GRADER_OK
