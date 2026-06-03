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
NEBIUS_API_KEY=<optional endpoint token>
```

The frontend keeps calling the backend:

```text
POST /api/incidents/{incident_id}/explain
POST /api/red-team/generate-scenario
```

The browser never receives Nebius tokens.

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

Build from repository root with the GitHub Container Registry namespace
`khab40`:

```bash
./scripts/build-serverless-images.sh
```

Push after local build succeeds:

```bash
PUSH=true ./scripts/build-serverless-images.sh
```

The script builds:

```text
ghcr.io/khab40/nebius-market-abuse-arena-endpoint:latest
ghcr.io/khab40/nebius-market-abuse-arena-jobs:latest
```

Equivalent manual commands:

```bash
docker build -f serverless/endpoint/Dockerfile \
  -t ghcr.io/khab40/nebius-market-abuse-arena-endpoint:latest \
  serverless/endpoint

docker build -f serverless/jobs/Dockerfile \
  -t ghcr.io/khab40/nebius-market-abuse-arena-jobs:latest \
  .
```

## First Deployment Checklist

1. Build and push `nebius-market-abuse-endpoint`.
2. Deploy it as a Nebius Serverless AI Endpoint using `endpoint/endpoint_config.example.yaml`.
3. Copy the public endpoint URL into backend env:
   - `NEBIUS_INCIDENT_EXPLAINER_URL`
   - `NEBIUS_SCENARIO_GENERATOR_URL`
4. Start the backend and frontend.
5. In Arena, create an incident and click Nebius AI Investigator.
6. In Lab/Judge flow, call `POST /api/red-team/generate-scenario`.
7. Build and push `nebius-market-abuse-jobs`.
8. Run the detector tournament job with `jobs/job_config.example.yaml`.
9. Run the synthetic dataset job with `jobs/dataset_job_config.example.yaml`.

## Cost Controls

- Keep endpoint mode as `mock` for initial connectivity tests.
- Use `--runs 100` and `--samples 100` until the full path works.
- Switch `NEBIUS_ENDPOINT_MODE=ai` only after backend-to-endpoint wiring is verified.

## Safety

All endpoint and job outputs are synthetic educational artifacts. They are not
real market abuse detections, trading signals, or compliance decisions.
