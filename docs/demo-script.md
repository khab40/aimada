# AIMADA Nebius AI Serverless Demo Script

## Goal

Show AIMADA as a Nebius AI Serverless-powered market surveillance command center in under five minutes. The demo works fully in local mock mode and keeps the same UI/API contracts for real Nebius execution.

## Setup

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:5173. The app should land on `AI Command Center`.

Local demo mode requires no Google login, no `NEBIUS_API_KEY`, and no deployed endpoint.

## Step 1: Generate AI Scenario

1. In `Nebius AI Scenario Generator`, choose:
   - manipulation type: `Spoofing`
   - difficulty: `Medium`
   - symbol: `AIMD`
   - duration: `120`
   - liquidity: `Thin`
   - volatility: `High`
2. Click `Generate Nebius AI Scenario`.
3. Show:
   - `Powered by Nebius AI Serverless Endpoint`
   - scenario id
   - ground truth label
   - expected detector signals
   - event timeline

Screenshot: `AI Scenario Generator` result.

## Step 2: Replay Scenario In Arena

1. Click `Replay in Arena`.
2. Open or switch to the Arena / Workload Generator if needed.
3. Show that the generated scenario is projected into the existing simulator replay path.
4. Point out that replay uses synthetic ground truth, not real market data.

Screenshot: Arena replay or active workload state.

## Step 3: Run Nebius AI Investigation Team

1. Return to `AI Command Center`.
2. In `Nebius AI Investigation Team`, click `Run Nebius AI Investigation Team`.
3. Show:
   - final verdict
   - risk score
   - confidence
   - agent findings
   - evidence timeline
   - recommended action

Screenshot: `Nebius AI Investigation Team` result.

## Step 4: Run Detector Tournament

1. In `Nebius AI Detector Tournament`, keep `Local Mock` for the reliable demo path.
2. Set:
   - scenarios: `100`
   - manipulation types: `spoofing`, `layering`, `quote stuffing`
   - detectors: `spoofing like`, `layering like`, `quote stuffing`
   - seed: `42`
3. Click `Run Nebius AI Detector Tournament`.
4. Show:
   - `Powered by Nebius Serverless Jobs`
   - execution mode
   - status
   - macro F1
   - false positives
   - false negatives

Screenshot: Detector Tournament status and metrics.

## Step 5: Show Leaderboard And Artifacts

1. Show the leaderboard rows.
2. Open artifact links if available:
   - `metrics.csv`
   - `results.json`
   - `benchmark_report.md`
   - F1 / confidence / latency charts
3. Explain that the same response shape is used when Nebius Serverless Jobs are configured.

Screenshot: Detector Tournament leaderboard and artifact links.

## Real Nebius Path

For a real Nebius run:

```bash
NEBIUS_ENDPOINT_MODE=ai
NEBIUS_API_KEY=<token>
NEBIUS_ENDPOINT_BASE_URL=<deployed-endpoint-base-url>
NEBIUS_MODEL=<model>
NEBIUS_JOB_IMAGE=<job-image>
NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE=<submit-command-template>
```

The interactive path calls the Nebius AI Serverless Endpoint. The batch path uses Nebius Serverless Jobs for detector tournament compute.

## Judge Talking Points

- Nebius AI Serverless Endpoint is used for interactive investigation and scenario generation.
- Nebius Serverless Jobs are used for scalable detector tournaments.
- Local mock mode exists for reliable judging and preserves the same API contracts.
- All outputs are synthetic and educational; AIMADA is not a real compliance system.
