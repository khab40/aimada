#!/usr/bin/env bash
set -euo pipefail

NAME="${NEBIUS_JOB_NAME:-market-abuse-smart-batch}"
IMAGE="${NEBIUS_JOB_IMAGE:-ghcr.io/khab40/ai-market-abuse-detection-arena-jobs:latest}"
PLATFORM="${NEBIUS_JOB_PLATFORM:-cpu-d3}"
PRESET="${NEBIUS_JOB_PRESET:-4vcpu-16gb}"
DISK_SIZE="${NEBIUS_JOB_DISK_SIZE:-100Gi}"
TIMEOUT="${NEBIUS_JOB_TIMEOUT:-1h}"
RUNS="${NEBIUS_JOB_RUNS:-1000}"
BATCH_SIZE="${NEBIUS_JOB_BATCH_SIZE:-100}"
OUTPUT_DIR="${NEBIUS_JOB_OUTPUT_DIR:-/job/outputs/serverless-batch}"
SCENARIOS="${NEBIUS_JOB_SCENARIOS:-normal_market,spoofing,layering,quote_stuffing,pump_and_cancel}"

if [[ -z "${NEBIUS_SUBNET_ID:-}" ]]; then
  printf "%s\n" "NEBIUS_SUBNET_ID is required." >&2
  exit 2
fi

args=(
  nebius ai job create
  --name "${NAME}"
  --image "${IMAGE}"
  --container-command python
  --args "/job/serverless/jobs/run_batch_experiments.py --runs ${RUNS} --batch-size ${BATCH_SIZE} --scenarios ${SCENARIOS} --output ${OUTPUT_DIR}"
  --platform "${PLATFORM}"
  --preset "${PRESET}"
  --disk-size "${DISK_SIZE}"
  --timeout "${TIMEOUT}"
  --subnet-id "${NEBIUS_SUBNET_ID}"
  --restart-policy never
  --format json
)

if [[ -n "${NEBIUS_PARENT_ID:-}" ]]; then
  args+=(--parent-id "${NEBIUS_PARENT_ID}")
fi

if [[ -n "${NEBIUS_VOLUME:-}" ]]; then
  args+=(--volume "${NEBIUS_VOLUME}")
fi

printf "%s\n" "Creating Nebius Serverless AI Job ${NAME}"
"${args[@]}"
