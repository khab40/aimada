#!/usr/bin/env bash
set -euo pipefail

OWNER="${GHCR_OWNER:-khab40}"
TAG="${IMAGE_TAG:-latest}"
PUSH="${PUSH:-false}"
PLATFORM="${IMAGE_PLATFORM:-linux/amd64}"

ENDPOINT_IMAGE="ghcr.io/${OWNER}/ai-market-abuse-detection-arena-endpoint:${TAG}"
JOBS_IMAGE="ghcr.io/${OWNER}/ai-market-abuse-detection-arena-jobs:${TAG}"

cd "$(dirname "$0")/.."

printf "%s\n" "Building Nebius serverless images"
printf "%s\n" "Endpoint image: ${ENDPOINT_IMAGE}"
printf "%s\n" "Jobs image:     ${JOBS_IMAGE}"
printf "%s\n" "Platform:       ${PLATFORM}"

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
