# Changelog

This changelog lists significant commits in reverse chronological order.
Update this file with each significant commit before pushing.

## 2026-06-03

### `2811d05` - docs: add architecture, use cases, and deployment docs

- Expanded the root README with quick start, API examples, environment mapping, documentation index, and screenshot links.
- Added architecture and use-case documentation, including Mermaid diagrams and ARD index updates.
- Added ARD-0002 through ARD-0009 for WebSocket schema, detector evidence, benchmark artifacts, Nebius endpoint/jobs, scenario labeling, and judge mode.
- Moved project phases from root `PHASES.md` to `docs/PHASES.md`.
- Added documentation guide, quickstart guide, design ideas, use cases, and SVG screenshot placeholders.
- Updated `docker-compose.yml` and `Makefile` documentation/deployment helpers.

### `3ccbece` - feat: add Nebius serverless endpoint and jobs

- Added Nebius Serverless AI Endpoint implementation with deterministic mock mode and optional AI Studio JSON calls.
- Added endpoint routes for health, incident explanation, simulation explanation, report generation, and scenario generation.
- Added detector tournament and synthetic dataset factory serverless job scripts.
- Added serverless Dockerfiles, example job configs, endpoint config, deployment env example, and serverless README.
- Added `scripts/build-serverless-images.sh` for linux/amd64 GHCR image builds and optional pushes.
- Added endpoint contract tests and smoke-tested benchmark/dataset scripts.

### `bb79d04` - feat: build arena cockpit and lab UI

- Reworked the frontend into a routed React/Vite app with Arena, Lab, Reports, and About pages.
- Added market cockpit widgets: order book ladder, liquidity heatmap, market timeline, detector confidence panel, attack tracker, evidence panel, agent event tape, and incident replay drawer.
- Added Nebius AI Investigator panel with mock/real backend integration through the API client.
- Added Experiment Lab with attack builder, benchmark table, Recharts charting, and report summary UI.
- Added Tailwind/PostCSS/ESLint config, React Router, Recharts, and frontend build/lint scripts.
- Removed the old duplicate benchmark page.

### `754b779` - feat: wire FastAPI arena routes and persistence

- Replaced the early runtime wiring with FastAPI arena, simulation, scenario, incident, Nebius, red-team, experiment, and WebSocket routes.
- Added backend `NebiusClient` with typed fallback responses for incident explanations and red-team scenario generation.
- Added local JSONL persistence for experiments, benchmark runs, attacks, incidents, labels, and significant events.
- Added `/api/status`, `/metrics`, `/api/arena/state`, `/api/incidents`, `/api/red-team/generate-scenario`, and `/ws/arena` runtime surfaces.
- Updated backend config/env mapping for Nebius endpoint URLs, tenant metadata, API key, output dirs, and dotenv loading.
- Added backend tests for incident creation/explanation, experiment persistence, and red-team generation.

### `bb27454` - feat: implement accepted arena ARD slice

- Implemented the synthetic L2 order book, arena state models, simulation engine, detector aggregation, and scenario controller.
- Added deterministic scenario state machines for spoofing-like, layering-like, quote-stuffing, and liquidity-evaporation patterns.
- Added detector feature extraction and detector modules for spoofing-like, layering-like, quote-stuffing, and liquidity shock.
- Added structured arena Pydantic schemas and frontend TypeScript arena models.
- Added versioned WebSocket arena state envelope and frontend arena source hook supporting mock and WebSocket modes.
- Added reproducible scenario labels and focused backend/frontend verification coverage.

### `0e6bf98` - chore: ignore local worktrees

- Added `.worktrees/` and related local-development artifacts to `.gitignore`.
- Prevented isolated implementation worktrees from being committed accidentally.

### `c942b59` - feat: initial simple setup

- Added the initial project scaffold for backend, frontend, serverless, docs, assets, data, and outputs.
- Added the first README, license, Makefile, Docker Compose file, environment example, and gitignore.
- Added initial FastAPI backend, Vite frontend, serverless scaffolds, sample data, and documentation structure.
