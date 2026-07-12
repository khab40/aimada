#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/deploy-nebius-k8s.sh [options]

Default targets:
  images,manifests,rollout,smoke

Options:
  --targets LIST     Comma-separated targets: images,manifests,rollout,smoke
  --dry-run          Print generated manifests and commands without applying.
  --skip-build       Skip image build/push.
  -h, --help         Show this help.

Key env:
  KUBE_CONTEXT=<optional kubectl context>
  K8S_NAMESPACE=aimada
  IMAGE_NAMESPACE=ghcr.io/khab40
  TAG=k8s
  NEBIUS_ENDPOINT_BASE_URL=<deployed local_vllm endpoint URL>
  ENDPOINT_TOKEN=<endpoint bearer token>
  K8S_PUBLIC_ORIGIN=https://aimada.example.com
  K8S_API_BASE_URL=https://aimada.example.com
  K8S_WS_URL=wss://aimada.example.com/ws/arena
  K8S_AGENT_RUNNER_REPLICAS=2

This deploys frontend, backend, and agent-runner only. GPU inference remains on
Nebius Serverless Endpoint; batch tournaments remain on Nebius Serverless Jobs.
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGETS="${K8S_TARGETS:-images,manifests,rollout,smoke}"
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
TAG="${TAG:-k8s}"
PLATFORM="${PLATFORM:-linux/amd64}"
K8S_NAMESPACE="${K8S_NAMESPACE:-aimada}"
K8S_PUBLIC_ORIGIN="${K8S_PUBLIC_ORIGIN:-http://localhost:5173}"
K8S_API_BASE_URL="${K8S_API_BASE_URL:-http://localhost:8000}"
K8S_WS_URL="${K8S_WS_URL:-ws://localhost:8000/ws/arena}"
K8S_AGENT_RUNNER_REPLICAS="${K8S_AGENT_RUNNER_REPLICAS:-2}"
K8S_BACKEND_REPLICAS="${K8S_BACKEND_REPLICAS:-1}"
K8S_FRONTEND_REPLICAS="${K8S_FRONTEND_REPLICAS:-1}"
K8S_INGRESS_HOST="${K8S_INGRESS_HOST:-aimada.example.com}"
K8S_ENABLE_INGRESS="${K8S_ENABLE_INGRESS:-false}"
NEBIUS_BACKEND_IMAGE="${NEBIUS_BACKEND_IMAGE:-${IMAGE_NAMESPACE}/ai-market-abuse-detection-arena-backend:${TAG}}"
NEBIUS_FRONTEND_IMAGE="${NEBIUS_FRONTEND_IMAGE:-${IMAGE_NAMESPACE}/ai-market-abuse-detection-arena-frontend:${TAG}}"
NEBIUS_AGENT_RUNNER_IMAGE="${NEBIUS_AGENT_RUNNER_IMAGE:-${IMAGE_NAMESPACE}/ai-market-abuse-detection-arena-agent-runner:${TAG}}"
K8S_RENDER_DIR="${K8S_RENDER_DIR:-${ROOT_DIR}/outputs/deployments/k8s-rendered}"

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

kubectl_cmd() {
  local args=(kubectl)
  if [[ -n "${KUBE_CONTEXT:-}" ]]; then
    args+=(--context "${KUBE_CONTEXT}")
  fi
  printf "%s\n" "${args[@]}"
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

build_image() {
  local dockerfile="$1"
  local tag="$2"
  local context="$3"
  run docker buildx build --platform "${PLATFORM}" -f "${dockerfile}" -t "${tag}" --push "${context}"
}

build_images() {
  if [[ "${SKIP_BUILD}" == "true" ]]; then
    printf "%s\n" "Skipping Kubernetes image build/push."
    return
  fi
  require_cmd docker
  build_image "${ROOT_DIR}/backend/Dockerfile" "${NEBIUS_BACKEND_IMAGE}" "${ROOT_DIR}"
  build_image "${ROOT_DIR}/frontend/Dockerfile" "${NEBIUS_FRONTEND_IMAGE}" "${ROOT_DIR}/frontend"
  build_image "${ROOT_DIR}/agent-runner/Dockerfile" "${NEBIUS_AGENT_RUNNER_IMAGE}" "${ROOT_DIR}"
}

render_manifests() {
  rm -rf "${K8S_RENDER_DIR}"
  mkdir -p "${K8S_RENDER_DIR}"
  cp "${ROOT_DIR}/deployments/k8s/"*.yaml "${K8S_RENDER_DIR}/"

  set_image_and_replicas
  write_runtime_config
  write_secret
  if [[ "${K8S_ENABLE_INGRESS}" != "true" ]]; then
    rm -f "${K8S_RENDER_DIR}/ingress.yaml"
    sed -i.bak '/ingress.yaml/d' "${K8S_RENDER_DIR}/kustomization.yaml"
    rm -f "${K8S_RENDER_DIR}/kustomization.yaml.bak"
  else
    replace_text "${K8S_RENDER_DIR}/ingress.yaml" "aimada.example.com" "${K8S_INGRESS_HOST}"
  fi
  printf "%s\n" "Rendered Kubernetes manifests: ${K8S_RENDER_DIR}"
}

runner_urls() {
  if [[ -n "${K8S_REMOTE_AGENT_URLS:-}" ]]; then
    printf "%s" "${K8S_REMOTE_AGENT_URLS}"
    return
  fi
  local urls=()
  local index=0
  while [[ "${index}" -lt "${K8S_AGENT_RUNNER_REPLICAS}" ]]; do
    urls+=("http://agent-runner-${index}.agent-runner.${K8S_NAMESPACE}.svc.cluster.local:9100")
    index=$((index + 1))
  done
  local joined="${urls[*]}"
  printf "%s" "${joined// /,}"
}

replace_text() {
  local file="$1"
  local from="$2"
  local to="$3"
  python3 - "$file" "$from" "$to" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
path.write_text(path.read_text().replace(sys.argv[2], sys.argv[3]))
PY
}

set_image_and_replicas() {
  replace_text "${K8S_RENDER_DIR}/backend.yaml" "ghcr.io/your-org/ai-market-abuse-detection-arena-backend:k8s" "${NEBIUS_BACKEND_IMAGE}"
  replace_text "${K8S_RENDER_DIR}/frontend.yaml" "ghcr.io/your-org/ai-market-abuse-detection-arena-frontend:k8s" "${NEBIUS_FRONTEND_IMAGE}"
  replace_text "${K8S_RENDER_DIR}/agent-runner.yaml" "ghcr.io/your-org/ai-market-abuse-detection-arena-agent-runner:k8s" "${NEBIUS_AGENT_RUNNER_IMAGE}"
  replace_text "${K8S_RENDER_DIR}/backend.yaml" "replicas: 1" "replicas: ${K8S_BACKEND_REPLICAS}"
  replace_text "${K8S_RENDER_DIR}/frontend.yaml" "replicas: 1" "replicas: ${K8S_FRONTEND_REPLICAS}"
  replace_text "${K8S_RENDER_DIR}/agent-runner.yaml" "replicas: 2" "replicas: ${K8S_AGENT_RUNNER_REPLICAS}"
}

write_runtime_config() {
  local remote_agent_urls
  remote_agent_urls="$(runner_urls)"
  cat > "${K8S_RENDER_DIR}/configmap.yaml" <<CONFIG
apiVersion: v1
kind: ConfigMap
metadata:
  name: aimada-config
  namespace: ${K8S_NAMESPACE}
data:
  LOG_LEVEL: "${LOG_LEVEL:-INFO}"
  ARENA_OUTPUT_DIR: "/app/outputs"
  ARENA_AGENT_COUNT: "${ARENA_AGENT_COUNT:-3}"
  ARENA_DATA_RETENTION_DAYS: "${ARENA_DATA_RETENTION_DAYS:-1}"
  ARENA_AGENT_DECISION_TIMEOUT_SECONDS: "${ARENA_AGENT_DECISION_TIMEOUT_SECONDS:-0.05}"
  ARENA_REMOTE_AGENT_URLS: "${remote_agent_urls}"
  ARENA_REMOTE_AGENT_TIMEOUT_SECONDS: "${ARENA_REMOTE_AGENT_TIMEOUT_SECONDS:-0.05}"
  ARENA_TICK_HISTORY_INTERVAL: "${ARENA_TICK_HISTORY_INTERVAL:-10}"
  ARENA_PERSIST_ALL_EVENTS: "${ARENA_PERSIST_ALL_EVENTS:-false}"
  CORS_ALLOWED_ORIGINS: "${CORS_ALLOWED_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173,${K8S_PUBLIC_ORIGIN}}"
  NEBIUS_ENDPOINT_MODE: "${NEBIUS_ENDPOINT_MODE:-local_vllm}"
  NEBIUS_ENDPOINT_BASE_URL: "${NEBIUS_ENDPOINT_BASE_URL:-}"
  NEBIUS_HEALTH_TIMEOUT_SECONDS: "${NEBIUS_HEALTH_TIMEOUT_SECONDS:-5}"
  NEBIUS_JOB_IMAGE: "${NEBIUS_JOB_IMAGE:-ghcr.io/khab40/ai-market-abuse-detection-arena-jobs:latest}"
  NEBIUS_JOB_OUTPUT_URI: "${NEBIUS_JOB_OUTPUT_URI:-}"
  NEBIUS_OBJECT_STORAGE_ENDPOINT_URL: "${NEBIUS_OBJECT_STORAGE_ENDPOINT_URL:-https://storage.eu-north1.nebius.cloud}"
  NEBIUS_OBJECT_STORAGE_REGION: "${NEBIUS_OBJECT_STORAGE_REGION:-eu-north1}"
  NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE: "${NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE:-}"
  NEBIUS_JOB_STATUS_COMMAND_TEMPLATE: "${NEBIUS_JOB_STATUS_COMMAND_TEMPLATE:-}"
  NEBIUS_JOB_LOGS_COMMAND_TEMPLATE: "${NEBIUS_JOB_LOGS_COMMAND_TEMPLATE:-}"
  NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE: "${NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE:-}"
  VITE_API_BASE_URL: "${VITE_API_BASE_URL:-${K8S_API_BASE_URL}}"
  VITE_ARENA_MODE: "websocket"
  VITE_ARENA_WS_URL: "${VITE_ARENA_WS_URL:-${K8S_WS_URL}}"
  VITE_ENABLE_GOOGLE_AUTH: "${VITE_ENABLE_GOOGLE_AUTH:-false}"
  VITE_ENABLE_ADVANCED_ATTACK_CONTROLS: "${VITE_ENABLE_ADVANCED_ATTACK_CONTROLS:-false}"
  VITE_ENABLE_LEGACY_PAGES: "${VITE_ENABLE_LEGACY_PAGES:-false}"
  AGENT_RUNNER_ID: "${AGENT_RUNNER_ID:-k8s-runner}"
  AGENT_RUNNER_AGENT_COUNT: "${AGENT_RUNNER_AGENT_COUNT:-250}"
  AGENT_RUNNER_MAX_AGENT_COUNT: "${AGENT_RUNNER_MAX_AGENT_COUNT:-1000}"
  AGENT_RUNNER_HEAVY_AGENT_COUNT: "${AGENT_RUNNER_HEAVY_AGENT_COUNT:-0}"
  AGENT_RUNNER_MAX_HEAVY_AGENT_COUNT: "${AGENT_RUNNER_MAX_HEAVY_AGENT_COUNT:-8}"
  AGENT_RUNNER_HEAVY_AGENT_COMPLEXITY: "${AGENT_RUNNER_HEAVY_AGENT_COMPLEXITY:-20000}"
  AGENT_RUNNER_HEAVY_AGENT_WORKERS: "${AGENT_RUNNER_HEAVY_AGENT_WORKERS:-2}"
  AGENT_RUNNER_MAX_HEAVY_AGENT_WORKERS: "${AGENT_RUNNER_MAX_HEAVY_AGENT_WORKERS:-8}"
  AGENT_RUNNER_LANGGRAPH_AGENT_COUNT: "${AGENT_RUNNER_LANGGRAPH_AGENT_COUNT:-0}"
  AGENT_RUNNER_MAX_LANGGRAPH_AGENT_COUNT: "${AGENT_RUNNER_MAX_LANGGRAPH_AGENT_COUNT:-32}"
  AGENT_RUNNER_LANGGRAPH_STRATEGY: "${AGENT_RUNNER_LANGGRAPH_STRATEGY:-liquidity_rebalancer}"
  AGENT_RUNNER_AGENT_ID_PREFIX: "${AGENT_RUNNER_AGENT_ID_PREFIX:-REMOTE}"
  AGENT_RUNNER_DECISION_TIMEOUT_SECONDS: "${AGENT_RUNNER_DECISION_TIMEOUT_SECONDS:-0.05}"
CONFIG
  replace_text "${K8S_RENDER_DIR}/namespace.yaml" "name: aimada" "name: ${K8S_NAMESPACE}"
  for file in "${K8S_RENDER_DIR}"/*.yaml; do
    replace_text "${file}" "namespace: aimada" "namespace: ${K8S_NAMESPACE}"
  done
}

write_secret() {
  cat > "${K8S_RENDER_DIR}/secret.yaml" <<SECRET
apiVersion: v1
kind: Secret
metadata:
  name: aimada-secrets
  namespace: ${K8S_NAMESPACE}
type: Opaque
stringData:
  ENDPOINT_TOKEN: "${ENDPOINT_TOKEN:-}"
  AIMADA_JWT_SECRET: "${AIMADA_JWT_SECRET:-replace-with-a-long-random-secret}"
  GOOGLE_CLIENT_ID: "${GOOGLE_CLIENT_ID:-}"
  GOOGLE_CLIENT_SECRET: "${GOOGLE_CLIENT_SECRET:-}"
  NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID: "${NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID:-}"
  NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY: "${NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY:-}"
  NEBIUS_OBJECT_STORAGE_SESSION_TOKEN: "${NEBIUS_OBJECT_STORAGE_SESSION_TOKEN:-}"
SECRET
  rm -f "${K8S_RENDER_DIR}/secret.example.yaml"
  replace_text "${K8S_RENDER_DIR}/kustomization.yaml" "secret.example.yaml" "secret.yaml"
}

apply_manifests() {
  render_manifests
  mapfile -t KUBECTL < <(kubectl_cmd)
  if [[ "${DRY_RUN}" == "true" ]]; then
    run "${KUBECTL[@]}" apply -k "${K8S_RENDER_DIR}" --dry-run=client
  else
    require_cmd kubectl
    run "${KUBECTL[@]}" apply -k "${K8S_RENDER_DIR}"
  fi
}

rollout() {
  mapfile -t KUBECTL < <(kubectl_cmd)
  run "${KUBECTL[@]}" -n "${K8S_NAMESPACE}" rollout status statefulset/agent-runner --timeout=180s
  run "${KUBECTL[@]}" -n "${K8S_NAMESPACE}" rollout status deployment/backend --timeout=180s
  run "${KUBECTL[@]}" -n "${K8S_NAMESPACE}" rollout status deployment/frontend --timeout=180s
}

smoke() {
  mapfile -t KUBECTL < <(kubectl_cmd)
  run "${KUBECTL[@]}" -n "${K8S_NAMESPACE}" get pods
  run "${KUBECTL[@]}" -n "${K8S_NAMESPACE}" get svc
}

cd "${ROOT_DIR}"

contains_target images && build_images
contains_target manifests && apply_manifests
contains_target rollout && rollout
contains_target smoke && smoke

cat <<SUMMARY

Kubernetes deployment path complete.

Use this after the VM path when agent-runner needs horizontal sharding.
Keep backend replicas at 1 until state/output storage is made durable.
SUMMARY
