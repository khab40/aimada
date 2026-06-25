#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAMESPACE="${IMAGE_NAMESPACE:-${GHCR_OWNER:-ghcr.io/khab40}}"
TAG="${TAG:-${IMAGE_TAG:-latest}}"
PUSH="${PUSH:-false}"
PLATFORM="${PLATFORM:-${IMAGE_PLATFORM:-linux/amd64}}"
SMOKE="${SMOKE:-false}"

ENDPOINT_IMAGE="${ENDPOINT_IMAGE:-${IMAGE_NAMESPACE}/ai-market-abuse-detection-arena-endpoint:${TAG}}"
JOBS_IMAGE="${JOBS_IMAGE:-${IMAGE_NAMESPACE}/ai-market-abuse-detection-arena-jobs:${TAG}}"

cd "$(dirname "$0")/.."

printf "%s\n" "Building Nebius serverless images"
printf "%s\n" "Endpoint image: ${ENDPOINT_IMAGE}"
printf "%s\n" "Jobs image:     ${JOBS_IMAGE}"
printf "%s\n" "Platform:       ${PLATFORM}"
printf "%s\n" "Push:           ${PUSH}"
printf "%s\n" "Smoke:          ${SMOKE}"

BUILD_OUTPUT="--load"
if [[ "${PUSH}" == "true" ]]; then
  BUILD_OUTPUT="--push"
fi

docker buildx build \
  --platform "${PLATFORM}" \
  -f serverless/endpoint/Dockerfile \
  -t "${ENDPOINT_IMAGE}" \
  "${BUILD_OUTPUT}" \
  serverless/endpoint

docker buildx build \
  --platform "${PLATFORM}" \
  -f serverless/jobs/Dockerfile \
  -t "${JOBS_IMAGE}" \
  "${BUILD_OUTPUT}" \
  .

if [[ "${PUSH}" == "true" ]]; then
  printf "%s\n" "Pushed ${PLATFORM} images to GHCR"
else
  printf "%s\n" "Build complete. To push, run:"
  printf "%s\n" "PUSH=true ./scripts/build-serverless-images.sh"
fi

if [[ "${SMOKE}" == "true" ]]; then
  if [[ "${PUSH}" == "true" ]]; then
    printf "%s\n" "Skipping smoke tests because PUSH=true does not load images locally."
    exit 0
  fi
  printf "%s\n" "Running endpoint container health smoke"
  endpoint_container="$(docker run -d -p 127.0.0.1::9000 "${ENDPOINT_IMAGE}")"
  cleanup() {
    docker rm -f "${endpoint_container}" >/dev/null 2>&1 || true
  }
  trap cleanup EXIT

  endpoint_port=""
  for _ in $(seq 1 30); do
    endpoint_port="$(docker port "${endpoint_container}" 9000/tcp 2>/dev/null | awk -F: 'END {print $NF}')"
    if [[ -n "${endpoint_port}" ]] && curl -fsS "http://127.0.0.1:${endpoint_port}/health" >/dev/null; then
      break
    fi
    sleep 1
  done
  if [[ -z "${endpoint_port}" ]]; then
    printf "%s\n" "Endpoint container did not expose port 9000." >&2
    exit 1
  fi
  curl -fsS "http://127.0.0.1:${endpoint_port}/health" >/dev/null
  printf "%s\n" "Endpoint health smoke passed on 127.0.0.1:${endpoint_port}"

  printf "%s\n" "Running jobs container 3-run smoke"
  docker run --rm "${JOBS_IMAGE}" \
    python /job/serverless/jobs/run_batch_experiments.py \
    --runs 3 \
    --batch-size 2 \
    --scenarios normal_market,spoofing \
    --output /tmp/ai-mada-serverless-smoke
  printf "%s\n" "Jobs 3-run smoke passed"
fi
