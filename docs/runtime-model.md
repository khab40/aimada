# Runtime Model

This document describes how the live arena runs, how agents participate in the exchange simulator, what the main UI screens show, and how runtime APIs and Nebius components fit together.

The continuous interactive arena and the versioned deterministic batch kernel are Java-only production authorities. Python remains for AI/ML, LangGraph-capable runner work, experiments, and serverless jobs.

## Live Exchange Loop

The exchange simulator ticks continuously while the arena is running. A normal local cadence is one tick every 250-500 ms, fast enough for a live visual demo while still leaving the UI readable.

```mermaid
flowchart TD
    Tick["Java arena tick<br/>250-500 ms"]
    Remote["Python agent-runner<br/>normal, heavy, ML/LangGraph"]
    Scenario["Java bounded scenarios"]
    Sort["Validate + deadline-filter + deterministic sort"]
    Exchange["Single-writer exchange + matching"]
    Guard["Restore baseline two-sided liquidity"]
    Detect["Feature extraction + deterministic detectors"]
    Persist["Events, incidents, snapshots, reports"]
    UI["WebSocket arena_state"]

    Tick -->|"MarketSnapshot"| Remote
    Tick --> Scenario
    Remote -->|"AgentIntent"| Sort
    Scenario -->|"labeled intent"| Sort
    Sort --> Exchange
    Exchange --> Guard
    Guard --> Detect
    Detect --> Persist
    Detect --> UI
    UI --> Tick
```

Java owns the clock and publishes each state update to connected browser clients. Java REST endpoints control start, pause, reset, scenario launch, incident lookup, and replay. FastAPI owns incident explanation, AI, experiment, and serverless APIs.

Agents run behind Python `agent-runner` `/decide` endpoints because this is the retained AI/ML and LangGraph boundary. Java concurrently gathers responses under a deadline, validates them, and sorts intents by tick, latency bucket, agent id, sequence, and kind before single-writer book mutation.

Runtime scale knobs:

```text
ARENA_DATA_RETENTION_DAYS=1
ARENA_REMOTE_AGENT_URLS=http://agent-runner:9100
ARENA_REMOTE_AGENT_TIMEOUT_MS=250
ARENA_TICK_INTERVAL_MS=500
ARENA_WEBSOCKET_STREAM_INTERVAL_MS=500
JAVA_ARENA_BASE_URL=http://java-kernel:8080
JAVA_ARENA_TIMEOUT_SECONDS=2
AGENT_RUNNER_AGENT_COUNT=24
AGENT_RUNNER_MAX_AGENT_COUNT=48
AGENT_RUNNER_HEAVY_AGENT_COUNT=0
AGENT_RUNNER_MAX_HEAVY_AGENT_COUNT=2
AGENT_RUNNER_HEAVY_AGENT_WORKERS=1
AGENT_RUNNER_MAX_HEAVY_AGENT_WORKERS=1
AGENT_RUNNER_LANGGRAPH_AGENT_COUNT=0
AGENT_RUNNER_MAX_LANGGRAPH_AGENT_COUNT=4
AGENT_RUNNER_LANGGRAPH_STRATEGY=liquidity_rebalancer
```

Docker Compose starts `java-kernel`, `agent-runner`, `backend`, and `frontend` together. Agents that miss the Java-side decision deadline are skipped for that tick. Runtime `set_level` intents update bounded per-agent synthetic quotes, worker-side `AGENT_RUNNER_MAX_*` values cap runner size, and Java restores baseline two-sided liquidity after each tick. Java writes arena events, attacks, incidents, and snapshots under `ARENA_OUTPUT_DIR`; FastAPI applies retention to its AI/serverless artifacts.

A runner exposes `POST /decide`, receives a read-only `MarketSnapshot`, and returns `AgentIntent` JSON. In Compose, Java points at `http://agent-runner:9100` by default. Only Java applies accepted intents to the exchange.

Heavy agents run expensive decision functions through a worker pool inside `agent-runner`. Generic LangGraph agents use `StateGraph` with `observe` and `decide` nodes, then emit the same `AgentIntent` contract. Java is deliberately unaware of whether an intent came from a simple function, ML model, process-pool worker, or LangGraph graph.

## UI Shell Runtime

The shared shell keeps presentation preferences in browser-local state, not backend state. Theme mode is stored as `lob-arena.themePreference` with `system`, `light`, and `dark` values. System mode follows `prefers-color-scheme` and applies the resolved mode through the document `data-theme` attribute. Shared widgets, status chips, order-book levels, Recharts timelines, tooltips, and the Liquidity Map canvas read semantic theme tokens rather than fixed dark colors.

Arena timeline-style widgets should only append frames when the backend tick advances. This keeps the Liquidity Map visually stable while the arena is paused or has not started from the UI.

## Agent Model

### Always-On Agents

These agents provide baseline market activity whenever the arena is running.

| Agent | Runtime Behavior |
| --- | --- |
| `TopOfBookMarketMaker` | Maintains bid and ask liquidity around the current mid price. |
| `DeterministicNoiseTrader` | Sends deterministic small depth updates to create background activity. |
| `PeriodicLiquidityTaker` | Occasionally sends aggressive buy or sell orders that consume visible liquidity. |
| Additional generated normal agents | Scale the same lightweight decision model to hundreds of registered agents. |

### Scenario Agents

Scenario agents are launched manually from the UI. They run for a bounded interval and inject labeled synthetic behavior for detector and explanation demos.

| Scenario Agent | Runtime Behavior |
| --- | --- |
| `SpoofingLikeAgent` | Places a large short-lived visible wall, then cancels before execution. |
| `LayeringLikeAgent` | Places multiple same-side levels, then cancels them as a group. |
| `QuoteStuffingLikeAgent` | Generates many place and cancel updates in a short time window. |
| `LiquidityEvaporationScenario` | Removes visible depth quickly and stresses liquidity-shock features. |
| `PanicSelloffScenario` | Sends aggressive sell pressure to simulate a sudden disorderly move. |

## Main UI Screens

### 1. Arena

The Arena screen is the live operator view.

Top bar:

```text
[Running/Paused] [Tick] [Selected Scenario] [Connection/Source] [Start] [Pause] [Reset]
```

Left section - Scenario / Attack Configuration:

- selected scenario and attack configuration
- Start / Pause / Reset controls
- attack builder and scenario launch controls

Center section - Market:

- Standard or Battlefield visualization mode
- order book ladder
- mid-price, spread, depth, and microstructure metrics
- switchable Heatmap and Timeline secondary views

Right section - Detection:

- detector confidence
- Evidence / Timeline tabs
- Incident Details with AI Investigator and AI cost/latency metrics

Scenario launcher examples:

```text
[Spoofing-like Wall]
[Layering-like Pattern]
[Quote Stuffing Burst]
[Liquidity Evaporation]
```

### 2. Incident Details

Incident Details opens when the user selects an incident card or when a new high-severity alert is raised.

```text
Suspicious Event Detected

Type: Spoofing-like liquidity wall
Agent: ABUSER_01
Confidence: 0.91
Severity: High

Evidence:
- ask depth increased 480%
- order lifetime 1.8 sec
- cancellation before execution
- imbalance shifted from +0.08 to -0.74

AI explanation:
...
```

Incident Details should show detector evidence first, then the generated explanation. AI text is supporting context, not the source of truth.

### 3. Detection / Experiments Benchmark Review

Detection and Experiments summarize offline detector quality by scenario family, replay evidence, generated reports, and Managed Experiment artifacts.

| Scenario | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| Spoofing-like wall | 0.91 | 0.86 | 0.88 |
| Layering-like | 0.84 | 0.79 | 0.81 |
| Quote stuffing | 0.96 | 0.92 | 0.94 |
| Liquidity shock | 0.89 | 0.83 | 0.86 |

## Core Runtime Modules

### `exchange/`

`order_book.py`

- `add_limit_order()`
- `cancel_order()`
- `apply_market_order()`
- `get_l2_snapshot()`
- `get_best_bid_ask()`

`matching_engine.py`

- `process_event()`
- `match_market_order()`
- `update_book()`

`event_log.py`

- `append_event()`
- `replay_events()`

### `agents/`

`runtime.py`

- `AgentIntent`
- `MarketSnapshot`
- `AgentManager`
- `build_normal_agents()`
- `build_heavy_agents()`

`TopOfBookMarketMaker`

- maintains bid and ask liquidity around mid price

`DeterministicNoiseTrader`

- emits deterministic small depth updates

`PeriodicLiquidityTaker`

- occasionally sends aggressive buy and sell orders

`SpoofingLikeAgent`

- places a large short-lived wall and cancels before execution

`LayeringLikeAgent`

- places multiple same-side levels and then cancels them

`QuoteStuffingLikeAgent`

- generates many place and cancel updates in a short window

### `detectors/`

`features.py`

- `spread_bps`
- `depth_top_n`
- `imbalance`
- `message_rate`
- `cancel_to_trade_ratio`
- `order_lifetime`
- `wall_size_ratio`
- `depth_change_pct`

`spoofing_detector.py`

- detects short-lived large visible walls

`layering_detector.py`

- detects coordinated same-side multi-level orders

`quote_stuffing_detector.py`

- detects high update and cancel rates with low execution ratio

`liquidity_shock_detector.py`

- detects depth collapse and spread widening

### `explain/`

The explanation layer receives structured incident evidence and returns a user-facing summary.

Input:

```json
{
  "incident_id": "INC-00042",
  "type": "spoofing_like_wall",
  "confidence": 0.91,
  "evidence": {
    "wall_size_ratio": 8.4,
    "order_lifetime_ms": 1800,
    "cancelled_before_execution": true,
    "imbalance_before": 0.08,
    "imbalance_after": -0.74
  }
}
```

Output:

```json
{
  "title": "Spoofing-like liquidity wall detected",
  "risk_level": "high",
  "plain_english_summary": "...",
  "evidence": ["...", "..."],
  "recommended_action": "Flag this interval for manual review."
}
```

## Nebius Components

### Serverless AI Job

Purpose: run offline benchmark simulations.

```bash
python -m serverless.jobs.run_batch_benchmark \
  --runs 200 \
  --scenarios spoofing,layering,quote_stuffing,liquidity_evaporation \
  --output outputs/benchmark
```

Expected output structure:

```text
outputs/benchmark/
  benchmark_report.md
  benchmark_results.json
  incidents.jsonl
  detector_metrics.csv
  charts/
    f1_by_scenario.png
    confidence_distribution.png
    detection_latency.png
```

### Serverless AI Endpoint

Purpose: explain detected incidents and simulation outcomes.

```text
GET  /health
POST /explain-event
POST /explain-simulation
POST /generate-report
```

## API Design

The live demo backend should expose a compact control API for the UI.

```text
GET  /health

POST /simulation/start
POST /simulation/pause
POST /simulation/reset

POST /scenario/spoofing-like
POST /scenario/layering-like
POST /scenario/quote-stuffing
POST /scenario/liquidity-evaporation

GET  /incidents
POST /incidents/{id}/explain

GET  /benchmark/latest
```

WebSocket updates should publish the latest order book snapshot, active agent list, recent events, detector scores, active incidents, and simulation status.
