# AI Market Abuse Detection Arena

![AI Market Abuse Detection Arena GitHub banner](assets/img/ai-mada.jpg)

A research and performance engineering workspace for synthetic order-book market abuse detection, live visualization, benchmark runs, and AI-generated incident explanations.

**🚀 Quick Start**: Get running in 5 minutes — see [Quick Start](#quick-start) section below, or read [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed walkthrough.

## ⚠️ Disclaimer

This project is an educational simulation. It does not detect real market manipulation, does not provide trading signals, and should not be used for compliance decisions. The scenarios are synthetic "abuse-like" patterns designed to demonstrate order-book anomaly detection and AI-generated explanations. See [docs/safety-and-disclaimers.md](docs/safety-and-disclaimers.md) for details.

## Current Implementation Status

Implemented:

- Live React/FastAPI arena with WebSocket state, order-book visualization, scenario launch, detector scores, incidents, and report/replay workflows.
- In-process `AgentManager` for hundreds of lightweight normal agents with per-tick deadlines and single-writer exchange application.
- Separate `agent-runner` service for out-of-process agents over HTTP, while the backend keeps the exchange/order book authoritative.
- LangGraph-compatible generic remote agents and worker-pool heavy agents inside `agent-runner`.
- Google authentication completion with verified Google identity storage, app-issued JWT sessions, and a collapsible professional auth widget.
- Deterministic detector evidence model for synthetic spoofing-like, layering-like, quote-stuffing-like, and liquidity-shock patterns.
- Nebius endpoint and job scaffolds with local typed fallbacks, Docker/config files, scripts, and UI control surfaces.
- Phase 4.5 managed experiments with deterministic attack manifests, local smart-batch execution, artifact normalization, aggregation, bounded AI investigations, and Reports review of summaries, leaderboards, markdown reports, artifact indexes, and original local-batch files.
- Coherent day/night/system UI theme behavior across widgets, charts, status chips, order-book levels, and canvas visualizations, plus compact vertical-navigation controls, paused-state-stable liquidity visualization, and documentation set for quick start, architecture, ARDs, runtime model, benchmark methodology, safety framing, deployment, and design ideas.

Not yet complete:

- Archived real Nebius endpoint and Serverless AI Job run with logs, metrics screenshots, and produced artifacts. Phase 4.5 `submit-nebius` correctly records `real_nebius_pending` until real job execution is implemented and evidenced.
- Committed sample benchmark report under `outputs/benchmark/`.
- Final screenshot assets for the README screenshot table.
- Dedicated Judge Mode timeline-window selector and formal benchmark artifact schema versioning.

## Repository Structure

```
backend/          FastAPI simulator, detectors, reports, local storage
frontend/         Vite React UI for live arena and benchmark views
serverless/       Nebius endpoint, job images, configs, and batch runners
docs/             Complete architecture, deployment, and research notes
assets/           Research articles, screenshots, diagrams, banners
data/             Sample input data for local testing
outputs/          Generated logs, incidents, reports, artifacts
```

## Getting Started

### 1. Clone and Configure

```bash
git clone https://github.com/khab40/ai-market-abuse-detection-arena.git
cd ai-market-abuse-detection-arena
cp .env.example .env
```

### 2. Start the Full Local Stack

```bash
docker compose up --build
```

- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:8000
- **WebSocket**: ws://localhost:8000/ws/arena

### 3. Explore

For guided next steps, see [docs/QUICKSTART.md](docs/QUICKSTART.md).

## Development

```bash
make backend-dev              # Run backend with auto-reload
make frontend-dev             # Run frontend dev server
make backend-test             # Run pytest suite
make serverless-benchmark     # Build batch job scaffold
```

## Docker Compose

Run the backend and frontend together:

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- WebSocket: ws://localhost:8000/ws/arena

Run the FastAPI backend directly:

```bash
cd backend
uv sync
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Common API Endpoints

Backend health and control:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/status
curl http://localhost:8000/api/nebius/status
curl http://localhost:8000/api/arena/state
curl -X POST http://localhost:8000/api/simulation/start
curl -X POST http://localhost:8000/api/simulation/pause
curl -X POST http://localhost:8000/api/simulation/reset
```

Scenario injection:

```bash
curl -X POST http://localhost:8000/api/scenarios/spoofing-like
curl -X POST http://localhost:8000/api/scenarios/layering-like
curl -X POST http://localhost:8000/api/scenarios/quote-stuffing
curl -X POST http://localhost:8000/api/scenarios/liquidity-evaporation
```

Incident inspection:

```bash
curl http://localhost:8000/api/incidents
curl http://localhost:8000/api/incidents/INC-000001
curl -X POST http://localhost:8000/api/incidents/INC-000001/explain
```

Red-team and scenario generation:

```bash
curl -X POST http://localhost:8000/api/red-team/generate-scenario \
  -H 'Content-Type: application/json' \
  -d '{"scenario_family":"quote_stuffing","market_regime":"volatile","goal":"hard_to_detect","constraints":{"max_duration_seconds":5}}'

curl -X POST http://localhost:8000/api/nebius/red-team-scenario \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"short spoofing-like wall in a thin book","constraints":{"scenario_type":"spoofing_like_wall"}}'
```

Nebius control path:

```bash
curl -X POST http://localhost:8000/api/nebius/smart-scenario
curl -X POST http://localhost:8000/api/nebius/smart-detection \
  -H 'Content-Type: application/json' \
  -d '{"features":{"wall_size_ratio":8.2,"message_rate":21,"cancel_to_trade_ratio":5.4},"scenario_hint":"spoofing"}'
curl -X POST http://localhost:8000/api/nebius/smart-batches \
  -H 'Content-Type: application/json' \
  -d '{"runs":100,"batch_size":100,"scenarios":["normal_market","spoofing","layering","quote_stuffing","pump_and_cancel"]}'
curl http://localhost:8000/api/nebius/observatory
```

Managed experiment path:

```bash
curl -X POST http://localhost:8000/api/experiments \
  -H 'Content-Type: application/json' \
  -d '{"name":"Local detector benchmark","attack_count":10,"batch_size":5,"scenarios":["normal_market","spoofing","layering","quote_stuffing","pump_and_cancel"],"seed":42,"nebius_mode":"mock"}'

curl -X POST http://localhost:8000/api/experiments/EXP_ID/generate-manifest
curl -X POST http://localhost:8000/api/experiments/EXP_ID/run-local-batch
curl -X POST http://localhost:8000/api/experiments/EXP_ID/normalize-artifacts
curl -X POST http://localhost:8000/api/experiments/EXP_ID/aggregate
curl -X POST 'http://localhost:8000/api/experiments/EXP_ID/run-investigations?top_k=7'
curl http://localhost:8000/api/experiments/EXP_ID/summary
curl http://localhost:8000/api/experiments/EXP_ID/leaderboard
curl http://localhost:8000/api/experiments/EXP_ID/report
curl http://localhost:8000/api/experiments/EXP_ID/investigations
```

The local experiment path writes synthetic benchmark evidence under `outputs/experiments/<experiment_id>/`, including `attacks.jsonl`, original `local-batch/` files, normalized artifact links, `artifact_index.json`, `experiment_summary.json`, `leaderboard.json`, `benchmark_report.md`, and optional investigation reports. `/reports` previews these artifacts for review. This is simulator evidence for education and reproducibility, not real market surveillance or compliance output.

## Environment Configuration

Nebius endpoint wiring is configured only through environment variables. Leave the URLs unset for local mock fallback mode:

```bash
NEBIUS_TENANT_ID=your-tenant-id
NEBIUS_ENDPOINT_BASE_URL=https://your-nebius-endpoint
NEBIUS_API_KEY=optional-token
```

The backend derives `POST /explain-event`, `POST /generate-scenario`, `POST /orderbook-alert`, and `POST /investigation-report` from `NEBIUS_ENDPOINT_BASE_URL`. Set `NEBIUS_INCIDENT_EXPLAINER_URL` and `NEBIUS_SCENARIO_GENERATOR_URL` only if you need explicit per-route overrides.

Phase 4 reproducibility:

```bash
python scripts/generate_scenarios.py
python scripts/run_local_eval.py
python scripts/submit_nebius_job.py --dry-run
python scripts/call_endpoint.py --base-url http://localhost:9000 --route orderbook-alert
```

Nebius resource creation:

```bash
export NEBIUS_PARENT_ID=<project-id>
export NEBIUS_SUBNET_ID=<vpc-subnet-id>
export NEBIUS_ENDPOINT_IMAGE=ghcr.io/<your-org>/ai-market-abuse-detection-arena-endpoint:<tag>
export NEBIUS_JOB_IMAGE=ghcr.io/<your-org>/ai-market-abuse-detection-arena-jobs:<tag>

./scripts/create-nebius-ai-endpoint.sh
./scripts/create-nebius-ai-job.sh
```

Frontend WebSocket connection:

```bash
VITE_ARENA_MODE=websocket
VITE_ARENA_WS_URL=ws://localhost:8000/ws/arena
```

Agent scheduler:

```bash
ARENA_AGENT_COUNT=3
ARENA_AGENT_DECISION_TIMEOUT_SECONDS=0.05
ARENA_REMOTE_AGENT_URLS=http://agent-runner:9100
ARENA_REMOTE_AGENT_TIMEOUT_SECONDS=0.05
ARENA_BASELINE_LIQUIDITY_LEVELS=12
ARENA_BASELINE_LIQUIDITY_BASE_SIZE=1.5
ARENA_BASELINE_LIQUIDITY_TICK_SIZE=1.0
ARENA_BASELINE_LIQUIDITY_REFERENCE_PRICE=68125.0
ARENA_MAX_AGENT_QUOTE_SIZE=25.0
AGENT_RUNNER_AGENT_COUNT=200
AGENT_RUNNER_HEAVY_AGENT_COUNT=8
AGENT_RUNNER_HEAVY_AGENT_WORKERS=2
AGENT_RUNNER_LANGGRAPH_AGENT_COUNT=16
AGENT_RUNNER_LANGGRAPH_STRATEGY=liquidity_rebalancer
```

Use a comma-separated `ARENA_REMOTE_AGENT_URLS` value to point the backend at agent runners in other containers or on other machines. The backend receives only `AgentIntent` objects; LangGraph and heavy-agent execution stay inside the runner. The `ARENA_BASELINE_LIQUIDITY_*` settings maintain a minimum bid/ask ladder around the reference price so market orders and scenarios cannot leave one side permanently empty. Agent `set_level` intents are additive per agent at a price level and capped by `ARENA_MAX_AGENT_QUOTE_SIZE`; scenarios can still replace whole levels when they need scripted walls or cancellations.

Google authentication:

```bash
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5173
AIMADA_JWT_SECRET=replace-with-a-long-random-secret
AIMADA_JWT_ISSUER=ai-market-abuse-detection-arena
AIMADA_JWT_EXPIRES_IN_SECONDS=43200
```

When `GOOGLE_CLIENT_ID` is configured, `POST /api/auth/google/complete` requires a Google `id_token` or authorization code. The backend verifies the Google token, stores/updates the user in `outputs/auth/auth.db`, and returns its own app JWT. Google tokens are not used as long-lived app sessions.

## WebSocket

Browser smoke test:

```js
const ws = new WebSocket("ws://localhost:8000/ws/arena");
ws.onmessage = (event) => console.log(JSON.parse(event.data));
ws.onopen = () => ws.send(JSON.stringify({ type: "arena_control", action: "start" }));
```

## Documentation Index

Start with the guides above, then explore:

| Topic | File | Purpose |
|-------|------|---------|
| **Quick Start** | [docs/QUICKSTART.md](docs/QUICKSTART.md) | 5-minute setup walkthrough |
| **Architecture Overview** | [docs/architecture.md](docs/architecture.md) | System design with Mermaid diagrams |
| **Architecture Records** | [docs/architecture/README.md](docs/architecture/README.md) | 13 decision records (ARD-0001 to ARD-0013) |
| **Use Cases & Workflows** | [docs/USE_CASES.md](docs/USE_CASES.md) | Eight primary workflows |
| **Runtime Model** | [docs/runtime-model.md](docs/runtime-model.md) | How the simulation engine executes |
| **Benchmark Methodology** | [docs/benchmark-methodology.md](docs/benchmark-methodology.md) | Detector quality metrics |
| **Nebius Deployment** | [docs/nebius-deployment.md](docs/nebius-deployment.md) | Setup serverless components |
| **Challenge Submission** | [docs/challenge-submission.md](docs/challenge-submission.md) | How to submit results |
| **Research Notes** | [docs/research-notes.md](docs/research-notes.md) | Market microstructure background |
| **Design Ideas** | [docs/DESIGN-IDEAS.md](docs/DESIGN-IDEAS.md) | Design exploration notes |
| **Development Timeline** | [docs/PHASES.md](docs/PHASES.md) | Milestones and phases |
| **Documentation Guide** | [docs/DOCUMENTATION_GUIDE.md](docs/DOCUMENTATION_GUIDE.md) | For maintainers & contributors |

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Interactive Path** | Live React UI where operators control a synthetic exchange, inject scenarios, and review detector alerts in real time |
| **Batch Path** | Nebius serverless jobs that run many simulations and compute detector metrics (precision, recall, F1) |
| **Arena** | The live order-book visualization showing normal trading agents and abuse-like scenario behavior |
| **Detector** | Deterministic algorithm that analyzes order-book microstructure and produces confidence scores |
| **Incident** | A time window flagged by the detector with supporting evidence |
| **Scenario** | A bounded abuse-like pattern (spoofing-like, layering-like, quote-stuffing-like) |
| **Nebius Endpoint** | Serverless AI service called by the backend to generate explanations and scenario suggestions |
| **Nebius Control Panel** | UI tab for smart endpoint scoring, parallel attack/detect batches, usage evidence, and benchmark charts |
| **Experiment Lab** | `/nebius` workflow for managed Phase 4.5 experiments: create manifest, generate attacks, run local batch, aggregate, investigate, and optionally record pending Nebius submission |
| **Reports Experiment Review** | `/reports` workflow for selected experiment summary, leaderboard, markdown report, investigation files, artifact index, and original local-batch artifacts |
| **Benchmark** | Evaluation of detector quality against labeled synthetic scenarios |
| **UI Shell Preferences** | Local browser preferences for collapsed auth controls and day/night/system theme behavior |

## Screenshots

Status: `[partial]`

The GitHub banner uses `assets/img/ai-mada.jpg`. `assets/screenshots/` currently contains only `.gitkeep`; the following screenshot assets are still planned:

| View | Planned Path | Description |
| --- | --- | --- |
| Arena cockpit | `assets/screenshots/arena-cockpit.svg` | Live order-book, detector alerts, incident details |
| Incident replay drawer | `assets/screenshots/incident-replay-drawer.svg` | Timeline replay, evidence metrics, AI explanation |
| Experiment Lab / Nebius job | `assets/screenshots/experiment-lab.svg` | Batch job config, live metrics, results streaming |
| Nebius logs and metrics | `assets/screenshots/nebius-logs-metrics.svg` | Log stream, CPU/memory/latency charts, worker health |

## For Maintainers & Contributors

Want to update the documentation or contribute? Read [docs/DOCUMENTATION_GUIDE.md](docs/DOCUMENTATION_GUIDE.md) for:
- Documentation structure and principles
- How to update docs and avoid stale information
- Validation checklist
- Common issues and fixes
