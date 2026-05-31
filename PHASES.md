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

## Phase 1: Core Live Arena

Goal: build the minimum live simulator and visual order book loop.

Scope:

- order book
- matching engine
- normal agents
- simulation clock
- WebSocket state stream
- basic UI ladder

Deliverables:

- `backend/app/exchange/order_book.py`
- `backend/app/exchange/matching_engine.py`
- `backend/app/agents/market_maker.py`
- `backend/app/agents/noise_trader.py`
- `backend/app/agents/liquidity_taker.py`
- `backend/app/arena/clock.py`
- `backend/app/arena/engine.py`
- `backend/app/websocket/broadcaster.py`
- basic React order book ladder in the Arena screen

Exit criteria:

- The simulator ticks continuously when started.
- Normal agents generate baseline activity.
- The matching engine updates the synthetic book.
- The frontend receives or can display live state.
- The UI shows bids, asks, best levels, and basic market state.

## Phase 2: Scenario Agents And Operator Controls

Goal: add manually launched synthetic abuse-like scenarios and visible agent activity.

Scope:

- spoofing-like wall
- layering-like pattern
- quote-stuffing-like burst
- scenario buttons
- agent feed

Deliverables:

- `SpoofingLikeAgent`
- `LayeringLikeAgent`
- `QuoteStuffingLikeAgent`
- scenario launch controls in the UI
- agent activity feed in the Arena screen
- backend scenario controller endpoints

Exit criteria:

- The UI can launch each scenario manually.
- Active scenario state is visible in the UI.
- Agent activity appears in the feed.
- Scenario events are labeled for detector and benchmark use.

## Phase 3: Deterministic Detectors And Incidents

Goal: add deterministic detector logic, confidence scores, incident cards, and evidence extraction.

Scope:

- microstructure features
- confidence scores
- incident cards
- evidence extraction

Deliverables:

- `backend/app/detectors/features.py`
- spoofing-like detector
- layering-like detector
- quote-stuffing-like detector
- liquidity-shock detector
- aggregate detector score model
- incident card UI
- incident drawer evidence section

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

- Detector confidence scores update as the simulation runs.
- Scenario activity can create incident cards.
- Each incident includes structured evidence.
- Detector behavior is deterministic for a fixed simulation seed.

## Phase 4: Nebius Benchmark And Explanation Runtime

Goal: integrate Nebius serverless components for offline benchmark runs and AI-generated explanations.

Scope:

- Serverless AI Job for benchmark
- Serverless AI Endpoint for explanation
- deployment docs
- screenshots of Nebius logs and metrics

Deliverables:

- `serverless/jobs/run_batch_benchmark.py`
- `serverless/jobs/job_config.example.yaml`
- benchmark output directory structure
- `serverless/endpoint/app.py`
- explanation prompts and schemas
- backend client for endpoint calls
- `docs/nebius-deployment.md`
- screenshots under `assets/screenshots/`

Benchmark outputs:

- `outputs/benchmark/benchmark_report.md`
- `outputs/benchmark/benchmark_results.json`
- `outputs/benchmark/incidents.jsonl`
- `outputs/benchmark/detector_metrics.csv`
- `outputs/benchmark/charts/f1_by_scenario.png`
- `outputs/benchmark/charts/confidence_distribution.png`
- `outputs/benchmark/charts/detection_latency.png`

Exit criteria:

- The benchmark job can run multiple synthetic scenarios.
- Precision, recall, and F1 are reported by scenario family.
- The explanation endpoint returns structured summaries for incidents.
- Deployment documentation includes the commands and screenshots needed for review.

## Phase 5: Polish And Submission Assets

Goal: package the project so it is easy to understand, review, and present.

Scope:

- README
- architecture diagram
- blog post
- short video
- research notes
- sample benchmark report

Deliverables:

- polished root `README.md`
- `docs/architecture.md`
- architecture diagram under `assets/diagrams/`
- blog post draft
- short demo video under `assets/demo-video/`
- `docs/research-notes.md`
- sample benchmark report under `outputs/benchmark/`
- final disclaimer and safety language

Exit criteria:

- A reviewer can understand the system from the README and docs.
- The demo can be started with documented commands.
- The architecture and runtime model are documented.
- The project includes supporting research notes and a sample benchmark report.
- The submission avoids claims about real market manipulation detection, trading signals, or compliance use.
