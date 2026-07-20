# Nebius Serverless Deployment

This folder contains the first-deployment serverless components needed to wire
the React frontend and FastAPI backend to Nebius-hosted AI surfaces.

## Components

- `endpoint/` - FastAPI Serverless AI Endpoint for incident explanation and scenario generation.
- `jobs/` - batch jobs for detector tournament benchmarks and synthetic dataset generation.
- `deployment.env.example` - backend and endpoint environment variables.

## Endpoint Wiring

The backend calls the endpoint through:

```text
NEBIUS_INCIDENT_EXPLAINER_URL=http://<endpoint>/explain-event
NEBIUS_SCENARIO_GENERATOR_URL=http://<endpoint>/generate-scenario
ENDPOINT_TOKEN=<optional endpoint token>
```

The frontend keeps calling the backend:

```text
POST /api/incidents/{incident_id}/explain
POST /api/red-team/generate-scenario
```

The browser never receives Nebius tokens.

The repository's single Compose file keeps this wiring disabled by default. To
run the app against deployed Serverless Endpoint and Job resources, configure
the endpoint/job variables and start it with:

```bash
NEBIUS_SERVERLESS_ENABLED=true \
NEBIUS_CLI_CONFIG_DIR="$HOME/.nebius" \
docker compose up --build
```

Use `--profile prometheus` or `--profile grafana` to add metrics or the complete
dashboard stack to the same serverless run.

## Local Smoke Test

Endpoint:

```bash
cd serverless/endpoint
uvicorn app:app --host 0.0.0.0 --port 9000
```

Backend env:

```bash
NEBIUS_INCIDENT_EXPLAINER_URL=http://localhost:9000/explain-event
NEBIUS_SCENARIO_GENERATOR_URL=http://localhost:9000/generate-scenario
```

## Container Build

Build from repository root with the default GitHub Container Registry namespace
`ghcr.io/khab40` and tag `latest`:

```bash
./scripts/build-serverless-images.sh
```

Equivalent Make target:

```bash
make serverless-build
```

Run endpoint health and jobs 3-run smoke checks against locally loaded images:

```bash
SMOKE=true ./scripts/build-serverless-images.sh
make serverless-smoke
```

Push images after local build/smoke succeeds:

```bash
PUSH=true ./scripts/build-serverless-images.sh
make serverless-push
```

The script options are environment variables:

```bash
IMAGE_NAMESPACE=ghcr.io/khab40
TAG=latest
ENDPOINT_IMAGE=ghcr.io/khab40/lob-arena-endpoint:latest
JOBS_IMAGE=ghcr.io/khab40/lob-arena-jobs:latest
PUSH=false
PLATFORM=linux/amd64
SMOKE=false
```

For example:

```bash
IMAGE_NAMESPACE=ghcr.io/<your-org> TAG=<tag> ./scripts/build-serverless-images.sh
PUSH=true IMAGE_NAMESPACE=ghcr.io/<your-org> TAG=<tag> ./scripts/build-serverless-images.sh
SMOKE=true IMAGE_NAMESPACE=ghcr.io/<your-org> TAG=<tag> ./scripts/build-serverless-images.sh
```

By default, the script builds these local tags:

```text
ghcr.io/khab40/lob-arena-endpoint:latest
ghcr.io/khab40/lob-arena-jobs:latest
```

Anonymous registry verification on 2026-07-13 confirmed the jobs `latest` and
`artifacts-v2` tags and the Endpoint `vllm-qwen-v11` tag. Each published image
includes `linux/amd64`; the Endpoint `latest` tag is not published. Local builds
may still use `latest`, but production Endpoint deployment examples use the
versioned public tag. VM and Kubernetes deployment scripts build and push their
application images to the explicitly configured namespace.

Smoke checks:

```text
Endpoint: docker run endpoint image, call GET /health.
Jobs: docker run jobs image with run_batch_experiments.py --runs 3 --batch-size 2.
```

## Deployment Smoke Workflow

After the endpoint, backend, and jobs image are available, run the end-to-end
deployment smoke workflow:

```bash
NEBIUS_ENDPOINT_BASE_URL=http://localhost:9000 \
BACKEND_BASE_URL=http://localhost:8000 \
JOBS_IMAGE=ghcr.io/khab40/lob-arena-jobs:latest \
./scripts/serverless-smoke.sh
```

For a deployed endpoint:

```bash
NEBIUS_ENDPOINT_BASE_URL=https://<endpoint-host> \
BACKEND_BASE_URL=https://<backend-host> \
ENDPOINT_TOKEN=<optional-endpoint-token> \
JOBS_IMAGE=ghcr.io/<your-org>/lob-arena-jobs:<tag> \
./scripts/serverless-smoke.sh
```

The script writes `outputs/serverless-smoke/summary.json` and stores raw
responses in the same directory. It checks endpoint `/health`,
`/orderbook-alert`, `/investigation-report`, runs the jobs image locally with
three runs, creates a backend experiment with 10 attacks, runs the local batch,
and optionally submits/collects Nebius job artifacts when command templates are
configured. Real Nebius job submission is not required for the smoke to pass;
when not configured, it is marked pending in the summary.

Equivalent manual commands:

```bash
docker build --platform linux/amd64 -f serverless/endpoint/Dockerfile \
  -t ghcr.io/khab40/lob-arena-endpoint:latest \
  serverless/endpoint

docker build -f serverless/jobs/Dockerfile \
  -t ghcr.io/khab40/lob-arena-jobs:latest \
  .
```

## First Deployment Checklist

1. Build and push `nebius-market-abuse-endpoint`.
2. Deploy it as a Nebius Serverless AI Endpoint with `scripts/create-nebius-ai-endpoint.sh`.
3. Copy the public endpoint URL into backend env:
   - `NEBIUS_INCIDENT_EXPLAINER_URL`
   - `NEBIUS_SCENARIO_GENERATOR_URL`
4. Start the backend and frontend.
5. In Arena, create an incident and click Nebius AI Investigator.

Local-vLLM L40S endpoint:

```bash
export NEBIUS_PARENT_ID=<project-id>
export NEBIUS_SUBNET_ID=<vpc-subnet-id>
export ENDPOINT_TOKEN=<endpoint-bearer-token>
export NEBIUS_ENDPOINT_IMAGE=ghcr.io/<your-org>/lob-arena-endpoint:<tag>
export NEBIUS_ENDPOINT_MODE=local_vllm
export NEBIUS_ENDPOINT_PLATFORM=gpu-l40s-d
export NEBIUS_ENDPOINT_PRESET=1gpu-16vcpu-96gb
export LOCAL_VLLM_BASE_URL=http://127.0.0.1:8001/v1
export LOCAL_VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct
export LOCAL_VLLM_HOST=127.0.0.1
export LOCAL_VLLM_PORT=8001
export LOCAL_VLLM_DTYPE=auto
export LOCAL_VLLM_GPU_MEMORY_UTILIZATION=0.90
export LOCAL_VLLM_MAX_MODEL_LEN=16384
export LOCAL_VLLM_ENABLE_PREFIX_CACHING=true
export LOCAL_VLLM_MAX_NUM_SEQS=16
export LOCAL_VLLM_TRUST_REMOTE_CODE=true

./scripts/create-nebius-ai-endpoint.sh
```
6. In Lab/Judge flow, call `POST /api/red-team/generate-scenario`.
7. Build and push `nebius-market-abuse-jobs`.
8. Run the detector tournament job with `jobs/job_config.example.yaml`.
9. Run the synthetic dataset job with `jobs/dataset_job_config.example.yaml`.

## Cost Controls

- Keep endpoint mode as `mock` for initial connectivity tests.
- Use `--runs 100` and `--samples 100` until the full path works.
- Switch `NEBIUS_ENDPOINT_MODE=local_vllm` only after backend-to-endpoint wiring is verified.

## Safety

All endpoint and job outputs are synthetic educational artifacts. They are not
real market abuse detections, trading signals, or compliance decisions.
