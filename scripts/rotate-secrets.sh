#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
IMPORT_FILE=""
APPLY=false
RESTART=false

usage() {
  printf '%s\n' \
    "Usage: $0 [--env-file PATH] [--import-env PATH] [--apply] [--restart]" \
    "" \
    "Generates new AIMADA_JWT_SECRET and ENDPOINT_TOKEN values." \
    "--import-env accepts only GOOGLE_CLIENT_SECRET and Nebius Object Storage keys." \
    "Dry-run is the default; secret values are never printed."
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --import-env) IMPORT_FILE="$2"; shift 2 ;;
    --apply) APPLY=true; shift ;;
    --restart) RESTART=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -f "${ENV_FILE}" ]] || { printf 'Missing env file: %s\n' "${ENV_FILE}" >&2; exit 2; }
[[ -z "${IMPORT_FILE}" || -f "${IMPORT_FILE}" ]] || { printf 'Missing import file: %s\n' "${IMPORT_FILE}" >&2; exit 2; }
[[ "${RESTART}" != "true" || "${APPLY}" == "true" ]] || { printf '%s\n' '--restart requires --apply' >&2; exit 2; }
command -v openssl >/dev/null 2>&1 || { printf '%s\n' 'openssl is required' >&2; exit 2; }

JWT_SECRET="$(openssl rand -base64 48 | tr -d '\n')"
ENDPOINT_TOKEN_VALUE="$(openssl rand -hex 32)"
ROTATION_KEYS=(AIMADA_JWT_SECRET ENDPOINT_TOKEN)
ROTATION_VALUES=("${JWT_SECRET}" "${ENDPOINT_TOKEN_VALUE}")

if [[ -n "${IMPORT_FILE}" ]]; then
  while IFS='=' read -r key value || [[ -n "${key:-}" ]]; do
    [[ -z "${key:-}" || "${key}" == \#* ]] && continue
    case "${key}" in
      GOOGLE_CLIENT_SECRET|NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID|NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY|NEBIUS_OBJECT_STORAGE_SESSION_TOKEN)
        [[ -n "${value}" ]] || { printf 'Imported value is empty: %s\n' "${key}" >&2; exit 2; }
        ROTATION_KEYS+=("${key}")
        ROTATION_VALUES+=("${value}")
        ;;
      *) printf 'Import key is not allowed: %s\n' "${key}" >&2; exit 2 ;;
    esac
  done < "${IMPORT_FILE}"
fi

printf 'Rotation plan for %s:\n' "${ENV_FILE}"
for index in "${!ROTATION_KEYS[@]}"; do
  printf '  - %s\n' "${ROTATION_KEYS[${index}]}"
done

if [[ "${APPLY}" != "true" ]]; then
  printf '%s\n' 'Dry-run only. Re-run with --apply to update the file.'
  exit 0
fi

ORIGINAL="$(mktemp "${ENV_FILE}.rollback.XXXXXX")"
WORK="$(mktemp "${ENV_FILE}.work.XXXXXX")"
cleanup() {
  rm -f "${ORIGINAL}" "${WORK}"
}
trap cleanup EXIT
cp -p "${ENV_FILE}" "${ORIGINAL}"
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

for index in "${!ROTATION_KEYS[@]}"; do
  set_env_value "${ROTATION_KEYS[${index}]}" "${ROTATION_VALUES[${index}]}"
done

chmod 600 "${WORK}"
mv "${WORK}" "${ENV_FILE}"

if [[ "${RESTART}" == "true" ]]; then
  if ! docker compose --env-file "${ENV_FILE}" up -d --build --force-recreate; then
    mv "${ORIGINAL}" "${ENV_FILE}"
    printf '%s\n' 'Compose restart failed; restored the original env file.' >&2
    exit 1
  fi
  if ! curl -fsS http://localhost:8000/health >/dev/null; then
    mv "${ORIGINAL}" "${ENV_FILE}"
    printf '%s\n' 'Health check failed; restored the original env file. Restart again to apply it.' >&2
    exit 1
  fi
fi

printf '%s\n' 'Rotation applied. Validate new provider credentials, then disable/delete the old credentials.'
