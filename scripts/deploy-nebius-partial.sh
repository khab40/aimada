#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/deploy-nebius-partial.sh [options]

Default scope:
  - build and push endpoint + jobs images for linux/amd64
  - create or reuse the Nebius GPU local-vLLM endpoint
  - write backend/job wiring to outputs/deployments/nebius-partial-latest.env
  - do not deploy frontend, backend, or agent-runner to Nebius
  - do not submit a sample Serverless Job unless requested

Options:
  --targets LIST        Comma-separated targets. Default: images,endpoint,backend-env
                        Available: images,endpoint,backend-env,sample-job
  --dry-run            Print actions without running them.
  --skip-build         Skip image build/push.
  --sample-job         Include sample-job target.
  -h, --help           Show this help.

Key env:
  IMAGE_NAMESPACE=ghcr.io/khab40
  TAG=latest
  NEBIUS_ENDPOINT_IMAGE=<endpoint image>
  NEBIUS_JOB_IMAGE=<jobs image>
  NEBIUS_SUBNET_ID=<subnet id>
  NEBIUS_PARENT_ID=<optional project id>
  ENDPOINT_TOKEN=<endpoint bearer token>
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=false
SKIP_BUILD=false
TARGETS="${NEBIUS_DEPLOY_TARGETS:-images,endpoint,backend-env}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --targets)
      TARGETS="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --sample-job)
      TARGETS="${TARGETS},sample-job"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf "%s\n" "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

load_env_file() {
  local file="$1"
  local line key value
  [[ -f "${file}" ]] || return 0
  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    [[ "${key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    [[ -z "${!key+x}" ]] || continue
    export "${key}=${value}"
  done < "${file}"
}

load_env_file "${ROOT_DIR}/.env"

IMAGE_NAMESPACE="${IMAGE_NAMESPACE:-ghcr.io/khab40}"
TAG="${TAG:-latest}"
PLATFORM="${PLATFORM:-linux/amd64}"
NEBIUS_ENDPOINT_MODE="${NEBIUS_ENDPOINT_MODE:-local_vllm}"
NEBIUS_ENDPOINT_PLATFORM="${NEBIUS_ENDPOINT_PLATFORM:-gpu-l40s-d}"
NEBIUS_ENDPOINT_PRESET="${NEBIUS_ENDPOINT_PRESET:-1gpu-16vcpu-96gb}"
NEBIUS_ENDPOINT_IMAGE="${NEBIUS_ENDPOINT_IMAGE:-${ENDPOINT_IMAGE:-${IMAGE_NAMESPACE}/lob-arena-endpoint:${TAG}}}"
NEBIUS_JOB_IMAGE="${NEBIUS_JOB_IMAGE:-${JOBS_IMAGE:-${IMAGE_NAMESPACE}/lob-arena-jobs:${TAG}}}"
NEBIUS_ENDPOINT_NAME="${NEBIUS_ENDPOINT_NAME:-lob-arena-ai-endpoint}"
NEBIUS_PARTIAL_REPORT="${NEBIUS_PARTIAL_REPORT:-${ROOT_DIR}/outputs/deployments/nebius-partial-latest.env}"
DEFAULT_JOB_SUBMIT_COMMAND_TEMPLATE='nebius ai job create --async --image {image} --container-command python --args {job_args} --platform cpu-d3 --preset 4vcpu-16gb --disk-size 100Gi --timeout 1h {subnet_id_arg} {parent_id_arg} {volume_arg} {object_storage_env_args} --restart-policy never --format json'
DEFAULT_JOB_STATUS_COMMAND_TEMPLATE='nebius ai job get {job_id} --format json'
DEFAULT_JOB_LOGS_COMMAND_TEMPLATE='nebius ai job logs {job_id}'

contains_target() {
  case ",${TARGETS}," in
    *",$1,"*) return 0 ;;
    *) return 1 ;;
  esac
}

run() {
  printf "+ "
  for item in "$@"; do
    printf "%q " "${item}"
  done
  printf "\n"
  if [[ "${DRY_RUN}" != "true" ]]; then
    "$@"
  fi
}

require_cmd() {
  if [[ "${DRY_RUN}" == "true" ]]; then
    return
  fi
  if ! command -v "$1" >/dev/null 2>&1; then
    printf "%s\n" "Missing required command: $1" >&2
    exit 2
  fi
}

require_env() {
  local missing=0
  for name in "$@"; do
    if [[ -z "${!name:-}" ]]; then
      printf "%s\n" "Missing required environment variable: ${name}" >&2
      missing=1
    fi
  done
  if [[ "${missing}" -ne 0 ]]; then
    exit 2
  fi
}

build_and_push_images() {
  if [[ "${SKIP_BUILD}" == "true" ]]; then
    printf "%s\n" "Skipping image build/push."
    return
  fi
  require_cmd docker
  run "${ROOT_DIR}/scripts/build-serverless-images.sh"
}

endpoint_exists() {
  [[ "${DRY_RUN}" != "true" ]] || return 1
  nebius ai endpoint get-by-name --name "${NEBIUS_ENDPOINT_NAME}" --format jsonpath='{.metadata.id}' >/dev/null 2>&1
}

deploy_endpoint() {
  require_cmd nebius
  require_env NEBIUS_SUBNET_ID
  if [[ "${NEBIUS_ENDPOINT_AUTH:-token}" == "token" && -z "${NEBIUS_ENDPOINT_TOKEN_SECRET:-}" ]]; then
    require_env ENDPOINT_TOKEN
  fi

  export ENDPOINT_IMAGE="${NEBIUS_ENDPOINT_IMAGE}"
  export NEBIUS_ENDPOINT_IMAGE
  export NEBIUS_ENDPOINT_MODE
  export NEBIUS_ENDPOINT_PLATFORM
  export NEBIUS_ENDPOINT_PRESET
  export NEBIUS_ENDPOINT_NAME

  if endpoint_exists && [[ "${NEBIUS_RECREATE_ENDPOINT:-false}" != "true" ]]; then
    printf "%s\n" "Nebius endpoint ${NEBIUS_ENDPOINT_NAME} already exists; reusing it."
  else
    mkdir -p "${ROOT_DIR}/outputs/deployments"
    if [[ "${DRY_RUN}" == "true" ]]; then
      run "${ROOT_DIR}/scripts/create-nebius-ai-endpoint.sh"
    else
      "${ROOT_DIR}/scripts/create-nebius-ai-endpoint.sh" | tee "${ROOT_DIR}/outputs/deployments/nebius-endpoint-create.json"
    fi
  fi

  if [[ "${DRY_RUN}" != "true" ]]; then
    NEBIUS_ENDPOINT_BASE_URL="$("${ROOT_DIR}/scripts/nebius-endpoint-url.sh")"
    export NEBIUS_ENDPOINT_BASE_URL
    printf "%s\n" "Resolved endpoint URL: ${NEBIUS_ENDPOINT_BASE_URL}"
  fi
}

write_backend_env() {
  if [[ "${DRY_RUN}" == "true" ]]; then
    printf "%s\n" "Would write backend wiring to ${NEBIUS_PARTIAL_REPORT}"
    return
  fi
  mkdir -p "$(dirname "${NEBIUS_PARTIAL_REPORT}")"
  write_env_var() {
    printf "%s=%q\n" "$1" "$2"
  }
  {
    write_env_var NEBIUS_DEPLOYMENT_SCOPE partial-serverless
    write_env_var NEBIUS_SERVERLESS_ENABLED true
    write_env_var NEBIUS_CLI_CONFIG_DIR "${NEBIUS_CLI_CONFIG_DIR:-${HOME}/.nebius}"
    write_env_var NEBIUS_ENDPOINT_MODE "${NEBIUS_ENDPOINT_MODE}"
    write_env_var NEBIUS_ENDPOINT_BASE_URL "${NEBIUS_ENDPOINT_BASE_URL:-}"
    write_env_var NEBIUS_ENDPOINT_IMAGE "${NEBIUS_ENDPOINT_IMAGE}"
    write_env_var ENDPOINT_IMAGE "${NEBIUS_ENDPOINT_IMAGE}"
    write_env_var NEBIUS_JOB_IMAGE "${NEBIUS_JOB_IMAGE}"
    write_env_var NEBIUS_SUBNET_ID "${NEBIUS_SUBNET_ID:-}"
    write_env_var NEBIUS_PARENT_ID "${NEBIUS_PARENT_ID:-}"
    write_env_var NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE "${NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE:-${DEFAULT_JOB_SUBMIT_COMMAND_TEMPLATE}}"
    write_env_var NEBIUS_JOB_STATUS_COMMAND_TEMPLATE "${NEBIUS_JOB_STATUS_COMMAND_TEMPLATE:-${DEFAULT_JOB_STATUS_COMMAND_TEMPLATE}}"
    write_env_var NEBIUS_JOB_LOGS_COMMAND_TEMPLATE "${NEBIUS_JOB_LOGS_COMMAND_TEMPLATE:-${DEFAULT_JOB_LOGS_COMMAND_TEMPLATE}}"
    write_env_var NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE "${NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE:-}"
    write_env_var NEBIUS_EVIDENCE_ARCHIVE_ENABLED "${NEBIUS_EVIDENCE_ARCHIVE_ENABLED:-true}"
  } > "${NEBIUS_PARTIAL_REPORT}"
  printf "%s\n" "Wrote backend wiring: ${NEBIUS_PARTIAL_REPORT}"
}

submit_sample_job() {
  require_cmd nebius
  require_env NEBIUS_SUBNET_ID
  export NEBIUS_JOB_IMAGE
  run "${ROOT_DIR}/scripts/create-nebius-ai-job.sh"
}

cd "${ROOT_DIR}"
export PUSH=true
export IMAGE_NAMESPACE TAG PLATFORM
export ENDPOINT_IMAGE="${NEBIUS_ENDPOINT_IMAGE}"
export JOBS_IMAGE="${NEBIUS_JOB_IMAGE}"

contains_target images && build_and_push_images
contains_target endpoint && deploy_endpoint
contains_target backend-env && write_backend_env
contains_target sample-job && submit_sample_job

cat <<SUMMARY

Partial Nebius deployment complete.

Current recommendation:
- Keep frontend, backend, and agent-runner local/Compose for the demo for now.
- Use Nebius AI Endpoint for GPU local-vLLM inference.
- Use Nebius Serverless Jobs for on-demand detector tournaments.
- Move backend/frontend later only if you need public multi-user access, durable uptime, or cloud-only demos.

Next local wiring:
  set -a
  . ${NEBIUS_PARTIAL_REPORT}
  set +a
  docker compose up -d --build
SUMMARY
