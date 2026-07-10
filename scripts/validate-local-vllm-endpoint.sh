#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-validate}"
ENDPOINT_BASE_URL="${NEBIUS_ENDPOINT_BASE_URL:-}"
ENDPOINT_TOKEN="${ENDPOINT_TOKEN:-}"
OUTPUT_DIR="${LOCAL_VLLM_VALIDATION_DIR:-outputs/local-vllm-endpoint-validation}"
EXPECTED_MODEL="${LOCAL_VLLM_MODEL:-Qwen/Qwen2.5-1.5B-Instruct}"
CURL_MAX_TIME="${ENDPOINT_CURL_MAX_TIME_SECONDS:-600}"
PYTHON_BIN="${PYTHON:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

mkdir -p "${OUTPUT_DIR}"

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    printf "%s\n" "${name} is required." >&2
    exit 2
  fi
}

curl_endpoint() {
  local method="$1"
  local url="$2"
  local payload_file="$3"
  local output_file="$4"
  local args=(-fsS --max-time "${CURL_MAX_TIME}" -X "${method}" -H "Content-Type: application/json")
  if [[ -n "${ENDPOINT_TOKEN}" ]]; then
    args+=(-H "Authorization: Bearer ${ENDPOINT_TOKEN}")
  fi
  if [[ -n "${payload_file}" ]]; then
    args+=(--data @"${payload_file}")
  fi
  curl "${args[@]}" "${url}" -o "${output_file}"
}

validate_json() {
  "${PYTHON_BIN}" - "$OUTPUT_DIR" "$EXPECTED_MODEL" <<'PY'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
expected_model = sys.argv[2]

health = json.loads((output_dir / "health.json").read_text(encoding="utf-8"))
orderbook = json.loads((output_dir / "orderbook_alert.json").read_text(encoding="utf-8"))
report = json.loads((output_dir / "investigation_report.json").read_text(encoding="utf-8"))

checks = [
    ("health.endpoint_mode", health.get("endpoint_mode") == "local_vllm"),
    ("health.model_mode", health.get("model_mode") == "local_vllm"),
    ("health.local_vllm_model", health.get("local_vllm_model") == expected_model),
    ("orderbook.model_mode", orderbook.get("model_mode") == "local_vllm"),
    ("orderbook.model", orderbook.get("model") == expected_model),
    ("orderbook.latency_ms", float(orderbook.get("latency_ms", 0)) > 0),
    ("report.model_mode", report.get("model_mode") == "local_vllm"),
    ("report.model", report.get("model") == expected_model),
    ("report.latency_ms", float(report.get("latency_ms", 0)) > 0),
]
failed = [name for name, ok in checks if not ok]
if failed:
    print("Local-vLLM endpoint validation failed:", ", ".join(failed), file=sys.stderr)
    print(json.dumps({"health": health, "orderbook_alert": orderbook, "investigation_report": report}, indent=2), file=sys.stderr)
    sys.exit(1)

summary = {
    "status": "passed",
    "endpoint_mode": health["endpoint_mode"],
    "model_mode": health["model_mode"],
    "local_vllm_model": health["local_vllm_model"],
    "orderbook_latency_ms": orderbook["latency_ms"],
    "investigation_report_latency_ms": report["latency_ms"],
}
(output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
PY
}

case "${COMMAND}" in
  validate)
    require_env NEBIUS_ENDPOINT_BASE_URL
    require_env ENDPOINT_TOKEN
    command -v curl >/dev/null 2>&1 || { printf "%s\n" "curl is required." >&2; exit 2; }
    command -v "${PYTHON_BIN}" >/dev/null 2>&1 || { printf "%s\n" "${PYTHON_BIN} is required." >&2; exit 2; }

    cat > "${OUTPUT_DIR}/orderbook_payload.json" <<'JSON'
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
  "scenario_hint": "spoofing",
  "tick": 12
}
JSON

    cat > "${OUTPUT_DIR}/investigation_payload.json" <<'JSON'
{
  "scenario_trace": {"scenario": "spoofing", "run_id": "local-vllm-cloud-validation"},
  "alerts": [{"detector": "spoofing_like", "confidence": 0.91}],
  "metrics": {"precision": 0.91, "recall": 0.88, "f1": 0.895, "avg_detection_latency_ms": 750}
}
JSON

    printf "%s\n" "Checking ${NEBIUS_ENDPOINT_BASE_URL%/}/health"
    curl_endpoint GET "${NEBIUS_ENDPOINT_BASE_URL%/}/health" "" "${OUTPUT_DIR}/health.json"

    printf "%s\n" "Calling ${NEBIUS_ENDPOINT_BASE_URL%/}/orderbook-alert"
    curl_endpoint POST "${NEBIUS_ENDPOINT_BASE_URL%/}/orderbook-alert" "${OUTPUT_DIR}/orderbook_payload.json" "${OUTPUT_DIR}/orderbook_alert.json"

    printf "%s\n" "Calling ${NEBIUS_ENDPOINT_BASE_URL%/}/investigation-report"
    curl_endpoint POST "${NEBIUS_ENDPOINT_BASE_URL%/}/investigation-report" "${OUTPUT_DIR}/investigation_payload.json" "${OUTPUT_DIR}/investigation_report.json"

    validate_json
    ;;
  logs)
    require_env NEBIUS_ENDPOINT_ID
    command -v nebius >/dev/null 2>&1 || { printf "%s\n" "nebius CLI is required." >&2; exit 2; }
    nebius ai endpoint logs "${NEBIUS_ENDPOINT_ID}" --follow
    ;;
  *)
    printf "%s\n" "Usage: $0 validate|logs" >&2
    exit 2
    ;;
esac
