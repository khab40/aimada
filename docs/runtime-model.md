# Runtime Model

This document describes how the live arena runs, how agents participate in the exchange simulator, what the main UI screens show, and how runtime APIs and Nebius components fit together.

## Live Exchange Loop

The exchange simulator ticks continuously while the arena is running. A normal local cadence is one tick every 250-500 ms, fast enough for a live visual demo while still leaving the UI readable.

```text
Every 250-500 ms:

1. normal always-on agents act
2. active scenario agents act
3. matching engine processes order events
4. order book state is updated
5. detectors recalculate feature values and confidence scores
6. incidents are emitted when detector thresholds are crossed
7. backend stores event and snapshot artifacts
8. UI receives the new state over WebSocket
```

The backend owns the clock and publishes each state update to connected browser clients. REST endpoints control start, pause, reset, scenario launch, incident explanation, and benchmark summary retrieval.

## Agent Model

### Always-On Agents

These agents provide baseline market activity whenever the arena is running.

| Agent | Runtime Behavior |
| --- | --- |
| `MarketMakerAgent` | Maintains bid and ask liquidity around the current mid price. |
| `NoiseTraderAgent` | Sends random small limit and market orders to create background activity. |
| `LiquidityTakerAgent` | Occasionally sends aggressive buy or sell orders that consume visible liquidity. |

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
[Start] [Pause] [Reset] [Auto Arena: ON/OFF] [Market Regime: Calm/Volatile/Thin]
```

Left panel:

- live order book ladder

Center panel:

- mid-price chart
- spread chart
- order-book imbalance gauge
- detector confidence timeline

Right panel:

- agent activity feed
- active agents
- incident cards

Bottom scenario launcher:

```text
[Spoofing-like Wall]
[Layering-like Pattern]
[Quote Stuffing Burst]
[Liquidity Evaporation]
[Panic Selloff]
```

### 2. Incident Drawer

The incident drawer opens when the user selects an incident card or when a new high-severity alert is raised.

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

The drawer should show detector evidence first, then the generated explanation. AI text is supporting context, not the source of truth.

### 3. Benchmark Screen

The benchmark screen summarizes offline detector quality by scenario family.

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

`MarketMakerAgent`

- maintains bid and ask liquidity around mid price

`NoiseTraderAgent`

- emits random small limit and market orders

`LiquidityTakerAgent`

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
POST /scenario/quote-stuffing-like
POST /scenario/liquidity-evaporation

GET  /incidents
POST /incidents/{id}/explain

GET  /benchmark/latest
```

WebSocket updates should publish the latest order book snapshot, active agent list, recent events, detector scores, active incidents, and simulation status.
