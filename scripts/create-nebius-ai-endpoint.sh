#!/usr/bin/env bash
set -euo pipefail

NAME="${NEBIUS_ENDPOINT_NAME:-market-abuse-arena-ai-endpoint}"
IMAGE="${NEBIUS_ENDPOINT_IMAGE:-ghcr.io/khab40/ai-market-abuse-detection-arena-endpoint:latest}"
PLATFORM="${NEBIUS_ENDPOINT_PLATFORM:-cpu-d3}"
PRESET="${NEBIUS_ENDPOINT_PRESET:-4vcpu-16gb}"
DISK_SIZE="${NEBIUS_ENDPOINT_DISK_SIZE:-100Gi}"
CONTAINER_PORT="${NEBIUS_ENDPOINT_PORT:-9000}"
AUTH="${NEBIUS_ENDPOINT_AUTH:-token}"
MODE="${NEBIUS_ENDPOINT_MODE:-mock}"
BASE_URL="${NEBIUS_BASE_URL:-${NEBIUS_AI_STUDIO_BASE_URL:-https://api.tokenfactory.nebius.com/v1/}}"
MODEL="${NEBIUS_MODEL:-${NEBIUS_AI_MODEL:-meta-llama/Llama-3.3-70B-Instruct}}"

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
  --env "NEBIUS_BASE_URL=${BASE_URL}"
  --env "NEBIUS_MODEL=${MODEL}"
  --env "NEBIUS_TEMPERATURE=${NEBIUS_TEMPERATURE:-0.2}"
  --env "NEBIUS_MAX_TOKENS=${NEBIUS_MAX_TOKENS:-800}"
  --env "NEBIUS_REQUEST_TIMEOUT_SECONDS=${NEBIUS_REQUEST_TIMEOUT_SECONDS:-12}"
  --format json
)

if [[ -n "${NEBIUS_PARENT_ID:-}" ]]; then
  args+=(--parent-id "${NEBIUS_PARENT_ID}")
fi

if [[ "${AUTH}" == "token" ]]; then
  if [[ -n "${NEBIUS_ENDPOINT_TOKEN_SECRET:-}" ]]; then
    args+=(--token-secret "${NEBIUS_ENDPOINT_TOKEN_SECRET}")
  else
    if [[ -z "${NEBIUS_ENDPOINT_TOKEN:-}" ]]; then
      printf "%s\n" "NEBIUS_ENDPOINT_TOKEN or NEBIUS_ENDPOINT_TOKEN_SECRET is required when auth=token." >&2
      exit 2
    fi
    args+=(--token "${NEBIUS_ENDPOINT_TOKEN}")
    printf "%s\n" "Using NEBIUS_ENDPOINT_TOKEN from the environment. Token value is not printed."
  fi
fi

if [[ -n "${NEBIUS_API_KEY_SECRET:-}" ]]; then
  args+=(--env-secret "NEBIUS_API_KEY=${NEBIUS_API_KEY_SECRET}")
elif [[ -n "${NEBIUS_API_KEY:-}" ]]; then
  args+=(--env "NEBIUS_API_KEY=${NEBIUS_API_KEY}")
  printf "%s\n" "Using NEBIUS_API_KEY from the environment. API key value is not printed."
fi

if [[ -n "${NEBIUS_VOLUME:-}" ]]; then
  args+=(--volume "${NEBIUS_VOLUME}")
fi

printf "%s\n" "Creating Nebius Serverless AI Endpoint ${NAME}"
"${args[@]}"
