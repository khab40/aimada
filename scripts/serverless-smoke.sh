#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT_DIR}"

SMOKE_DIR="${SMOKE_OUTPUT_DIR:-outputs/serverless-smoke}"
ENDPOINT_BASE_URL="${NEBIUS_ENDPOINT_BASE_URL:-${SERVERLESS_ENDPOINT_URL:-http://localhost:9000}}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-${VITE_API_BASE_URL:-http://localhost:8000}}"
IMAGE_NAMESPACE="${IMAGE_NAMESPACE:-ghcr.io/khab40}"
TAG="${TAG:-latest}"
JOBS_IMAGE="${JOBS_IMAGE:-${NEBIUS_JOB_IMAGE:-${IMAGE_NAMESPACE}/lob-arena-jobs:${TAG}}}"
PYTHON_BIN="${PYTHON:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi
SUBMIT_ENABLED="false"
COLLECT_STATUS="not_run"
SUBMIT_STATUS="not_configured"
EXPERIMENT_ID=""
STARTED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

mkdir -p "${SMOKE_DIR}"
SMOKE_ABS_DIR="$(cd "${SMOKE_DIR}" && pwd)"

summary_status="running"
summary_message=""

write_summary() {
  local completed_at
  completed_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  SUMMARY_STATUS="${summary_status}" \
  SUMMARY_MESSAGE="${summary_message}" \
  STARTED_AT="${STARTED_AT}" \
  COMPLETED_AT="${completed_at}" \
  SMOKE_DIR="${SMOKE_DIR}" \
  ENDPOINT_BASE_URL="${ENDPOINT_BASE_URL}" \
  BACKEND_BASE_URL="${BACKEND_BASE_URL}" \
  JOBS_IMAGE="${JOBS_IMAGE}" \
  EXPERIMENT_ID="${EXPERIMENT_ID}" \
  SUBMIT_STATUS="${SUBMIT_STATUS}" \
  COLLECT_STATUS="${COLLECT_STATUS}" \
  "${PYTHON_BIN}" - <<'PY'
import json
import os
from pathlib import Path

smoke_dir = Path(os.environ["SMOKE_DIR"])

def load_json(name: str):
    path = smoke_dir / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"raw": path.read_text(encoding="utf-8")}

summary = {
    "status": os.environ["SUMMARY_STATUS"],
    "message": os.environ["SUMMARY_MESSAGE"],
    "started_at": os.environ["STARTED_AT"],
    "completed_at": os.environ["COMPLETED_AT"],
    "endpoint_base_url": os.environ["ENDPOINT_BASE_URL"],
    "backend_base_url": os.environ["BACKEND_BASE_URL"],
    "jobs_image": os.environ["JOBS_IMAGE"],
    "experiment_id": os.environ["EXPERIMENT_ID"] or None,
    "submit_status": os.environ["SUBMIT_STATUS"],
    "collect_status": os.environ["COLLECT_STATUS"],
    "artifacts": {
        "endpoint_health": str(smoke_dir / "endpoint_health.json"),
        "orderbook_alert": str(smoke_dir / "orderbook_alert.json"),
        "investigation_report": str(smoke_dir / "investigation_report.json"),
        "jobs_smoke_manifest": str(smoke_dir / "jobs-output" / "manifest.json"),
        "experiment": str(smoke_dir / "experiment.json"),
        "local_batch": str(smoke_dir / "local_batch.json"),
        "submit_nebius": str(smoke_dir / "submit_nebius.json"),
        "collect_artifacts": str(smoke_dir / "collect_artifacts.json"),
    },
    "responses": {
        "endpoint_health": load_json("endpoint_health.json"),
        "orderbook_alert": load_json("orderbook_alert.json"),
        "investigation_report": load_json("investigation_report.json"),
        "experiment": load_json("experiment.json"),
        "local_batch": load_json("local_batch.json"),
        "submit_nebius": load_json("submit_nebius.json"),
        "collect_artifacts": load_json("collect_artifacts.json"),
    },
}
(smoke_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
PY
}

on_error() {
  local line="$1"
  summary_status="failed"
  summary_message="serverless smoke failed near line ${line}"
  write_summary || true
}
trap 'on_error "$LINENO"' ERR

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf "%s\n" "Required command not found: $1" >&2
    exit 2
  fi
}

curl_json() {
  local method="$1"
  local url="$2"
  local payload_file="$3"
  local output_file="$4"
  local args=(-fsS -X "${method}" -H "Content-Type: application/json")
  if [[ -n "${ENDPOINT_TOKEN:-}" ]]; then
    args+=(-H "Authorization: Bearer ${ENDPOINT_TOKEN}")
  fi
  if [[ -n "${payload_file}" ]]; then
    args+=(--data @"${payload_file}")
  fi
  curl "${args[@]}" "${url}" -o "${output_file}"
}

backend_json() {
  local method="$1"
  local path="$2"
  local payload_file="$3"
  local output_file="$4"
  local args=(-fsS -X "${method}" -H "Content-Type: application/json")
  if [[ -n "${payload_file}" ]]; then
    args+=(--data @"${payload_file}")
  fi
  curl "${args[@]}" "${BACKEND_BASE_URL%/}${path}" -o "${output_file}"
}

printf "%s\n" "1. Verifying smoke environment"
require_command curl
require_command docker
require_command "${PYTHON_BIN}"

cat > "${SMOKE_DIR}/orderbook_payload.json" <<'JSON'
{
  "bids": [{"price": 68120, "quantity": 12.4, "owner": "abuser"}],
  "asks": [{"price": 68130, "quantity": 1.8, "owner": "normal"}],
  "features": {
    "wall_size_ratio": 8.2,
    "message_rate": 21.0,
    "cancel_to_trade_ratio": 5.4,
    "depth_change_pct": 0.38,
    "imbalance": 0.72
  },
  "scenario_hint": "spoofing_like_wall",
  "tick": 12
}
JSON

cat > "${SMOKE_DIR}/investigation_payload.json" <<'JSON'
{
  "scenario_trace": {"scenario": "spoofing_like_wall", "run_id": "serverless-smoke"},
  "alerts": [{"detector": "spoofing_like", "confidence": 0.91}],
  "metrics": {"precision": 0.91, "recall": 0.88, "f1": 0.895, "avg_detection_latency_ms": 750}
}
JSON

printf "%s\n" "2. Checking endpoint health at ${ENDPOINT_BASE_URL%/}/health"
curl_json GET "${ENDPOINT_BASE_URL%/}/health" "" "${SMOKE_DIR}/endpoint_health.json"

printf "%s\n" "3. Calling /orderbook-alert"
curl_json POST "${ENDPOINT_BASE_URL%/}/orderbook-alert" "${SMOKE_DIR}/orderbook_payload.json" "${SMOKE_DIR}/orderbook_alert.json"

printf "%s\n" "4. Calling /investigation-report"
curl_json POST "${ENDPOINT_BASE_URL%/}/investigation-report" "${SMOKE_DIR}/investigation_payload.json" "${SMOKE_DIR}/investigation_report.json"

printf "%s\n" "5. Running jobs image 3-run smoke with ${JOBS_IMAGE}"
rm -rf "${SMOKE_DIR}/jobs-output"
mkdir -p "${SMOKE_DIR}/jobs-output"
docker run --rm \
  -v "${SMOKE_ABS_DIR}/jobs-output:/job/outputs/serverless-smoke" \
  "${JOBS_IMAGE}" \
  python /job/serverless/jobs/run_batch_experiments.py \
  --runs 3 \
  --batch-size 2 \
  --scenarios normal_market,spoofing_like_wall \
  --output /job/outputs/serverless-smoke \
  > "${SMOKE_DIR}/jobs_smoke_stdout.json"

printf "%s\n" "6. Creating backend experiment with 10 attacks at ${BACKEND_BASE_URL%/}"
cat > "${SMOKE_DIR}/experiment_create_payload.json" <<'JSON'
{
  "name": "Serverless smoke experiment",
  "attack_count": 10,
  "batch_size": 5,
  "scenarios": ["normal_market", "spoofing_like_wall", "layering_like", "quote_stuffing", "liquidity_evaporation"],
  "seed": 2026,
  "nebius_mode": "real_nebius_pending"
}
JSON
backend_json POST "/api/experiments" "${SMOKE_DIR}/experiment_create_payload.json" "${SMOKE_DIR}/experiment.json"
EXPERIMENT_ID="$(SMOKE_DIR="${SMOKE_DIR}" "${PYTHON_BIN}" - <<'PY'
import json
import os
from pathlib import Path
print(json.loads((Path(os.environ["SMOKE_DIR"]) / "experiment.json").read_text(encoding="utf-8"))["id"])
PY
)"

printf "%s\n" "7. Running local batch for ${EXPERIMENT_ID}"
backend_json POST "/api/experiments/${EXPERIMENT_ID}/run-local-batch" "" "${SMOKE_DIR}/local_batch.json"

printf "%s\n" "8. Optional Nebius job submit"
if [[ -n "${NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE:-}" ]]; then
  SUBMIT_ENABLED="true"
  backend_json POST "/api/experiments/${EXPERIMENT_ID}/submit-nebius" "" "${SMOKE_DIR}/submit_nebius.json"
  SUBMIT_STATUS="$(SMOKE_DIR="${SMOKE_DIR}" "${PYTHON_BIN}" - <<'PY'
import json
import os
from pathlib import Path
payload = json.loads((Path(os.environ["SMOKE_DIR"]) / "submit_nebius.json").read_text(encoding="utf-8"))
print(payload.get("status", "unknown"))
PY
)"
else
  SUBMIT_STATUS="pending_not_configured"
  cat > "${SMOKE_DIR}/submit_nebius.json" <<JSON
{"status":"real_nebius_pending","message":"NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE is not configured; real Nebius job submit skipped."}
JSON
fi

printf "%s\n" "9. Collecting artifacts if available"
if [[ "${SUBMIT_ENABLED}" == "true" || -n "${NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE:-}" ]]; then
  backend_json POST "/api/experiments/${EXPERIMENT_ID}/collect-nebius-artifacts" "" "${SMOKE_DIR}/collect_artifacts.json"
  COLLECT_STATUS="$(SMOKE_DIR="${SMOKE_DIR}" "${PYTHON_BIN}" - <<'PY'
import json
import os
from pathlib import Path
payload = json.loads((Path(os.environ["SMOKE_DIR"]) / "collect_artifacts.json").read_text(encoding="utf-8"))
print(payload.get("status", "unknown"))
PY
)"
else
  COLLECT_STATUS="pending_not_configured"
  cat > "${SMOKE_DIR}/collect_artifacts.json" <<JSON
{"status":"cloud_artifacts_pending","message":"Real Nebius job artifacts are not configured for this smoke run."}
JSON
fi

printf "%s\n" "10. Writing summary"
summary_status="passed"
summary_message="serverless smoke completed; real Nebius submit/artifact collection may be pending when not configured"
write_summary

printf "%s\n" "Serverless smoke summary: ${SMOKE_DIR}/summary.json"
