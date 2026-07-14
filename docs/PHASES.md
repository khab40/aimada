# Project Phases

AI Market Abuse Detection Arena is built as:

- React visual arena
- FastAPI simulator
- synthetic exchange and order book
- normal and abuse-like agents
- deterministic detectors
- Nebius Serverless AI Job benchmark
- Nebius AI / LLM explanations

This project is an educational simulation. The scenarios are synthetic abuse-like patterns for demonstrating order-book anomaly detection and AI Investigator explanations.

## Nebius AI Serverless Build Challenge Overlay

Status: `[done]`

Current product narrative: AIMADA is a Nebius AI Serverless-powered market surveillance command center. The Arena generates suspicious market workloads; Nebius AI Serverless investigates, explains, generates scenarios, and runs detector benchmarks.

Implementation phases:

- `[done]` Phase 1, Nebius AI Investigation Team via Serverless Endpoint: `POST /api/nebius/investigation-team/analyze` forwards incident, detector, order-book, trade, and metric context to `/investigation-team`, with deterministic mock fallback.
- `[done]` Phase 2, Nebius AI Scenario Generator via Serverless Endpoint: `POST /api/nebius/scenario-generator/generate` returns simulator-compatible scenario JSON with ground truth, replay metadata, expected detector behavior, and mock fallback.
- `[done]` Phase 3, Nebius AI Detector Tournament via Serverless Jobs: `POST /api/nebius/tournament/start` queues detector benchmark work, submits configured Nebius jobs when available, or completes a local mock tournament with the same response schema.
- `[done]` Challenge E2E smoke path: `POST /api/nebius/serverless-smoke/run` orchestrates one spoofing incident demo, labels missing cloud job templates as `real_nebius_pending`, and writes `outputs/serverless-smoke/` artifacts.

Primary docs:

- `docs/architecture/ARD-0015-nebius-ai-investigation-team.md`
- `docs/architecture/ARD-0016-ai-scenario-generator.md`
- `docs/architecture/ARD-0017-ai-detector-tournament.md`
- `docs/use-cases/nebius-serverless-use-cases.md`
- `docs/demo-script.md`

## Status Legend

- `[done]` Implemented and committed.
- `[partial]` Implemented enough for the current MVP, with known follow-up gaps.
- `[todo]` Not implemented yet.

## Phase 1: Core Live Arena

Status: `[done]`

Goal: build the minimum live simulator and visual order book loop.

Scope:

- order book
- matching engine
- normal agents
- simulation clock
- WebSocket state stream
- basic UI ladder

Deliverables:

- `[done]` `backend/app/exchange/order_book.py`
- `[done]` `backend/app/exchange/matching_engine.py`
- `[done]` `backend/app/agents/runtime.py` in-process `AgentManager` with deterministic intent sorting and per-tick deadlines
- `[done]` `backend/app/agents/market_maker.py`
- `[done]` `backend/app/agents/noise_trader.py`
- `[done]` `backend/app/agents/liquidity_taker.py`
- `[done]` `backend/app/arena/clock.py`
- `[done]` `backend/app/arena/engine.py`
- `[done]` `backend/app/websocket/broadcaster.py`
- `[done]` `backend/app/websocket/manager.py`
- `[done]` `backend/app/websocket/routes.py`
- `[done]` basic React order book ladder in the Arena screen

Exit criteria:

- `[done]` The simulator ticks continuously when started.
- `[done]` Normal agents generate baseline activity.
- `[done]` The backend can register hundreds of lightweight normal agents while keeping exchange mutation single-writer.
- `[done]` The matching engine updates the synthetic book.
- `[done]` Regression tests cover add/cancel/market flows, price-time priority, partial fills, modify-like quote updates, and L2 snapshots.
- `[done]` The frontend receives or can display live state.
- `[done]` The UI shows bids, asks, best levels, and basic market state.

## Phase 2A: Out-of-Process Agent Runners

Status: `[done]`

Goal: let normal agents run outside the exchange/backend container while preserving one authoritative exchange writer.

Deliverables:

- `[done]` HTTP remote-agent protocol using `MarketSnapshot` requests and `AgentIntent` responses.
- `[done]` backend `RemoteAgentClient` support through `ARENA_REMOTE_AGENT_URLS`.
- `[done]` separate `agent-runner` service and Dockerfile.
- `[done]` Docker Compose wiring for local backend + remote runner separation.
- `[done]` tests for remote intent parsing and local/remote manager composition.

Exit criteria:

- `[done]` Agents can run in a separate container.
- `[done]` Agent runners can be moved to another server by changing `ARENA_REMOTE_AGENT_URLS`.
- `[done]` The exchange/order book remains single-writer in the backend.

## Phase 2: Scenario Agents And Operator Controls

Status: `[done]`

Goal: add manually launched synthetic abuse-like scenarios and visible agent activity.

Scope:

- spoofing-like wall
- layering-like pattern
- quote-stuffing-like burst
- scenario buttons
- agent feed

Deliverables:

- `[done]` `SpoofingLikeAgent`
- `[done]` `LayeringLikeAgent`
- `[done]` `QuoteStuffingLikeAgent`
- `[done]` scenario launch controls in the UI
- `[done]` agent activity feed in the Arena screen
- `[done]` backend scenario controller endpoints

Exit criteria:

- `[done]` The UI can launch each scenario manually.
- `[done]` Active scenario state is visible in the UI.
- `[done]` Agent activity appears in the feed.
- `[done]` Scenario events are labeled for detector and benchmark use.

## Phase 3B: Baseline Liquidity And Quote Ownership

Status: `[done]`

Goal: keep the synthetic exchange two-sided and bounded while hundreds of agents quote into the same book.

Deliverables:

- `[done]` baseline liquidity guard restores configured bid/ask ladder after each tick.
- `[done]` runtime `set_level` intents update per-agent synthetic quotes instead of replacing whole price levels.
- `[done]` `ARENA_BASELINE_LIQUIDITY_*` and `ARENA_MAX_AGENT_QUOTE_SIZE` backend configuration.
- `[done]` regression tests for empty-side reseeding, additive shared-price liquidity, quote clamping, and long-run bounded depth.

Future work:

- `[todo]` browser controls for ladder and quote-cap tuning.
- `[todo]` dynamic reference-price model for drifting market regimes.

## Phase 3A: Heavy And LangGraph Remote Agents

Status: `[done]`

Goal: keep CPU-heavy and LangGraph-based agent decisions outside the exchange/backend process while preserving the same intent protocol.

Deliverables:

- `[done]` `HeavyAnalysisAgent` support with worker-pool execution.
- `[done]` `agent-runner` process-pool configuration for heavy agents.
- `[done]` generic LangGraph remote agents using `StateGraph` observe/decide nodes.
- `[done]` Docker image dependency on `langgraph` for the runner only.
- `[done]` environment controls for heavy and LangGraph agent counts, strategy, and worker pool size.

Exit criteria:

- `[done]` Expensive agent decision work runs outside the backend/exchange process.
- `[done]` LangGraph agents emit the same `AgentIntent` contract as other agents.
- `[done]` The backend stays framework-agnostic and remains the only exchange writer.

## Phase 3: Deterministic Detectors And Incidents

Status: `[done]`

Goal: add deterministic detector logic, confidence scores, incident cards, and evidence extraction.

Scope:

- microstructure features
- confidence scores
- incident cards
- evidence extraction

Deliverables:

- `[done]` `backend/app/detectors/features.py`
- `[done]` spoofing-like detector
- `[done]` layering-like detector
- `[done]` quote-stuffing detector
- `[done]` liquidity-shock detector
- `[done]` aggregate detector score model
- `[done]` incident card UI
- `[done]` Incident Details evidence section

Core features:

- spread bps
- top-N depth
- imbalance
- message rate
- cancel-to-trade ratio
- order lifetime
- wall size ratio

Validation:

- `[done]` Normal market-making features do not alert.
- `[done]` Spoofing-like, layering-like, and quote-stuffing detector paths have focused regression tests.
- `[done]` Deterministic simulation replay is covered for same-seed runs.
- depth change percentage

Exit criteria:

- `[done]` Detector confidence scores update as the simulation runs.
- `[done]` Scenario activity can create incident cards.
- `[done]` Each incident includes structured evidence.
- `[done]` Detector behavior is deterministic for a fixed simulation seed.

## Phase 4: Nebius Benchmark And Explanation Runtime

Status: `[partial]`

Goal: integrate Nebius serverless components for offline benchmark runs and AI Investigator explanations.

Scope:

- Serverless AI Job for benchmark
- Nebius AI endpoint for AI Investigator explanations
- deployment docs
- screenshots of Nebius logs and metrics

Deliverables:

- `[done]` `serverless/jobs/detector_tournament.py`
- `[done]` `serverless/jobs/synthetic_dataset_factory.py`
- `[done]` `serverless/jobs/job_config.example.yaml`
- `[done]` `serverless/jobs/dataset_job_config.example.yaml`
- `[done]` benchmark output directory structure
- `[done]` `serverless/endpoint/app.py`
- `[done]` endpoint explanation and scenario-generation prompts
- `[done]` backend client for endpoint calls
- `[done]` `/orderbook-alert` and `/investigation-report` endpoint contracts for smart detection and report generation
- `[done]` `serverless/jobs/run_batch_experiments.py` for parallel attack/detect batches
- `[done]` `serverless/jobs/nebius_job_config.yaml`
- `[done]` `serverless/jobs/render_job_config.py` for experiment-specific Nebius job config rendering
- `[done]` `serverless/endpoint/endpoint_config.yaml`
- `[done]` reproducibility scripts under `scripts/`
- `[done]` `AI Command Center` UI destination with model selection, inference, batch execution, GPU utilization, datasets, Managed Experiment operations, and artifact access to benchmark outputs
- `[done]` `docs/nebius-deployment.md`
- `[todo]` screenshots under `assets/screenshots/` are still missing except for `.gitkeep`; real Nebius logs/metrics screenshots are still needed.

Benchmark outputs:

- Detector tournament writes:
  - `outputs/benchmark/benchmark_report.md`
  - `outputs/benchmark/metrics.csv`
  - `outputs/benchmark/results.json`
- Synthetic dataset factory writes:
  - `outputs/synthetic-dataset/events.jsonl`
  - `outputs/synthetic-dataset/incidents.jsonl`
  - `outputs/synthetic-dataset/labels.jsonl`
  - `outputs/synthetic-dataset/snapshots.parquet` when Parquet dependencies are available
  - `outputs/synthetic-dataset/snapshots.parquet.jsonl` when Parquet dependencies are unavailable
  - `outputs/synthetic-dataset/manifest.json`
- `[done]` Optional chart artifacts:
  - `outputs/benchmark/charts/f1_by_scenario.png`
  - `outputs/benchmark/charts/confidence_distribution.png`
  - `outputs/benchmark/charts/detection_latency.png`

Exit criteria:

- `[done]` The benchmark job can run multiple synthetic scenarios.
- `[done]` Precision, recall, and F1 are reported by scenario family.
- `[done]` The explanation endpoint returns structured summaries for incidents.
- `[partial]` Deployment documentation includes commands; real Nebius logs/metrics screenshots are still needed for final review.
- `[done]` Real Nebius Endpoint and Job execution is archived in the committed jury evidence bundle with S3 evidence metadata and checksums.

## Phase 4.5: Experiment Manager

Status: `[done]`

Goal: add a first-class experiment manifest layer that coordinates benchmark intent, persisted artifacts, and report visibility without duplicating Nebius Control smart-batch execution.

Deliverables:

- `[done]` `backend/app/experiments/models.py` typed experiment request, status, mode, manifest, and delete response models.
- `[done]` `backend/app/experiments/repository.py` manifest persistence under `outputs/experiments/<experiment_id>/experiment.json`.
- `[done]` `backend/app/experiments/manager.py` experiment creation, listing, lookup, deletion, deterministic attack manifest generation, local batch submission, smart-batch-compatible artifact paths, and report history indexing.
- `[done]` `backend/app/experiments/attack_manifest.py` writes deterministic attack manifests to `outputs/experiments/<experiment_id>/attacks.jsonl` without running the simulator.
- `[done]` `backend/app/experiments/artifact_normalizer.py` copies local-batch outputs into canonical experiment-root artifact names and writes `artifact_index.json` without deleting originals.
- `[done]` `backend/app/experiments/investigation_pipeline.py` runs bounded AI investigation reports over top persisted batch alerts only.
- `[done]` `backend/app/experiments/aggregator.py` writes `experiment_summary.json`, `leaderboard.json`, and `benchmark_report.md` from normalized batch artifacts.
- `[done]` `backend/app/experiments/nebius_orchestrator.py` is the only boundary for real Nebius Serverless Job command-template submission/status/log/artifact adapters.
- `[done]` REST routes on the existing experiment API: `POST /api/experiments`, `GET /api/experiments`, `GET /api/experiments/{id}`, `DELETE /api/experiments/{id}`, `POST /api/experiments/{id}/generate-manifest`, `POST /api/experiments/{id}/run-local-batch`, `POST /api/experiments/{id}/normalize-artifacts`, `POST /api/experiments/{id}/run-investigations`, `GET /api/experiments/{id}/investigations`, `POST /api/experiments/{id}/aggregate`, `GET /api/experiments/{id}/summary`, `GET /api/experiments/{id}/leaderboard`, `GET /api/experiments/{id}/report`, `POST /api/experiments/{id}/render-nebius-job-config`, `POST /api/experiments/{id}/submit-nebius`, `GET /api/experiments/{id}/jobs`, `POST /api/experiments/{id}/refresh-jobs`, and `POST /api/experiments/{id}/collect-nebius-artifacts`.
- `[done]` experiment local batches reuse the same `serverless/jobs/run_batch_experiments.py` execution path as `/api/nebius/smart-batches`.
- `[done]` local batch outputs write to `outputs/experiments/<experiment_id>/local-batch/`, with one `local_parallel_batch` job record in `outputs/experiments/<experiment_id>/jobs.jsonl`.
- `[done]` when real Nebius job execution is not configured, `submit-nebius` writes a `real_nebius_pending` job record instead of pretending cloud execution happened.
- `[done]` when `NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE` is configured, `submit-nebius` executes the command, parses the job id, writes a queued `nebius_serverless_job`, and redacts persisted command output.
- `[done]` `refresh-jobs` can use optional status/log/artifact command templates and only marks a job completed after status and artifact collection both confirm completion.
- `[done]` `collect-nebius-artifacts` collects the existing Nebius job output file format from mounted output or `NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE` into the canonical experiment artifact layout without fabricating missing files.
- `[done]` `/api/nebius/observatory` includes experiment job summary counts when experiment jobs exist.
- `[done]` Reports summary includes managed experiment manifests alongside older attack-builder experiments.
- `[done]` `/nebius` Managed Experiment Lab drives the lifecycle through FastAPI: create, generate manifest, run local or production Jobs, synchronize S3 artifacts, aggregate, run bounded AI Investigator reports, and expose evidence to the UI.
- `[done]` `/nebius` Real Nebius Deployment panel exposes endpoint health checks, route smoke calls, rendered job config, submit-template readiness, latest cloud job status, and cloud artifact collection state without treating pending jobs as successful real-cloud runs.
- `[done]` Detection shows managed experiments with selected summary, scenario leaderboard, markdown benchmark report viewer, AI Investigator reports, `artifact_index.json` links, and original `local-batch` artifacts.
- `[done]` `/api/nebius/smart-batches` remains unchanged for Nebius AI smart-batch execution.
- `[done]` tests for create, list, get, report visibility, delete, deterministic attack manifests, attack counts, expected labels, a 3-run local batch, fake local-batch artifact normalization, mocked Nebius investigations, sample-CSV aggregation, and missing real Nebius config.
- `[done]` local HTTP verification created a 10-row mixed-scenario experiment in mock mode and confirmed manifest rows, normalized artifacts, original local-batch files, summary, leaderboard, benchmark report, and investigation artifacts under `outputs/experiments/<experiment_id>/`.
- `[done]` more than ten production Nebius Serverless AI Job runs validated container execution, scenario generation, detector evaluation, metric aggregation, reporting, logging, and artifact persistence.
- `[partial]` the compact artifact bundle is committed and the judge-facing submission index includes measured runtime/cost records; console screenshots remain publication work.

Current behavior:

- New experiments start in `manifest_generated` status.
- Attack manifests use the experiment's `attack_count`, `scenarios`, and `seed`, preserve the requested scenario mix, and support 10, 100, and 1000-row experiments.
- Expected detector labels are generated for `normal_market`, `spoofing`, `layering`, `quote_stuffing`, and `pump_and_cancel`.
- `run-local-batch` ensures `attacks.jsonl` exists, runs the local parallel batch with experiment `attack_count`, `batch_size`, and `scenarios`, then updates status to `completed` or `failed`.
- `normalize-artifacts` maps `order_book_events.jsonl`, `trades.jsonl`, `attack_labels.jsonl`, `blue_team_alerts.jsonl`, `detector_metrics.csv`, `generated_report.md`, and `manifest.json` into `events.jsonl`, `trades.jsonl`, `labels.jsonl`, `alerts.jsonl`, `detector_metrics.csv`, `benchmark_report.md`, `batch_manifest.json`, and `artifact_index.json`.
- `run-investigations` reads `alerts.jsonl` or `local-batch/blue_team_alerts.jsonl`, selects the top alerts by confidence, calls the existing Nebius investigation-report client once per selected alert, and persists JSON/Markdown reports under `investigations/`.
- The investigation path is batch-only and never calls an LLM for every simulation tick.
- `aggregate` reads `detector_metrics.csv`, alerts, labels, and investigations, reuses CSV metrics as the source of truth, and writes `experiment_summary.json`, `leaderboard.json`, and `benchmark_report.md`.
- `render-nebius-job-config` renders `nebius_job_config.rendered.yaml` for the current experiment without submitting a cloud job.
- `submit-nebius` ensures `attacks.jsonl` exists, renders `nebius_job_config.rendered.yaml`, and records either `real_nebius_pending` when no submit template is configured or a queued `nebius_serverless_job` when the configured submit command returns a job id.
- `collect-nebius-artifacts` maps Nebius job output files into the same canonical artifacts as `normalize-artifacts`; when no mounted output or artifact command output is available, the experiment status becomes `cloud_artifacts_pending`.
- `nebius_mode` supports `mock`, `local_parallel_batch`, and `real_nebius_pending`.
- `smart_batch_id` is optional and is set to the local batch id after `run-local-batch` completes.
- Reports distinguish requested manifest row count from labeled attack rows because mixed experiments can include `normal_market` rows with `expected_has_attack=false`.

## Phase 5: Polish And Submission Assets

Status: `[partial]`

Goal: package the project so it is easy to understand, review, and present.

Scope:

- README
- GitHub banner and visual identity assets
- architecture diagram
- blog post
- short video
- research notes
- sample benchmark report
- UI shell presentation controls

Deliverables:

- `[done]` polished root `README.md` with `assets/img/ai-mada.jpg` GitHub banner
- `[done]` `docs/architecture.md`
- `[partial]` architecture diagrams exist in Mermaid docs; standalone assets under `assets/diagrams/` are still optional/future work.
- `[done]` blog post draft in `docs/linkedin-technical-blog-post.md`
- `[partial]` demo narration scripts and captions under `assets/demo-video/`; rendered demo video is still missing.
- `[done]` `docs/research-notes.md`
- `[done]` committed benchmark report and production evidence under `outputs/benchmark/`
- `[done]` final disclaimer and safety language in README/docs/UI
- `[done]` professional UI shell controls: collapsible Google/auth widget, compact sidebar toggle, day/night/system theme selector, and paused-state-stable Liquidity Map
- `[done]` multiuser platform foundation with demo fallback user/workspace, global workspace/user menu, case ownership metadata, report attribution, and audit trail records.
- `[done]` compact primary navigation: Command Center, Arena / Workload Generator, Scenario Generator, and About
- `[done]` Command Center orchestrates endpoint status, scenario generation, AI investigation, detector tournaments, jobs, and artifacts
- `[done]` Arena three-section layout: Scenario / Attack Configuration, Market, and Detection
- `[done]` About and ARD-0001 architecture diagrams show Front, Back, Agent Runners Workspace, and Nebius Serverless Cloud

### Future work

- Durable backend organization/workspace, case assignment, and audit-log persistence APIs.
- Formal benchmark artifact schema versioning and advanced Judge Mode timeline selectors.
- Richer multi-user workflows and additional scenario families.

Exit criteria:

- `[done]` A reviewer can understand the system from the README and docs.
- `[done]` The demo can be started with documented commands.
- `[done]` The architecture and runtime model are documented.
- `[partial]` The project includes research notes, a blog draft, GitHub banner, UI controls, demo narration, and a committed benchmark evidence bundle; the screenshot set and rendered video remain publication work.
- `[done]` The submission avoids claims about real market manipulation detection, trading signals, or compliance use.
