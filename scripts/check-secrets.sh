#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${1:-${ROOT_DIR}/.env}"

[[ -f "${ENV_FILE}" ]] || { printf 'Missing env file: %s\n' "${ENV_FILE}" >&2; exit 2; }

if [[ "${ENV_FILE}" == "${ROOT_DIR}/.env" ]]; then
  git -C "${ROOT_DIR}" check-ignore -q .env || { printf '%s\n' '.env is not ignored by Git' >&2; exit 1; }
fi

SERVERLESS_MODE="$(awk -F= '$1 == "NEBIUS_SERVERLESS_ENABLED" {print $2; exit}' "${ENV_FILE}")"
case "${SERVERLESS_MODE}" in
  true)
    grep -q '^ENDPOINT_TOKEN=.' "${ENV_FILE}" || {
      printf '%s\n' 'ENDPOINT_TOKEN is required when NEBIUS_SERVERLESS_ENABLED=true' >&2
      exit 1
    }
    ;;
  false)
    if grep -q '^ENDPOINT_TOKEN=.' "${ENV_FILE}"; then
      printf '%s\n' 'ENDPOINT_TOKEN must be empty when NEBIUS_SERVERLESS_ENABLED=false' >&2
      exit 1
    fi
    ;;
  "")
    grep -q '^ENDPOINT_TOKEN=.' "${ENV_FILE}" || { printf '%s\n' 'ENDPOINT_TOKEN is missing' >&2; exit 1; }
    ;;
  *)
    printf '%s\n' 'NEBIUS_SERVERLESS_ENABLED must be true or false' >&2
    exit 1
    ;;
esac

if git -C "${ROOT_DIR}" grep -nE '(GOCSPX-[A-Za-z0-9_-]{12,}|ENDPOINT_TOKEN=[A-Fa-f0-9]{32,}([[:space:]]|$)|NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY=[A-Za-z0-9/+_-]{24,}([[:space:]]|$))' -- ':!scripts/check-secrets.sh'; then
  printf '%s\n' 'Potential secret found in tracked files' >&2
  exit 1
fi

printf '%s\n' 'Secret checks passed.'
