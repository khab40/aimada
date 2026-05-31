# Nebius Deployment

This project has two Nebius-oriented deployment surfaces:

- a serverless AI endpoint for explanations and report generation
- a serverless batch job for detector benchmarking

## Explanation Endpoint

The endpoint under `serverless/endpoint` exposes:

- `POST /explain-event`
- `POST /explain-simulation`
- `POST /generate-incident-report`

Configuration starts from `serverless/endpoint/endpoint_config.example.yaml`.

## Batch Benchmark Job

The batch job under `serverless/jobs` runs repeated synthetic simulations, injects labeled abuse-like patterns, computes detector metrics, and emits a benchmark report.

Configuration starts from `serverless/jobs/job_config.example.yaml`.

## Local Configuration

Copy `.env.example` to `.env` and set:

- `NEBIUS_API_KEY`
- `NEBIUS_EXPLAIN_ENDPOINT_URL`
- `ARENA_OUTPUT_DIR`

Keep secrets out of source control.
