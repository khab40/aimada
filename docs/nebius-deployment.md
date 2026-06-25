# Nebius Deployment

This project has two Nebius-oriented deployment surfaces:

- a serverless AI endpoint for explanations and report generation
- a serverless batch job for detector benchmarking

The Nebius design is intentionally split between offline jobs and interactive
endpoints. Jobs handle repeatable engineering work that can run outside the UI.
Endpoints handle low-latency explanation and narration requests from the FastAPI
backend.

## Nebius Serverless AI Jobs

```mermaid
graph TD
    Jobs["Nebius Serverless AI Jobs"]
    Batch["Batch simulations"]
    Scenario["Scenario generation"]
    Features["Feature extraction"]
    Evaluation["Evaluation runs"]
    Reports["Experiment reports"]

    Jobs --> Batch
    Jobs --> Scenario
    Jobs --> Features
    Jobs --> Evaluation
    Jobs --> Reports
```

Job responsibilities:

- run bounded batches of synthetic simulations
- generate small synthetic datasets for detector evaluation
- extract market microstructure features from event and snapshot artifacts
- run detector tournament benchmarks across scenario families
- produce experiment reports, charts, and reproducible benchmark artifacts

Jobs should use small run counts during development to control time and credit
usage. Large runs belong in final benchmark passes only.

## Nebius Serverless AI Endpoints

```mermaid
graph TD
    Endpoints["Nebius Serverless AI Endpoints"]
    Judge["Real-time AI judge"]
    Explain["Explanation generation"]
    Narrator["Scenario narrator"]

    Endpoints --> Judge
    Endpoints --> Explain
    Endpoints --> Narrator
```

Endpoint responsibilities:

- explain detected synthetic incidents from structured evidence
- summarize selected timeline windows in Judge Mode
- narrate scenario behavior for the demo UI
- generate bounded red-team scenario drafts for the simulator

The UI does not call Nebius directly. The FastAPI backend owns endpoint URLs,
optional API tokens, fallback behavior, and request shaping.

## Product Mode Mapping

| Product mode | Nebius surface | Purpose |
| --- | --- | --- |
| Live Arena Mode | Serverless AI Endpoint | Real-time judge, explanation generation, and scenario narration for selected incidents. |
| Experiment Mode | Serverless AI Job | Batch simulations, synthetic dataset generation, feature extraction, detector evaluation, and experiment reports. |
| Judge Mode | Serverless AI Endpoint | Explain a selected timeline segment and produce an investigation-style report. |

## Reproducibility Commands

Another practitioner should be able to run the Phase 4 path from the repository
root with these commands:

```bash
python scripts/generate_scenarios.py
python scripts/run_local_eval.py
python scripts/submit_nebius_job.py --dry-run
python scripts/call_endpoint.py --base-url http://localhost:9000 --route orderbook-alert
```

For a real Nebius submission, build and push images first:

```bash
PUSH=true GHCR_OWNER=<your-org> IMAGE_TAG=<tag> ./scripts/build-serverless-images.sh
```

Then create the endpoint and job:

```bash
export NEBIUS_SUBNET_ID=<vpc-subnet-id>
export NEBIUS_PARENT_ID=<project-id>
export NEBIUS_ENDPOINT_IMAGE=ghcr.io/<your-org>/ai-market-abuse-detection-arena-endpoint:<tag>
export NEBIUS_JOB_IMAGE=ghcr.io/<your-org>/ai-market-abuse-detection-arena-jobs:<tag>

./scripts/create-nebius-ai-endpoint.sh
./scripts/create-nebius-ai-job.sh
```

The shell scripts use the current deterministic CLI surfaces:

- `nebius ai endpoint create`
- `nebius ai job create`
- `nebius ai endpoint logs <endpoint-id> --follow`
- `nebius ai job logs <job-id> --follow`

## Endpoint Contract

The endpoint under `serverless/endpoint` exposes:

- `POST /orderbook-alert`
- `POST /investigation-report`
- `POST /explain-event`
- `POST /explain-simulation`
- `POST /generate-incident-report`
- `POST /generate-scenario`
- `POST /generate-smart-scenario`

Primary routes:

| Route | Input | Output |
| --- | --- | --- |
| `/orderbook-alert` | recent L2 order book window, events, feature snapshot | suspicion score, detected synthetic pattern, reasons |
| `/investigation-report` | scenario trace, alerts, detector metrics | human-readable synthetic market abuse case report |

Configuration starts from `serverless/endpoint/endpoint_config.yaml`.

## Batch Benchmark Job

The batch job under `serverless/jobs` runs repeated synthetic simulations, injects labeled abuse-like patterns, computes detector metrics, and emits a benchmark report.

The smart batch job under `serverless/jobs/` runs attack/detect mode in parallel
batches. It covers:

- normal market
- spoofing attack
- layering attack
- quote stuffing
- pump-and-cancel pattern

Outputs:

- `order_book_events.jsonl`
- `trades.jsonl`
- `attack_labels.jsonl`
- `blue_team_alerts.jsonl`
- `detector_metrics.csv`
- `generated_report.md`
- `manifest.json`

Configuration starts from `serverless/jobs/nebius_job_config.yaml`.

## Phase 4.5 Experiment Flow

The managed experiment flow is available locally through FastAPI and the React UI:

- `/nebius` Experiment Lab creates experiment manifests, generates attack manifests, runs local batches, aggregates outputs, and runs bounded mock/endpoint-backed investigations.
- `/reports` lists experiments and shows the selected experiment summary, detector leaderboard, `benchmark_report.md`, investigation report files, `artifact_index.json`, canonical artifacts, and original `local-batch` files.
- Local batch execution reuses `serverless/jobs/run_batch_experiments.py` and writes under `outputs/experiments/<experiment_id>/`.
- `POST /api/experiments/{id}/submit-nebius` currently records a `real_nebius_pending` job record when real Nebius credentials/job execution are not configured.

Real Nebius Serverless Job execution for Phase 4.5 is TODO until there is actual job submission code in `backend/app/experiments/nebius_orchestrator.py` plus archived Nebius job logs, metrics, and produced artifacts. Do not treat the local batch path or `real_nebius_pending` records as evidence of real cloud execution.

## Local Configuration

Copy `.env.example` to `.env` and set:

- `NEBIUS_TENANT_ID`
- `NEBIUS_INCIDENT_EXPLAINER_URL`
- `NEBIUS_SCENARIO_GENERATOR_URL`
- `NEBIUS_API_KEY`
- `ARENA_OUTPUT_DIR`

Keep secrets out of source control.

## Production Environment Mapping

Use the same key names, but place them in different deployment surfaces.

### Nebius Serverless AI Endpoint

Set these on the deployed endpoint container:

| Variable | Required | Purpose |
| --- | --- | --- |
| `NEBIUS_ENDPOINT_MODE` | yes | `mock` for deterministic fallback, `ai` to call Nebius AI Studio. |
| `NEBIUS_API_KEY` | only for `ai` mode | Token used by the endpoint to call Nebius AI Studio. Store as a secret. |
| `NEBIUS_AI_STUDIO_BASE_URL` | no | AI Studio API base URL. Defaults to `https://api.studio.nebius.com/v1`. |
| `NEBIUS_AI_MODEL` | no | Model used for explanation/scenario JSON. |
| `NEBIUS_TEMPERATURE` | no | Model temperature. Use `0.2` for stable outputs. |
| `NEBIUS_MAX_TOKENS` | no | Max completion size. Use a small value such as `800`. |
| `NEBIUS_REQUEST_TIMEOUT_SECONDS` | no | Endpoint model-call timeout. |

The endpoint exposes:

```text
GET  /health
POST /orderbook-alert
POST /investigation-report
POST /explain-event
POST /generate-scenario
POST /explain-simulation
POST /generate-report
```

### FastAPI Backend

Set these on the backend container or backend Docker Compose environment:

| Variable | Required | Purpose |
| --- | --- | --- |
| `NEBIUS_TENANT_ID` | recommended | Tenant metadata shown by `/api/nebius/status`. |
| `NEBIUS_ENDPOINT_BASE_URL` | yes for real endpoint | Base URL for the deployed endpoint. The backend derives `/explain-event` and `/generate-scenario`. |
| `NEBIUS_INCIDENT_EXPLAINER_URL` | no | Explicit full URL override for `/explain-event`. |
| `NEBIUS_SCENARIO_GENERATOR_URL` | no | Explicit full URL override for `/generate-scenario`. |
| `NEBIUS_API_KEY` | optional | Bearer token if the deployed endpoint requires auth. |
| `ARENA_OUTPUT_DIR` | no | Local/output artifact path. |
| `LOG_LEVEL` | no | Backend logging level. |

Example backend production values:

```bash
NEBIUS_TENANT_ID=tenant-e00ek8wmcr5jzwfa9k
NEBIUS_ENDPOINT_BASE_URL=http://<nebius-endpoint>
NEBIUS_API_KEY=<endpoint-auth-token-if-used>
```

### Frontend

Set these for the frontend build/runtime:

| Variable | Required | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | yes | Public URL of the FastAPI backend. |
| `VITE_ARENA_MODE` | yes | Use `websocket` in production. |
| `VITE_ARENA_WS_URL` | yes | Backend WebSocket URL `/ws/arena`. |

Example frontend production values:

```bash
VITE_API_BASE_URL=https://<backend-host>
VITE_ARENA_MODE=websocket
VITE_ARENA_WS_URL=wss://<backend-host>/ws/arena
```

### Nebius Serverless Jobs

Jobs do not need endpoint URLs for the first benchmark path. Configure job
arguments instead:

```bash
python detector_tournament.py --runs 100 --scenarios normal_market,spoofing,layering,quote_stuffing,pump_and_cancel --detectors spoofing_like,layering_like,quote_stuffing,liquidity_shock --output /job/outputs/benchmark
python synthetic_dataset_factory.py --samples 100 --output /job/outputs/synthetic-dataset
python /job/serverless/jobs/run_batch_experiments.py --runs 1000 --batch-size 100 --output /job/outputs/serverless-batch
```

Keep run counts small for first deployment checks.

## Serverless Cost/Runtime Observatory

The React `Nebius Control Panel` tab reads `/api/nebius/observatory` and displays
submission evidence:

```text
Endpoint:
- requests: 24
- avg latency: 1.2s
- purpose: incident explanation and order-book alert scoring

Jobs:
- simulations: 1,000
- runtime: 7m 42s
- output files: 7
- artifacts: benchmark_report.md, detector_metrics.csv, generated_report.md, manifest.json
```

Before final review, replace placeholder evidence with real Nebius endpoint/job
screenshots and archived logs/metrics.

The current Phase 4.5 Reports evidence is synthetic educational benchmark output from the simulator. It is useful for reproducibility and demo review, but it is not real market surveillance and is not compliance evidence.

## Architecture Records

Nebius implementation should follow the ARDs before adding runtime code:

- [ARD-0005: Nebius Endpoint Contract](architecture/ARD-0005-nebius-endpoint-contract.md)
- [ARD-0007: Nebius Serverless AI Jobs](architecture/ARD-0007-nebius-serverless-ai-jobs.md)
- [ARD-0008: Nebius Serverless AI Endpoints](architecture/ARD-0008-nebius-serverless-ai-endpoints.md)
- [ARD-0009: Judge Mode Investigation Reports](architecture/ARD-0009-judge-mode-investigation-reports.md)
