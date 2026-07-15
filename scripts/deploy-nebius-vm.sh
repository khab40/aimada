#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/deploy-nebius-vm.sh [options]

Default targets:
  images,deploy,smoke

Options:
  --targets LIST     Comma-separated targets: images,provision,deploy,smoke
  --dry-run          Print commands and generated deployment path without running remote changes.
  --skip-build       Skip local image build/push.
  -h, --help         Show this help.

Required for deploy:
  NEBIUS_VM_HOST     VM public IP or DNS name.

Recommended:
  NEBIUS_VM_USER=ubuntu
  NEBIUS_VM_SSH_KEY=~/.ssh/id_ed25519
  IMAGE_NAMESPACE=ghcr.io/<owner>
  TAG=vm-demo
  ENDPOINT_TOKEN=<endpoint bearer token>
  NEBIUS_ENDPOINT_BASE_URL=<deployed local_vllm endpoint URL>

Optional VM provisioning:
  NEBIUS_VM_CREATE_COMMAND_TEMPLATE='nebius ...'

The VM runs backend, frontend, and agent-runner only. Keep GPU local-vLLM on
Nebius Serverless Endpoint and detector batches on Nebius Serverless Jobs.
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGETS="${NEBIUS_VM_TARGETS:-images,deploy,smoke}"
DRY_RUN=false
SKIP_BUILD=false

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
TAG="${TAG:-vm-demo}"
PLATFORM="${PLATFORM:-linux/amd64}"
NEBIUS_BACKEND_IMAGE="${NEBIUS_BACKEND_IMAGE:-${IMAGE_NAMESPACE}/lob-arena-backend:${TAG}}"
NEBIUS_FRONTEND_IMAGE="${NEBIUS_FRONTEND_IMAGE:-${IMAGE_NAMESPACE}/lob-arena-frontend:${TAG}}"
NEBIUS_AGENT_RUNNER_IMAGE="${NEBIUS_AGENT_RUNNER_IMAGE:-${IMAGE_NAMESPACE}/lob-arena-agent-runner:${TAG}}"
NEBIUS_VM_USER="${NEBIUS_VM_USER:-ubuntu}"
NEBIUS_VM_APP_DIR="${NEBIUS_VM_APP_DIR:-aimada}"
NEBIUS_VM_BACKEND_PORT="${NEBIUS_VM_BACKEND_PORT:-8000}"
NEBIUS_VM_FRONTEND_PORT="${NEBIUS_VM_FRONTEND_PORT:-80}"
NEBIUS_VM_AGENT_RUNNER_REPLICAS="${NEBIUS_VM_AGENT_RUNNER_REPLICAS:-1}"
NEBIUS_VM_BOOTSTRAP_DOCKER="${NEBIUS_VM_BOOTSTRAP_DOCKER:-true}"
NEBIUS_VM_PUBLIC_BASE_URL="${NEBIUS_VM_PUBLIC_BASE_URL:-}"
NEBIUS_VM_API_BASE_URL="${NEBIUS_VM_API_BASE_URL:-}"
NEBIUS_VM_WS_BASE_URL="${NEBIUS_VM_WS_BASE_URL:-}"
NEBIUS_VM_REPORT="${NEBIUS_VM_REPORT:-${ROOT_DIR}/outputs/deployments/nebius-vm-latest.env}"

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

ssh_args() {
  local args=()
  if [[ -n "${NEBIUS_VM_SSH_KEY:-}" ]]; then
    args+=("-i" "${NEBIUS_VM_SSH_KEY}")
  fi
  args+=("-o" "StrictHostKeyChecking=accept-new")
  printf "%s\n" "${args[@]}"
}

vm_target() {
  printf "%s@%s" "${NEBIUS_VM_USER}" "${NEBIUS_VM_HOST}"
}

build_image() {
  local dockerfile="$1"
  local tag="$2"
  local context="$3"
  run docker buildx build --platform "${PLATFORM}" -f "${dockerfile}" -t "${tag}" --push "${context}"
}

build_images() {
  if [[ "${SKIP_BUILD}" == "true" ]]; then
    printf "%s\n" "Skipping VM image build/push."
    return
  fi
  require_cmd docker
  build_image "${ROOT_DIR}/backend/Dockerfile" "${NEBIUS_BACKEND_IMAGE}" "${ROOT_DIR}"
  build_image "${ROOT_DIR}/frontend/Dockerfile" "${NEBIUS_FRONTEND_IMAGE}" "${ROOT_DIR}/frontend"
  build_image "${ROOT_DIR}/agent-runner/Dockerfile" "${NEBIUS_AGENT_RUNNER_IMAGE}" "${ROOT_DIR}"
}

render_template() {
  local template="$1"
  template="${template//\{name\}/${NEBIUS_VM_NAME:-aimada-vm}}"
  template="${template//\{subnet_id\}/${NEBIUS_SUBNET_ID:-}}"
  template="${template//\{parent_id\}/${NEBIUS_PARENT_ID:-}}"
  template="${template//\{platform\}/${NEBIUS_VM_PLATFORM:-cpu-d3}}"
  template="${template//\{preset\}/${NEBIUS_VM_PRESET:-4vcpu-16gb}}"
  template="${template//\{ssh_public_key_path\}/${NEBIUS_VM_SSH_PUBLIC_KEY:-}}"
  printf "%s" "${template}"
}

provision_vm() {
  if [[ -z "${NEBIUS_VM_CREATE_COMMAND_TEMPLATE:-}" ]]; then
    printf "%s\n" "Skipping provision: NEBIUS_VM_CREATE_COMMAND_TEMPLATE is not set."
    return
  fi
  require_cmd nebius
  local rendered
  rendered="$(render_template "${NEBIUS_VM_CREATE_COMMAND_TEMPLATE}")"
  printf "+ %s\n" "${rendered}"
  if [[ "${DRY_RUN}" != "true" ]]; then
    bash -lc "${rendered}"
  fi
}

write_env_line() {
  local key="$1"
  local value="${2//$'\n'/ }"
  printf "%s=%s\n" "${key}" "${value}"
}

prepare_bundle() {
  local bundle_dir="$1"
  local public_base api_base ws_base
  public_base="${NEBIUS_VM_PUBLIC_BASE_URL}"
  if [[ -z "${public_base}" && -n "${NEBIUS_VM_HOST:-}" ]]; then
    public_base="http://${NEBIUS_VM_HOST}"
  fi
  api_base="${NEBIUS_VM_API_BASE_URL:-${public_base}:${NEBIUS_VM_BACKEND_PORT}}"
  ws_base="${NEBIUS_VM_WS_BASE_URL:-${api_base/http:/ws:}}"

  mkdir -p "${bundle_dir}"
  cp "${ROOT_DIR}/deployments/nebius-vm-compose.yml" "${bundle_dir}/docker-compose.yml"
  {
    write_env_line NEBIUS_BACKEND_IMAGE "${NEBIUS_BACKEND_IMAGE}"
    write_env_line NEBIUS_FRONTEND_IMAGE "${NEBIUS_FRONTEND_IMAGE}"
    write_env_line NEBIUS_AGENT_RUNNER_IMAGE "${NEBIUS_AGENT_RUNNER_IMAGE}"
    write_env_line NEBIUS_VM_BACKEND_PORT "${NEBIUS_VM_BACKEND_PORT}"
    write_env_line NEBIUS_VM_FRONTEND_PORT "${NEBIUS_VM_FRONTEND_PORT}"
    write_env_line VITE_API_BASE_URL "${VITE_API_BASE_URL:-${api_base}}"
    write_env_line VITE_ARENA_WS_URL "${VITE_ARENA_WS_URL:-${ws_base}/ws/arena}"
    write_env_line CORS_ALLOWED_ORIGINS "${CORS_ALLOWED_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173,${public_base}}"
    write_env_line LOG_LEVEL "${LOG_LEVEL:-INFO}"
    write_env_line ARENA_AGENT_COUNT "${ARENA_AGENT_COUNT:-3}"
    write_env_line ARENA_REMOTE_AGENT_URLS "${ARENA_REMOTE_AGENT_URLS:-http://agent-runner:9100}"
    write_env_line ARENA_REMOTE_AGENT_TIMEOUT_SECONDS "${ARENA_REMOTE_AGENT_TIMEOUT_SECONDS:-0.05}"
    write_env_line ARENA_DATA_RETENTION_DAYS "${ARENA_DATA_RETENTION_DAYS:-1}"
    write_env_line ARENA_TICK_HISTORY_INTERVAL "${ARENA_TICK_HISTORY_INTERVAL:-10}"
    write_env_line ARENA_PERSIST_ALL_EVENTS "${ARENA_PERSIST_ALL_EVENTS:-false}"
    write_env_line ENDPOINT_TOKEN "${ENDPOINT_TOKEN:-}"
    write_env_line NEBIUS_ENDPOINT_MODE "${NEBIUS_ENDPOINT_MODE:-local_vllm}"
    write_env_line NEBIUS_ENDPOINT_BASE_URL "${NEBIUS_ENDPOINT_BASE_URL:-}"
    write_env_line NEBIUS_HEALTH_TIMEOUT_SECONDS "${NEBIUS_HEALTH_TIMEOUT_SECONDS:-5}"
    write_env_line NEBIUS_JOB_IMAGE "${NEBIUS_JOB_IMAGE:-ghcr.io/khab40/lob-arena-jobs:latest}"
    write_env_line NEBIUS_JOB_OUTPUT_URI "${NEBIUS_JOB_OUTPUT_URI:-}"
    write_env_line NEBIUS_OBJECT_STORAGE_ENDPOINT_URL "${NEBIUS_OBJECT_STORAGE_ENDPOINT_URL:-https://storage.eu-north1.nebius.cloud}"
    write_env_line NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID "${NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID:-}"
    write_env_line NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY "${NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY:-}"
    write_env_line NEBIUS_OBJECT_STORAGE_SESSION_TOKEN "${NEBIUS_OBJECT_STORAGE_SESSION_TOKEN:-}"
    write_env_line NEBIUS_OBJECT_STORAGE_REGION "${NEBIUS_OBJECT_STORAGE_REGION:-eu-north1}"
    write_env_line NEBIUS_SUBNET_ID "${NEBIUS_SUBNET_ID:-}"
    write_env_line NEBIUS_PARENT_ID "${NEBIUS_PARENT_ID:-}"
    write_env_line NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE "${NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE:-}"
    write_env_line NEBIUS_JOB_STATUS_COMMAND_TEMPLATE "${NEBIUS_JOB_STATUS_COMMAND_TEMPLATE:-}"
    write_env_line NEBIUS_JOB_LOGS_COMMAND_TEMPLATE "${NEBIUS_JOB_LOGS_COMMAND_TEMPLATE:-}"
    write_env_line NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE "${NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE:-}"
    write_env_line AGENT_RUNNER_ID "${AGENT_RUNNER_ID:-vm-runner-1}"
    write_env_line AGENT_RUNNER_AGENT_COUNT "${AGENT_RUNNER_AGENT_COUNT:-250}"
    write_env_line AGENT_RUNNER_MAX_AGENT_COUNT "${AGENT_RUNNER_MAX_AGENT_COUNT:-1000}"
    write_env_line AGENT_RUNNER_HEAVY_AGENT_COUNT "${AGENT_RUNNER_HEAVY_AGENT_COUNT:-0}"
    write_env_line AGENT_RUNNER_MAX_HEAVY_AGENT_COUNT "${AGENT_RUNNER_MAX_HEAVY_AGENT_COUNT:-8}"
    write_env_line AGENT_RUNNER_HEAVY_AGENT_WORKERS "${AGENT_RUNNER_HEAVY_AGENT_WORKERS:-2}"
    write_env_line AGENT_RUNNER_MAX_HEAVY_AGENT_WORKERS "${AGENT_RUNNER_MAX_HEAVY_AGENT_WORKERS:-8}"
    write_env_line AGENT_RUNNER_LANGGRAPH_AGENT_COUNT "${AGENT_RUNNER_LANGGRAPH_AGENT_COUNT:-0}"
    write_env_line AGENT_RUNNER_MAX_LANGGRAPH_AGENT_COUNT "${AGENT_RUNNER_MAX_LANGGRAPH_AGENT_COUNT:-32}"
    write_env_line AGENT_RUNNER_LANGGRAPH_STRATEGY "${AGENT_RUNNER_LANGGRAPH_STRATEGY:-liquidity_rebalancer}"
    write_env_line AGENT_RUNNER_AGENT_ID_PREFIX "${AGENT_RUNNER_AGENT_ID_PREFIX:-REMOTE}"
    write_env_line AGENT_RUNNER_DECISION_TIMEOUT_SECONDS "${AGENT_RUNNER_DECISION_TIMEOUT_SECONDS:-0.05}"
  } > "${bundle_dir}/.env"
}

bootstrap_remote_vm() {
  local target="$1"
  if [[ "${NEBIUS_VM_BOOTSTRAP_DOCKER}" != "true" ]]; then
    ssh "${SSH_ARGS[@]}" "${target}" "mkdir -p '${NEBIUS_VM_APP_DIR}/outputs' '${NEBIUS_VM_APP_DIR}/nebius'"
    return
  fi
  ssh "${SSH_ARGS[@]}" "${target}" "set -e; SUDO=''; if [ \"\$(id -u)\" -ne 0 ]; then SUDO=sudo; fi; if ! command -v docker >/dev/null 2>&1; then curl -fsSL https://get.docker.com -o /tmp/get-docker.sh; \$SUDO sh /tmp/get-docker.sh; fi; mkdir -p '${NEBIUS_VM_APP_DIR}/outputs' '${NEBIUS_VM_APP_DIR}/nebius'"
}

remote_compose() {
  local target="$1"
  shift
  local compose_args="$*"
  ssh "${SSH_ARGS[@]}" "${target}" "cd '${NEBIUS_VM_APP_DIR}' && DOCKER=docker; if ! docker info >/dev/null 2>&1; then DOCKER='sudo docker'; fi; \$DOCKER compose ${compose_args}"
}

deploy_vm() {
  if [[ -z "${NEBIUS_VM_HOST:-}" && "${DRY_RUN}" == "true" ]]; then
    NEBIUS_VM_HOST="<vm-public-ip>"
  else
    require_env NEBIUS_VM_HOST
  fi
  require_cmd ssh
  require_cmd scp
  local target bundle_dir
  target="$(vm_target)"
  bundle_dir="$(mktemp -d "${TMPDIR:-/tmp}/aimada-nebius-vm.XXXXXX")"
  prepare_bundle "${bundle_dir}"

  if [[ "${DRY_RUN}" == "true" ]]; then
    printf "%s\n" "Rendered VM compose bundle: ${bundle_dir}"
    printf "%s\n" "Would deploy to ${target}:${NEBIUS_VM_APP_DIR}"
    return
  fi

  mapfile -t SSH_ARGS < <(ssh_args)
  bootstrap_remote_vm "${target}"
  scp "${SSH_ARGS[@]}" "${bundle_dir}/docker-compose.yml" "${bundle_dir}/.env" "${target}:${NEBIUS_VM_APP_DIR}/"
  remote_compose "${target}" pull
  remote_compose "${target}" up -d --remove-orphans --scale "agent-runner=${NEBIUS_VM_AGENT_RUNNER_REPLICAS}"
}

smoke_vm() {
  if [[ -z "${NEBIUS_VM_HOST:-}" && "${DRY_RUN}" == "true" ]]; then
    NEBIUS_VM_HOST="<vm-public-ip>"
  else
    require_env NEBIUS_VM_HOST
  fi
  require_cmd curl
  local api_base
  api_base="${NEBIUS_VM_API_BASE_URL:-http://${NEBIUS_VM_HOST}:${NEBIUS_VM_BACKEND_PORT}}"
  run curl -fsS "${api_base%/}/health"
  printf "\n"
}

write_report() {
  if [[ "${DRY_RUN}" == "true" ]]; then
    return
  fi
  mkdir -p "$(dirname "${NEBIUS_VM_REPORT}")"
  {
    write_env_line NEBIUS_DEPLOYMENT_SCOPE vm-compose
    write_env_line NEBIUS_VM_HOST "${NEBIUS_VM_HOST:-}"
    write_env_line NEBIUS_VM_USER "${NEBIUS_VM_USER}"
    write_env_line NEBIUS_VM_APP_DIR "${NEBIUS_VM_APP_DIR}"
    write_env_line NEBIUS_BACKEND_IMAGE "${NEBIUS_BACKEND_IMAGE}"
    write_env_line NEBIUS_FRONTEND_IMAGE "${NEBIUS_FRONTEND_IMAGE}"
    write_env_line NEBIUS_AGENT_RUNNER_IMAGE "${NEBIUS_AGENT_RUNNER_IMAGE}"
    write_env_line NEBIUS_VM_AGENT_RUNNER_REPLICAS "${NEBIUS_VM_AGENT_RUNNER_REPLICAS}"
  } > "${NEBIUS_VM_REPORT}"
  printf "%s\n" "Wrote VM deployment report: ${NEBIUS_VM_REPORT}"
}

cd "${ROOT_DIR}"

contains_target images && build_images
contains_target provision && provision_vm
contains_target deploy && deploy_vm
contains_target smoke && smoke_vm
write_report

cat <<SUMMARY

Nebius VM deployment path complete.

Recommended path:
- small VM now: frontend + backend + agent-runner via Docker Compose
- GPU inference remains on Nebius Serverless Endpoint
- batch tournaments remain on Nebius Serverless Jobs
- later scale agent-runner with Kubernetes CPU node pools and per-runner service discovery
SUMMARY
