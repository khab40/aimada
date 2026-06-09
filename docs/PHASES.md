# Project Phases

Nebius Market Abuse Arena will be built as:

- React visual arena
- FastAPI simulator
- synthetic exchange and order book
- normal and abuse-like agents
- deterministic detectors
- Nebius Serverless AI Job benchmark
- Nebius Serverless AI Endpoint explanations

This project is an educational simulation. The scenarios are synthetic abuse-like patterns for demonstrating order-book anomaly detection and AI-generated explanations.

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
- `[done]` The matching engine updates the synthetic book.
- `[done]` The frontend receives or can display live state.
- `[done]` The UI shows bids, asks, best levels, and basic market state.

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
- `[done]` incident drawer evidence section

Core features:

- spread bps
- top-N depth
- imbalance
- message rate
- cancel-to-trade ratio
- order lifetime
- wall size ratio
- depth change percentage

Exit criteria:

- `[done]` Detector confidence scores update as the simulation runs.
- `[done]` Scenario activity can create incident cards.
- `[done]` Each incident includes structured evidence.
- `[done]` Detector behavior is deterministic for a fixed simulation seed.

## Phase 4: Nebius Benchmark And Explanation Runtime

Status: `[partial]`

Goal: integrate Nebius serverless components for offline benchmark runs and AI-generated explanations.

Scope:

- Serverless AI Job for benchmark
- Serverless AI Endpoint for explanation
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
- `[done]` `serverless/endpoint/endpoint_config.yaml`
- `[done]` reproducibility scripts under `scripts/`
- `[done]` `Nebius Control Panel` UI tab with observatory widgets and benchmark charts
- `[done]` `docs/nebius-deployment.md`
- `[partial]` screenshots under `assets/screenshots/` exist as placeholders; real Nebius logs/metrics screenshots are still needed.

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
- `[partial]` Deployment documentation includes commands and placeholder screenshots; real Nebius logs/metrics screenshots are still needed for final review.
- `[todo]` Run and archive one real end-to-end Nebius endpoint + job execution with outputs.

## Phase 5: Polish And Submission Assets

Status: `[partial]`

Goal: package the project so it is easy to understand, review, and present.

Scope:

- README
- architecture diagram
- blog post
- short video
- research notes
- sample benchmark report

Deliverables:

- `[done]` polished root `README.md`
- `[done]` `docs/architecture.md`
- `[partial]` architecture diagrams exist in Mermaid docs; standalone assets under `assets/diagrams/` are still optional/future work.
- `[todo]` blog post draft
- `[todo]` short demo video under `assets/demo-video/`
- `[done]` `docs/research-notes.md`
- `[todo]` committed sample benchmark report under `outputs/benchmark/`
- `[done]` final disclaimer and safety language in README/docs/UI

Exit criteria:

- `[done]` A reviewer can understand the system from the README and docs.
- `[done]` The demo can be started with documented commands.
- `[done]` The architecture and runtime model are documented.
- `[partial]` The project includes supporting research notes; sample benchmark report still needs to be generated and committed.
- `[done]` The submission avoids claims about real market manipulation detection, trading signals, or compliance use.
