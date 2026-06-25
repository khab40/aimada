# Changelog

This changelog lists significant commits in reverse chronological order.
Update this file with each significant commit before pushing.

## Unreleased

### Current - feat: render experiment Nebius job configs

- Added `serverless/jobs/render_job_config.py` to render experiment-specific Nebius Serverless Job configs from the existing `serverless/jobs/nebius_job_config.yaml` template.
- Supported overrides for runs, batch size, scenarios, job output directory, and job image repository/tag without adding parallel Dockerfiles or job templates.
- Updated experiment `submit-nebius` to persist `outputs/experiments/<id>/nebius_job_config.rendered.yaml` and include it in job and experiment artifact paths while keeping real cloud execution marked pending.
- Added tests for direct config rendering and experiment submission artifact generation.

### Current - feat: wire backend to deployed serverless endpoint

- Extended backend `NebiusClient` to derive `/orderbook-alert`, `/investigation-report`, `/explain-event`, and `/generate-scenario` from `NEBIUS_ENDPOINT_BASE_URL`.
- Added explicit `NEBIUS_ORDERBOOK_ALERT_URL` and `NEBIUS_INVESTIGATION_REPORT_URL` route overrides alongside the existing incident and scenario overrides.
- Kept Bearer-token forwarding with `NEBIUS_API_KEY`, timeout handling, and mock fallback behavior for unavailable deployed endpoints.
- Added endpoint `/health` probing plus endpoint base/order-book/investigation/mode metadata to `/api/nebius/status` and `/api/nebius/observatory`.
- Added mocked HTTP tests for route derivation, explicit overrides, Bearer auth, deployed order-book/investigation calls, and fallback on endpoint failure.

### Current - fix: harden serverless Nebius endpoint fallback behavior

- Added `/ready` to the existing serverless endpoint app and expanded `/health` with endpoint mode, active model mode, model name, and sanitized credential readiness metadata.
- Added `model`, `model_mode`, and `latency_ms` metadata to endpoint responses where possible.
- Hardened Nebius model JSON parsing and route-specific schema validation so malformed or wrong-shaped AI output falls back deterministically.
- Preserved no-fail deterministic fallback behavior for mock mode, missing credentials, HTTP/model failures, and invalid model JSON without exposing API keys.
- Added endpoint contract tests for mock mode, mocked AI responses, invalid model JSON fallback, and missing-key fallback.

### Current - fix: normalize Nebius endpoint environment names

- Added `NEBIUS_BASE_URL` and `NEBIUS_MODEL` as canonical endpoint AI configuration names, defaulting `NEBIUS_BASE_URL` to `https://api.tokenfactory.nebius.com/v1/`.
- Kept backward compatibility for `NEBIUS_AI_STUDIO_BASE_URL` and `NEBIUS_AI_MODEL` in backend settings and the serverless endpoint runtime.
- Updated serverless env/config examples, Docker Compose, endpoint creation script, and Nebius deployment docs.
- Stopped the Nebius endpoint creation script from printing generated auth tokens.
- Added tests for new-name precedence, old-name fallback, and the tokenfactory default.

### Current - fix: restore backend Docker startup

- Fixed a Python 3.11 import-time annotation crash in `ExperimentManager` where the `list()` method shadowed the builtin `list` for later `list[...]` return annotations.
- Verified the rebuilt backend Docker image can import `app.main` successfully.

### Current - feat: add phase-4.5 experiment manager

- Added a managed experiment manifest layer under `/api/experiments` with create/list/get/delete routes.
- Persisted experiment manifests at `outputs/experiments/<experiment_id>/experiment.json`.
- Added deterministic attack manifest generation with `POST /api/experiments/{id}/generate-manifest`, writing `outputs/experiments/<experiment_id>/attacks.jsonl`.
- Added `POST /api/experiments/{id}/run-local-batch`, reusing the existing smart-batch runner to write `outputs/experiments/<experiment_id>/local-batch/` and `jobs.jsonl`.
- Added `POST /api/experiments/{id}/normalize-artifacts` to copy local-batch outputs into canonical experiment-root artifacts and write `artifact_index.json` without deleting originals.
- Added batch alert investigation with `POST /api/experiments/{id}/run-investigations` and `GET /api/experiments/{id}/investigations`, reusing the existing Nebius investigation-report client against top persisted alerts only.
- Added experiment aggregation with `POST /api/experiments/{id}/aggregate`, `GET /summary`, `GET /leaderboard`, and `GET /report`, reusing existing `detector_metrics.csv` values for scenario precision/recall/F1.
- Added a real Nebius orchestration boundary with `POST /api/experiments/{id}/submit-nebius`, `GET /api/experiments/{id}/jobs`, and `POST /api/experiments/{id}/refresh-jobs`; without real Nebius job configuration it records `real_nebius_pending` instead of faking cloud execution.
- Added experiment job summaries to `/api/nebius/observatory`.
- Upgraded `/nebius` with an Experiment Lab that creates experiments, generates manifests, runs local batches, submits pending Nebius jobs, aggregates, runs investigations, and shows status, jobs, artifacts, and leaderboard data through FastAPI only.
- Integrated Phase 4.5 experiments into `/reports` with an experiment list, selected experiment summary, leaderboard, `benchmark_report.md` viewer, investigation report list, `artifact_index.json` links, and original `local-batch` artifact workbenches.
- Reused smart-batch-compatible artifact path conventions and Reports history indexing without changing `/api/nebius/smart-batches`.
- Added backend tests for managed experiment create, list, get, report visibility, delete behavior, deterministic attack manifests, attack counts, expected labels, a 3-run local batch, fake local-batch artifact normalization, mocked Nebius investigations, sample-CSV aggregation, and missing real Nebius config.
- Verified a local 10-row mixed-scenario experiment end-to-end in mock mode through HTTP APIs, producing normalized experiment artifacts, original local-batch artifacts, aggregation outputs, and seven mock investigation reports.
- Real Nebius Serverless Job execution remains TODO until actual Nebius job evidence, logs, and artifacts exist.

### Current - fix: sync arena tick widgets

- Aligned Liquidity Map, Market Timeline, and Incidents on the same tick window and labels.
- Changed Liquidity Map frame labels from local sequence numbers to real arena ticks.
- Added a persistent Incidents widget label with current/live tick context.
- Fixed detector Confidence graph attack-marker labels so they render as an overlay without shrinking the graph.

### Current - feat: polish AI-MADA branding and UI shell

- Switched the README/GitHub banner to `assets/img/ai-mada.jpg`.
- Added persisted day/night/system theme behavior for the shared UI shell and migrated widgets, charts, status chips, order-book levels, and the Liquidity Map canvas to theme-aware tokens.
- Made the Google/auth widget collapsible and retained a compact authenticated account control.
- Tightened the vertical navigation collapse/expand control and removed the stale product subtitle from the UI shell.
- Stopped the Liquidity Map from appending or shifting frames while the arena tick is not advancing.
- Added ARD-0013 and refreshed README, architecture, design ideas, phase status, and use-case docs for the current UI/auth/runtime state.

### Current - feat: add Google authentication persistence

- Added Google ID token verification with `google-auth` and optional authorization-code exchange using configured Google OAuth credentials.
- Added SQLite-backed Google user persistence with `id`, `email`, `name`, `avatar_url`, `google_id`, `auth_provider`, `created_at`, and `updated_at`.
- Added app-issued JWT sessions so Google tokens are only verification input, not long-lived app sessions.
- Wired the frontend Google button to Google Identity Services authorization-code flow when Google auth is configured.
- Fixed the GIS popup code exchange path to pass the browser origin consistently and return Google token-exchange details in 401 responses.
- Added ARD-0012 and tests for verified Google login, DB storage, JWT lookup, and configured-mode validation.

### Current - fix: preserve baseline exchange liquidity

- Added a baseline liquidity guard that restores a configured minimum bid/ask ladder after each simulation tick.
- Added per-agent level updates so runtime agents quoting the same price add independent synthetic orders instead of overwriting the whole price level.
- Added `ARENA_BASELINE_LIQUIDITY_*` and `ARENA_MAX_AGENT_QUOTE_SIZE` backend configuration plus regression tests for empty-side reseeding, shared-price agent liquidity, quote clamping, and long-run bounded depth.

### Current - feat: add phase-3 LangGraph remote agents

- Added generic LangGraph remote agents in `agent-runner` using `StateGraph` observe/decide nodes.
- Added heavy-agent worker-pool execution inside `agent-runner` so expensive decisions stay out of the backend/exchange process.
- Added `AGENT_RUNNER_HEAVY_AGENT_*` and `AGENT_RUNNER_LANGGRAPH_*` configuration in Docker Compose.
- Added ARD-0010 and updated architecture/runtime docs for local, remote, heavy, and LangGraph-compatible agent execution.

### Current - feat: add phase-2 remote agent runners

- Added HTTP remote-agent runner support through `RemoteAgentClient` and `ARENA_REMOTE_AGENT_URLS`.
- Added a separate `agent-runner` service with `/health`, `/agents`, and `/decide` endpoints.
- Updated Docker Compose so normal agents can run outside the backend/exchange container by default.
- Added tests for remote runner intent parsing and local/remote agent manager composition.

### Current - feat: add phase-1 in-process agent scheduler

- Added an in-process `AgentManager` that registers scalable normal agents, gathers per-tick intents with a deadline, sorts intents deterministically, and keeps order-book mutation single-writer.
- Added generated normal-agent support through `ARENA_AGENT_COUNT` and `ARENA_AGENT_DECISION_TIMEOUT_SECONDS`; Docker Compose defaults the backend to 200 normal agents.
- Added focused tests for hundreds of registered agents, deterministic intent ordering, deadline drops, and high-agent-count engine ticks.
- Updated runtime and phase docs to describe the agent scheduler boundary and future out-of-process agent-runner path.

### Current - rename product and mark implementation status

- Renamed the product identity from the old Nebius-branded project name to AI Market Abuse Detection Arena across UI labels, package/service names, docs, scripts, manifests, and demo assets.
- Updated the README with a current implementation snapshot and open gaps.
- Added implementation status sections to ARD-0001 through ARD-0009 and summarized done/partial work in the ARD index.
- Updated design ideas and phase tracking to mark implemented, partial, and missing pieces, including Judge Mode, screenshots, demo video, and sample benchmark artifacts.

### Current - fix: align cloud lab UI, replay reports, and education flow

- Split the high-level UI into clearer newcomer workflows: Market Arena, Red Team Attack Scenario Generator, Blue Team Surveillance, Nebius Control Panel, Replay & Reports, and About.
- Moved concrete attack-plan creation out of Nebius Control Panel so the red-team tab owns attack scenario generation, variants, injection, Nebius batch submission, and scenario templates.
- Added blue-team surveillance views for live detector scores, suspicious agents, evidence, incident replay, Nebius detection, and AI incident reports.
- Added replay/report cleanup with a typed confirmation dialog and backend clear endpoint for local persisted evidence.
- Added backend-backed artifact workbench actions for preview, keyboard navigation, export to Markdown/PDF, benchmark comparison, incident replay, screenshot attachment, and evidence promotion.
- Added red/blue geometric team marks and route-level branding without cartoon imagery.
- Updated About copy for a newcomer-friendly educational story, ML mental model, market-abuse consequences, guardrails, and runtime flow.
- Updated architecture, use-case, ARD, and phase documentation to match the current cloud-native AI laboratory workflow.

## 2026-06-09

### `4553a5e` - Add Nebius control panel and serverless workflows

- Added a Nebius Control Panel UI for cloud runtime status, AI analyst actions, serverless batch experiments, scenario grids, artifacts, usage/cost, and deployment health.
- Added backend Nebius observatory and smart batch APIs with typed mock adapters that can later be replaced by real Nebius SDK/API calls.
- Added reproducible scripts for scenario generation, local evaluation, Nebius job submission, endpoint calls, and endpoint/job creation.
- Added serverless endpoint and job Docker/config artifacts under the consolidated `serverless/` tree.
- Added report/artifact UI actions for benchmark outputs, Nebius logs/metrics evidence, export, comparison, replay, and promoted challenge bundles.
- Updated README, quickstart, deployment docs, ARDs, and phase tracking for Nebius Serverless AI Jobs and Endpoints.

## 2026-06-08

### `ee25dd5` - fix: documentation updates

- Added editor recommendations and a one-slide market-abuse arena visual asset.
- Added an AI Market Abuse Detection Arena one-pager and updated the overall architecture ARD.
- Refined Arena/Lab UI copy and scenario-launch styling.
- Updated Nebius endpoint creation script details and included the modeling document artifact.

## 2026-06-04

### `2ad792d` - docs: add 3D market battlefield concept artifacts

- Documented the 3D Market Battlefield simulator idea in `docs/DESIGN-IDEAS.md`.
- Added the detailed 3D LOB terrain concept under `docs/3d-concept-lob.md`.
- Added detached frontend prototype artifacts under `frontend/src/tabs/MarketBattlefield3D/`.
- Added game-scenario visual concept artifacts under `assets/game-scenario/`.
- Kept the 3D tab detached from the main UI navigation while preserving the prototype code for future iteration.

## 2026-06-03

### `6709f20` - feat: wire Nebius jobs and polish arena operations

- Wired the Lab "Run on Nebius Serverless Job" action through FastAPI to execute `serverless/jobs/detector_tournament.py` and parse produced benchmark artifacts.
- Updated backend Docker packaging so the FastAPI container includes `serverless/jobs` and can run the detector tournament path in Docker.
- Added persistent incident explanation records under `incidents/explanations.jsonl` and exposed them in Reports as Nebius analysis history.
- Polished the Arena cockpit toward a denser FinTech terminal UI with better viewport usage, responsive heatmap sizing, tighter panels, and clearer market-data styling.
- Made Arena Start/Pause/Reset controls state-dependent to avoid duplicate starts and invalid resets.
- Added a browser/site icon and web manifest for the AI Market Abuse Detection Arena UI.
- Added a concise one-pager under `assets/` describing AI Market Abuse Detection Arena as an early-stage product demo and future near-real-time detection direction.
- Updated `docs/PHASES.md` with status markers and aligned Phase 4 artifacts with the current serverless job outputs.

### `0c1f58b` - fix: preserve labeled legacy scenario runtime

- Kept the legacy scenario-agent and `LiveArenaRuntime` path because committed tests and older scenario-controller code still reference it.
- Added scenario metadata propagation to spoofing-like, layering-like, and quote-stuffing-like agents.
- Added scenario launch support to `LiveArenaRuntime` and covered it with tests.
- Extended the matching engine to preserve scenario identifiers on cancel, limit-order, and market-order events.

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
