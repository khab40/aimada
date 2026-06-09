#!/usr/bin/env bash
set -euo pipefail

NAME="${NEBIUS_ENDPOINT_NAME:-market-abuse-arena-ai-endpoint}"
ENDPOINT_ID="${NEBIUS_ENDPOINT_ID:-}"

if [[ -z "${ENDPOINT_ID}" ]]; then
  ENDPOINT_ID="$(nebius ai endpoint get-by-name --name "${NAME}" --format jsonpath='{.metadata.id}')"
fi

ENDPOINT_IP="$(nebius ai endpoint get "${ENDPOINT_ID}" --format jsonpath='{.status.public_endpoints[0]}')"
printf "http://%s\n" "${ENDPOINT_IP}"
