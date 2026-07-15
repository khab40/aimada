#!/usr/bin/env bash
set -euo pipefail

NAME="${NEBIUS_ENDPOINT_NAME:-lob-arena-ai-endpoint}"
IMAGE="${ENDPOINT_IMAGE:-${NEBIUS_ENDPOINT_IMAGE:-ghcr.io/khab40/lob-arena-endpoint:vllm-qwen-v11}}"
PLATFORM="${NEBIUS_ENDPOINT_PLATFORM:-gpu-l40s-d}"
PRESET="${NEBIUS_ENDPOINT_PRESET:-1gpu-16vcpu-96gb}"
DISK_SIZE="${NEBIUS_ENDPOINT_DISK_SIZE:-200Gi}"
CONTAINER_PORT="${NEBIUS_ENDPOINT_PORT:-9000}"
AUTH="${NEBIUS_ENDPOINT_AUTH:-token}"
ASYNC="${NEBIUS_ENDPOINT_ASYNC:-false}"
MODE="${NEBIUS_ENDPOINT_MODE:-local_vllm}"
LOCAL_VLLM_MODEL="${LOCAL_VLLM_MODEL:-Qwen/Qwen2.5-14B-Instruct}"
LOCAL_VLLM_HOST="${LOCAL_VLLM_HOST:-127.0.0.1}"
LOCAL_VLLM_PORT="${LOCAL_VLLM_PORT:-8001}"
LOCAL_VLLM_BASE_URL="${LOCAL_VLLM_BASE_URL:-http://${LOCAL_VLLM_HOST}:${LOCAL_VLLM_PORT}/v1}"
LOCAL_VLLM_DTYPE="${LOCAL_VLLM_DTYPE:-auto}"
LOCAL_VLLM_GPU_MEMORY_UTILIZATION="${LOCAL_VLLM_GPU_MEMORY_UTILIZATION:-0.90}"
LOCAL_VLLM_MAX_MODEL_LEN="${LOCAL_VLLM_MAX_MODEL_LEN:-16384}"
LOCAL_VLLM_ENABLE_PREFIX_CACHING="${LOCAL_VLLM_ENABLE_PREFIX_CACHING:-true}"
LOCAL_VLLM_MAX_NUM_SEQS="${LOCAL_VLLM_MAX_NUM_SEQS:-16}"
LOCAL_VLLM_TRUST_REMOTE_CODE="${LOCAL_VLLM_TRUST_REMOTE_CODE:-true}"

if [[ -z "${NEBIUS_SUBNET_ID:-}" ]]; then
  printf "%s\n" "NEBIUS_SUBNET_ID is required." >&2
  exit 2
fi

args=(
  nebius ai endpoint create
  --name "${NAME}"
  --image "${IMAGE}"
  --platform "${PLATFORM}"
  --preset "${PRESET}"
  --disk-size "${DISK_SIZE}"
  --subnet-id "${NEBIUS_SUBNET_ID}"
  --container-port "${CONTAINER_PORT}"
  --public
  --auth "${AUTH}"
  --env "NEBIUS_ENDPOINT_MODE=${MODE}"
  --env "NEBIUS_REQUEST_TIMEOUT_SECONDS=${NEBIUS_REQUEST_TIMEOUT_SECONDS:-180}"
  --env "LOCAL_VLLM_BASE_URL=${LOCAL_VLLM_BASE_URL}"
  --env "LOCAL_VLLM_MODEL=${LOCAL_VLLM_MODEL}"
  --env "LOCAL_VLLM_HOST=${LOCAL_VLLM_HOST}"
  --env "LOCAL_VLLM_PORT=${LOCAL_VLLM_PORT}"
  --env "LOCAL_VLLM_DTYPE=${LOCAL_VLLM_DTYPE}"
  --env "LOCAL_VLLM_GPU_MEMORY_UTILIZATION=${LOCAL_VLLM_GPU_MEMORY_UTILIZATION}"
  --env "LOCAL_VLLM_MAX_MODEL_LEN=${LOCAL_VLLM_MAX_MODEL_LEN}"
  --env "LOCAL_VLLM_ENABLE_PREFIX_CACHING=${LOCAL_VLLM_ENABLE_PREFIX_CACHING}"
  --env "LOCAL_VLLM_MAX_NUM_SEQS=${LOCAL_VLLM_MAX_NUM_SEQS}"
  --env "LOCAL_VLLM_TRUST_REMOTE_CODE=${LOCAL_VLLM_TRUST_REMOTE_CODE}"
  --format json
)

if [[ -n "${NEBIUS_PARENT_ID:-}" ]]; then
  args+=(--parent-id "${NEBIUS_PARENT_ID}")
fi

if [[ "${ASYNC,,}" =~ ^(1|true|yes|on)$ ]]; then
  args+=(--async)
fi

if [[ "${AUTH}" == "token" ]]; then
  if [[ -n "${NEBIUS_ENDPOINT_TOKEN_SECRET:-}" ]]; then
    args+=(--token-secret "${NEBIUS_ENDPOINT_TOKEN_SECRET}")
  else
    if [[ -z "${ENDPOINT_TOKEN:-}" ]]; then
      printf "%s\n" "ENDPOINT_TOKEN or NEBIUS_ENDPOINT_TOKEN_SECRET is required when auth=token." >&2
      exit 2
    fi
    args+=(--token "${ENDPOINT_TOKEN}")
    printf "%s\n" "Using ENDPOINT_TOKEN from the environment. Token value is not printed."
  fi
fi

if [[ -n "${NEBIUS_VOLUME:-}" ]]; then
  args+=(--volume "${NEBIUS_VOLUME}")
fi

printf "%s\n" "Creating Nebius Serverless AI Endpoint ${NAME}"
set +e
response="$("${args[@]}" 2>&1)"
status=$?
set -e
printf "%s\n" "${response}" | sed -E \
  -e 's/("auth_token"[[:space:]]*:[[:space:]]*)"[^"]*"/\1"[redacted]"/' \
  -e 's/^(Token:[[:space:]]*).*/\1[redacted]/'
exit "${status}"
