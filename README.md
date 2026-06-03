# Nebius Market Abuse Arena

![Nebius Market Abuse Arena GitHub banner](assets/img/github-banner.png)

A research and performance engineering workspace for synthetic order-book market abuse detection, live visualization, benchmark runs, and AI-generated incident explanations.

**🚀 Quick Start**: Get running in 5 minutes — see [Quick Start](#quick-start) section below, or read [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed walkthrough.

## ⚠️ Disclaimer

This project is an educational simulation. It does not detect real market manipulation, does not provide trading signals, and should not be used for compliance decisions. The scenarios are synthetic "abuse-like" patterns designed to demonstrate order-book anomaly detection and AI-generated explanations. See [docs/safety-and-disclaimers.md](docs/safety-and-disclaimers.md) for details.

## Repository Structure

```
backend/          FastAPI simulator, detectors, reports, local storage
frontend/         Vite React UI for live arena and benchmark views
serverless/       Nebius serverless endpoint and batch job scaffolds
docs/             Complete architecture, deployment, and research notes
assets/           Research articles, screenshots, diagrams, banners
data/             Sample input data for local testing
outputs/          Generated logs, incidents, reports, artifacts
```

## Getting Started

### 1. Clone and Configure

```bash
git clone https://github.com/khab40/nebius-market-abuse-arena.git
cd nebius-market-abuse-arena
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

## Environment Configuration

Nebius endpoint wiring is configured only through environment variables. Leave the URLs unset for local mock fallback mode:

```bash
NEBIUS_TENANT_ID=your-tenant-id
NEBIUS_ENDPOINT_BASE_URL=https://your-nebius-endpoint
NEBIUS_API_KEY=optional-token
```

The backend derives `POST /explain-event` and `POST /generate-scenario` from `NEBIUS_ENDPOINT_BASE_URL`. Set `NEBIUS_INCIDENT_EXPLAINER_URL` and `NEBIUS_SCENARIO_GENERATOR_URL` only if you need explicit per-route overrides.

Frontend WebSocket connection:

```bash
VITE_ARENA_MODE=websocket
VITE_ARENA_WS_URL=ws://localhost:8000/ws/arena
```

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
| **Architecture Records** | [docs/architecture/README.md](docs/architecture/README.md) | 9 detailed decision records (ARD-0001 to 0009) |
| **Use Cases & Workflows** | [docs/USE_CASES.md](docs/USE_CASES.md) | Six primary workflows |
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
| **Benchmark** | Evaluation of detector quality against labeled synthetic scenarios |

## Screenshots

Interactive SVG mockups of the system UI:

| View | Path | Description |
| --- | --- | --- |
| Arena cockpit | [assets/screenshots/arena-cockpit.svg](assets/screenshots/arena-cockpit.svg) | Live order-book, detector alerts, incident details |
| Incident replay drawer | [assets/screenshots/incident-replay-drawer.svg](assets/screenshots/incident-replay-drawer.svg) | Timeline replay, evidence metrics, AI explanation |
| Experiment Lab / Nebius job | [assets/screenshots/experiment-lab.svg](assets/screenshots/experiment-lab.svg) | Batch job config, live metrics, results streaming |
| Nebius logs and metrics | [assets/screenshots/nebius-logs-metrics.svg](assets/screenshots/nebius-logs-metrics.svg) | Log stream, CPU/memory/latency charts, worker health |

## For Maintainers & Contributors

Want to update the documentation or contribute? Read [docs/DOCUMENTATION_GUIDE.md](docs/DOCUMENTATION_GUIDE.md) for:
- Documentation structure and principles
- How to update docs and avoid stale information
- Validation checklist
- Common issues and fixes
