#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  deployments/deploy.sh <mode> [--dry-run] [--skip-build] [--skip-smoke]

Modes:
  local-demo
  nebius-cloud-demo
  production-nebius

Examples:
  deployments/deploy.sh local-demo
  deployments/deploy.sh nebius-cloud-demo --dry-run
  deployments/deploy.sh production-nebius
USAGE
}

MODE="${1:-}"
if [[ -z "${MODE}" || "${MODE}" == "-h" || "${MODE}" == "--help" ]]; then
  usage
  exit 0
fi
shift || true

DRY_RUN=false
SKIP_BUILD=false
SKIP_SMOKE=false
for arg in "$@"; do
  case "${arg}" in
    --dry-run) DRY_RUN=true ;;
    --skip-build) SKIP_BUILD=true ;;
    --skip-smoke) SKIP_SMOKE=true ;;
    *)
      printf "%s\n" "Unknown argument: ${arg}" >&2
      usage
      exit 2
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE_FILE="${ROOT_DIR}/deployments/modes/${MODE}.env"
DEPLOY_REPORT_DIR="${ROOT_DIR}/outputs/deployments"
DEPLOY_REPORT="${DEPLOY_REPORT_DIR}/${MODE}-latest.env"

if [[ ! -f "${MODE_FILE}" ]]; then
  printf "%s\n" "Unknown deployment mode: ${MODE}" >&2
  usage
  exit 2
fi

set -a
# shellcheck disable=SC1090
. "${MODE_FILE}"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  . "${ROOT_DIR}/.env"
fi
set +a

run() {
  local label="$1"
  shift
  printf "+ %s:" "${label}"
  for item in "$@"; do
    printf " %q" "${item}"
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
  if [[ "${DRY_RUN}" == "true" ]]; then
    return
  fi
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

write_report() {
  if [[ "${DRY_RUN}" == "true" ]]; then
    printf "%s\n" "Dry-run deployment report would be: ${DEPLOY_REPORT}"
    return
  fi
  mkdir -p "${DEPLOY_REPORT_DIR}"
  {
    printf "AIMADA_DEPLOYMENT_MODE=%s\n" "${MODE}"
    printf "AIMADA_DEPLOYMENT_PROFILE=%s\n" "${AIMADA_DEPLOYMENT_PROFILE:-${MODE}}"
    printf "AIMADA_DEPLOYMENT_LIFECYCLE=%s\n" "${AIMADA_DEPLOYMENT_LIFECYCLE:-simulate,detect,explain,investigate,report,audit,benchmark}"
    printf "AIMADA_DEPLOYMENT_REAL_NEBIUS=%s\n" "${AIMADA_DEPLOYMENT_REAL_NEBIUS:-false}"
    printf "AIMADA_DEPLOYMENT_SIMULATED_FALLBACK=%s\n" "${AIMADA_DEPLOYMENT_SIMULATED_FALLBACK:-true}"
    printf "NEBIUS_ENDPOINT_BASE_URL=%s\n" "${NEBIUS_ENDPOINT_BASE_URL:-}"
    printf "NEBIUS_ENDPOINT_IMAGE=%s\n" "${NEBIUS_ENDPOINT_IMAGE:-}"
    printf "NEBIUS_JOB_IMAGE=%s\n" "${NEBIUS_JOB_IMAGE:-}"
    printf "AIMADA_OBJECT_STORAGE_URI=%s\n" "${AIMADA_OBJECT_STORAGE_URI:-}"
    printf "AIMADA_POSTGRES_DSN_CONFIGURED=%s\n" "$(configured AIMADA_POSTGRES_DSN)"
    printf "AIMADA_MLFLOW_TRACKING_URI=%s\n" "${AIMADA_MLFLOW_TRACKING_URI:-}"
    printf "AIMADA_OBSERVABILITY_ENDPOINT=%s\n" "${AIMADA_OBSERVABILITY_ENDPOINT:-}"
    printf "AIMADA_IAM_PROFILE=%s\n" "${AIMADA_IAM_PROFILE:-}"
    printf "AIMADA_SECRETS_BACKEND=%s\n" "${AIMADA_SECRETS_BACKEND:-}"
  } > "${DEPLOY_REPORT}"
  printf "%s\n" "Deployment report: ${DEPLOY_REPORT}"
}

configured() {
  if [[ -n "${!1:-}" ]]; then
    printf "true"
  else
    printf "false"
  fi
}

build_serverless_images() {
  if [[ "${SKIP_BUILD}" == "true" ]]; then
    return
  fi
  if [[ "${AIMADA_BUILD_SERVERLESS_IMAGES:-false}" == "true" ]]; then
    require_cmd docker
    run "build serverless images" env \
      IMAGE_NAMESPACE="${IMAGE_NAMESPACE:-ghcr.io/khab40}" \
      TAG="${TAG:-latest}" \
      PUSH="${AIMADA_PUSH_SERVERLESS_IMAGES:-false}" \
      PLATFORM="${PLATFORM:-linux/amd64}" \
      ENDPOINT_IMAGE="${NEBIUS_ENDPOINT_IMAGE:-}" \
      JOBS_IMAGE="${NEBIUS_JOB_IMAGE:-}" \
      "${ROOT_DIR}/scripts/build-serverless-images.sh"
  fi
}

smoke_local_stack() {
  if [[ "${SKIP_SMOKE}" == "true" ]]; then
    return
  fi
  run "backend health" curl -fsS "http://localhost:${AIMADA_BACKEND_PORT:-8000}/health"
  run "nebius status" curl -fsS "http://localhost:${AIMADA_BACKEND_PORT:-8000}/api/nebius/status"
}

deploy_local_demo() {
  require_cmd docker
  export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-aimada-local-demo}"
  export NEBIUS_ENDPOINT_MODE=mock
  export NEBIUS_ENDPOINT_BASE_URL=http://endpoint:9000
  export VITE_ARENA_MODE="${VITE_ARENA_MODE:-websocket}"
  run "local demo stack" docker compose -f "${ROOT_DIR}/docker-compose.yml" up --build -d
  smoke_local_stack
}

deploy_nebius_cloud_demo() {
  require_cmd docker
  require_cmd nebius
  require_env NEBIUS_SUBNET_ID NEBIUS_ENDPOINT_TOKEN
  export NEBIUS_ENDPOINT_MODE=nebius
  build_serverless_images
  run "create Nebius endpoint" "${ROOT_DIR}/scripts/create-nebius-ai-endpoint.sh"
  run "create Nebius batch job" "${ROOT_DIR}/scripts/create-nebius-ai-job.sh"
  export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-aimada-nebius-cloud-demo}"
  export NEBIUS_ENDPOINT_MODE="${NEBIUS_ENDPOINT_MODE:-nebius}"
  run "cloud demo app stack" docker compose -f "${ROOT_DIR}/docker-compose.yml" up --build -d backend frontend
  smoke_local_stack
}

deploy_production_nebius() {
  require_cmd nebius
  require_env \
    NEBIUS_SUBNET_ID \
    NEBIUS_ENDPOINT_TOKEN \
    AIMADA_OBJECT_STORAGE_URI \
    AIMADA_POSTGRES_DSN \
    AIMADA_MLFLOW_TRACKING_URI \
    AIMADA_OBSERVABILITY_ENDPOINT \
    AIMADA_IAM_PROFILE \
    AIMADA_SECRETS_BACKEND
  export NEBIUS_ENDPOINT_MODE=nebius
  build_serverless_images
  run "create production Nebius endpoint" "${ROOT_DIR}/scripts/create-nebius-ai-endpoint.sh"
  run "create production Nebius job" "${ROOT_DIR}/scripts/create-nebius-ai-job.sh"
  if [[ -n "${AIMADA_APP_DEPLOY_COMMAND:-}" ]]; then
    run "production app deploy hook" bash -lc "${AIMADA_APP_DEPLOY_COMMAND}"
  elif [[ "${DRY_RUN}" == "true" ]]; then
    printf "%s\n" "AIMADA_APP_DEPLOY_COMMAND not set; production app deploy hook would be skipped."
  else
    printf "%s\n" "AIMADA_APP_DEPLOY_COMMAND not set; serverless resources deployed, app deploy hook skipped."
  fi
}

cd "${ROOT_DIR}"
case "${MODE}" in
  local-demo) deploy_local_demo ;;
  nebius-cloud-demo) deploy_nebius_cloud_demo ;;
  production-nebius) deploy_production_nebius ;;
  *)
    printf "%s\n" "Unsupported mode: ${MODE}" >&2
    exit 2
    ;;
esac

write_report
