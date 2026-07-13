#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
PROJECT_ID=""
TENANT_ID=""
BUCKET_NAME=""
SERVICE_ACCOUNT_NAME="aimada-artifacts"
REGION="eu-north1"
APPLY=false
RESTART=false
ROTATE_KEY=false

usage() {
  printf '%s\n' \
    "Usage: $0 --project-id ID --tenant-id ID --bucket-name NAME [options]" \
    "" \
    "Options:" \
    "  --env-file PATH              Environment file to update (default: .env)." \
    "  --service-account-name NAME  Dedicated account name (default: aimada-artifacts)." \
    "  --region REGION              Object Storage region (default: eu-north1)." \
    "  --rotate-key                 Issue a replacement access key." \
    "  --apply                      Provision resources and update the env file." \
    "  --restart                    Restart and validate the real-Nebius backend." \
    "" \
    "Dry-run is the default. Secret values are never printed."
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --project-id) PROJECT_ID="$2"; shift 2 ;;
    --tenant-id) TENANT_ID="$2"; shift 2 ;;
    --bucket-name) BUCKET_NAME="$2"; shift 2 ;;
    --service-account-name) SERVICE_ACCOUNT_NAME="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --rotate-key) ROTATE_KEY=true; shift ;;
    --apply) APPLY=true; shift ;;
    --restart) RESTART=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "${PROJECT_ID}" ]] || { printf '%s\n' '--project-id is required' >&2; exit 2; }
[[ -n "${TENANT_ID}" ]] || { printf '%s\n' '--tenant-id is required' >&2; exit 2; }
[[ -n "${BUCKET_NAME}" ]] || { printf '%s\n' '--bucket-name is required' >&2; exit 2; }
[[ -f "${ENV_FILE}" ]] || { printf 'Missing env file: %s\n' "${ENV_FILE}" >&2; exit 2; }
[[ "${RESTART}" != "true" || "${APPLY}" == "true" ]] || { printf '%s\n' '--restart requires --apply' >&2; exit 2; }

printf '%s\n' \
  "Nebius artifact storage plan:" \
  "  - project: ${PROJECT_ID}" \
  "  - service account: ${SERVICE_ACCOUNT_NAME}" \
  "  - private bucket: ${BUCKET_NAME}" \
  "  - output root: s3://${BUCKET_NAME}/aimada"

if [[ "${APPLY}" != "true" ]]; then
  printf '%s\n' 'Dry-run only. Re-run with --apply to provision resources.'
  exit 0
fi

for command in nebius jq awk mktemp; do
  command -v "${command}" >/dev/null 2>&1 || { printf 'Missing command: %s\n' "${command}" >&2; exit 2; }
done

WORK="$(mktemp "${ENV_FILE}.work.XXXXXX")"
KEY_JSON="$(mktemp "${TMPDIR:-/tmp}/aimada-access-key.XXXXXX")"
RESOURCE_JSON="$(mktemp "${TMPDIR:-/tmp}/aimada-resource.XXXXXX")"
cleanup() {
  rm -f "${WORK}" "${KEY_JSON}" "${RESOURCE_JSON}"
}
trap cleanup EXIT
chmod 600 "${KEY_JSON}" "${RESOURCE_JSON}"
cp "${ENV_FILE}" "${WORK}"

set_env_value() {
  local key="$1" value="$2" next
  next="$(mktemp "${ENV_FILE}.next.XXXXXX")"
  awk -v target="${key}" -v replacement="${value}" '
    BEGIN { found = 0 }
    index($0, target "=") == 1 { print target "=" replacement; found = 1; next }
    { print }
    END { if (!found) print target "=" replacement }
  ' "${WORK}" > "${next}"
  mv "${next}" "${WORK}"
}

if nebius iam service-account get-by-name \
  --name "${SERVICE_ACCOUNT_NAME}" --parent-id "${PROJECT_ID}" \
  --format json --no-check-update > "${RESOURCE_JSON}" 2>/dev/null; then
  SERVICE_ACCOUNT_ID="$(jq -er '.metadata.id' "${RESOURCE_JSON}")"
else
  nebius iam service-account create \
    --name "${SERVICE_ACCOUNT_NAME}" --parent-id "${PROJECT_ID}" \
    --description 'AIMADA Serverless Job artifact upload and collection' \
    --format json --no-check-update --no-progress > "${RESOURCE_JSON}"
  SERVICE_ACCOUNT_ID="$(jq -er '.metadata.id' "${RESOURCE_JSON}")"
fi

nebius iam group get-by-name \
  --name editors --parent-id "${TENANT_ID}" \
  --format json --no-check-update > "${RESOURCE_JSON}"
EDITORS_GROUP_ID="$(jq -er '.metadata.id' "${RESOURCE_JSON}")"
if ! nebius iam group-membership create \
  --parent-id "${EDITORS_GROUP_ID}" --member-id "${SERVICE_ACCOUNT_ID}" \
  --format json --no-check-update --no-progress > "${RESOURCE_JSON}" 2>&1; then
  if ! grep -Eqi 'already exists|already_exists' "${RESOURCE_JSON}"; then
    printf '%s\n' 'Failed to grant artifact service-account access.' >&2
    exit 1
  fi
fi

if ! nebius storage bucket get-by-name \
  --name "${BUCKET_NAME}" --parent-id "${PROJECT_ID}" \
  --format json --no-check-update > "${RESOURCE_JSON}" 2>/dev/null; then
  nebius storage bucket create \
    --name "${BUCKET_NAME}" --parent-id "${PROJECT_ID}" \
    --max-size-bytes 10737418240 --default-storage-class standard \
    --labels app=aimada,purpose=serverless-job-artifacts \
    --format json --no-check-update --no-progress > "${RESOURCE_JSON}"
fi

EXISTING_ACCESS_KEY="$(awk -F= '$1 == "NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID" {sub(/^[^=]*=/, ""); print; exit}' "${ENV_FILE}")"
EXISTING_SECRET_KEY="$(awk -F= '$1 == "NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY" {sub(/^[^=]*=/, ""); print; exit}' "${ENV_FILE}")"
ACCESS_KEY_RESOURCE_ID=""
if [[ "${ROTATE_KEY}" == "true" || -z "${EXISTING_ACCESS_KEY}" || -z "${EXISTING_SECRET_KEY}" ]]; then
  nebius iam v2 access-key create \
    --account-service-account-id "${SERVICE_ACCOUNT_ID}" --parent-id "${PROJECT_ID}" \
    --name aimada-artifacts --description 'AIMADA Object Storage access key' \
    --secret-delivery-mode inline --format json --no-check-update --no-progress > "${KEY_JSON}"
  ACCESS_KEY_RESOURCE_ID="$(jq -er '.metadata.id' "${KEY_JSON}")"
  ACCESS_KEY="$(jq -er '.status.aws_access_key_id' "${KEY_JSON}")"
  SECRET_KEY="$(jq -er '.status.secret' "${KEY_JSON}")"
  set_env_value NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID "${ACCESS_KEY}"
  set_env_value NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY "${SECRET_KEY}"
fi

set_env_value NEBIUS_PARENT_ID "${PROJECT_ID}"
set_env_value NEBIUS_JOB_OUTPUT_URI "s3://${BUCKET_NAME}/aimada"
set_env_value NEBIUS_OBJECT_STORAGE_ENDPOINT_URL "https://storage.${REGION}.nebius.cloud"
set_env_value NEBIUS_OBJECT_STORAGE_REGION "${REGION}"
set_env_value NEBIUS_OBJECT_STORAGE_SERVICE_ACCOUNT_ID "${SERVICE_ACCOUNT_ID}"
if [[ -n "${ACCESS_KEY_RESOURCE_ID}" ]]; then
  set_env_value NEBIUS_OBJECT_STORAGE_ACCESS_KEY_RESOURCE_ID "${ACCESS_KEY_RESOURCE_ID}"
fi
SUBMIT_TEMPLATE="$(awk -F= '$1 == "NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE" {sub(/^[^=]*=/, ""); print; exit}' "${WORK}")"
if [[ -n "${SUBMIT_TEMPLATE}" && "${SUBMIT_TEMPLATE}" != *'{object_storage_env_args}'* ]]; then
  set_env_value NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE "${SUBMIT_TEMPLATE} {object_storage_env_args}"
fi

chmod 600 "${WORK}"
mv "${WORK}" "${ENV_FILE}"

if [[ "${RESTART}" == "true" ]]; then
  docker compose -f "${ROOT_DIR}/docker-compose.yml" -f "${ROOT_DIR}/docker-compose.nebius.yml" \
    --env-file "${ENV_FILE}" up -d --build --no-deps backend
  docker compose -f "${ROOT_DIR}/docker-compose.yml" -f "${ROOT_DIR}/docker-compose.nebius.yml" \
    --env-file "${ENV_FILE}" exec -T backend \
    sh -c 'AWS_ACCESS_KEY_ID="$NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID" \
      AWS_SECRET_ACCESS_KEY="$NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY" \
      AWS_SESSION_TOKEN="$NEBIUS_OBJECT_STORAGE_SESSION_TOKEN" \
      AWS_DEFAULT_REGION="$NEBIUS_OBJECT_STORAGE_REGION" \
      aws --endpoint-url "$NEBIUS_OBJECT_STORAGE_ENDPOINT_URL" s3 ls "$1" >/dev/null' \
    _ "s3://${BUCKET_NAME}"
fi

printf '%s\n' 'Nebius artifact storage configured. Credentials were not printed.'
