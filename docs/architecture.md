# High-Level Architecture

Nebius Market Abuse Arena is organized around two execution paths:

- an interactive demo path for live simulation, visualization, incident review, and AI-assisted explanations
- a batch benchmark path for running many synthetic simulations and measuring detector quality

The design keeps the browser UI, demo orchestration backend, local simulation engine, Nebius AI endpoints, and persisted event artifacts separate so each part can evolve independently.

## Interactive Demo Path

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        React / Next UI                              │
│                                                                     │
│  Live Order Book  | Charts | Agent Feed | Scenario Buttons | Alerts │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ WebSocket / REST
                                v
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Demo Backend                        │
│                                                                     │
│  - simulation controller                                             │
│  - WebSocket broadcaster                                             │
│  - scenario launcher                                                 │
│  - incident store                                                    │
│  - calls Nebius AI explanation endpoint                              │
└───────────────┬───────────────────────┬─────────────────────────────┘
                │                       │
                v                       v
┌────────────────────────────┐   ┌────────────────────────────────────┐
│  Local Live Simulation     │   │ Nebius Serverless AI Endpoint       │
│                            │   │                                    │
│  - exchange simulator      │   │  /explain-event                    │
│  - normal agents           │   │  /explain-simulation               │
│  - abuse-like scenarios    │   │  /generate-incident-report         │
│  - detector engine         │   │                                    │
└───────────────┬────────────┘   └────────────────────────────────────┘
                │
                v
┌─────────────────────────────────────────────────────────────────────┐
│                         Event / Snapshot Log                        │
│                                                                     │
│  events.jsonl / snapshots.parquet / incidents.json / reports.md     │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
| --- | --- |
| React / Next UI | Presents the live order book, charts, agent activity, scenario controls, alerts, and incident explanations. It consumes real-time updates over WebSocket and invokes backend actions through REST. |
| FastAPI demo backend | Owns the demo control plane. It starts and stops simulations, launches scenarios, broadcasts state to the UI, persists incidents, and calls Nebius AI endpoints for explanation and report generation. |
| Local live simulation | Runs the in-process market simulation. It models an exchange, normal trading agents, synthetic abuse-like behaviors, and the detector engine. |
| Nebius Serverless AI endpoint | Provides LLM-assisted explanation and summarization APIs for events, whole simulations, and incident reports. |
| Event / snapshot log | Stores replayable event streams, order book snapshots, detected incidents, and generated reports for inspection and offline analysis. |

### Runtime Flow

1. The user starts or controls a scenario from the React / Next UI.
2. The UI sends a REST request to the FastAPI backend.
3. The backend starts or updates the local simulation and subscribes to generated events.
4. The simulation emits order events, snapshots, agent actions, detector signals, and incidents.
5. The backend persists events and snapshots, then broadcasts live updates to connected UI clients over WebSocket.
6. When an explanation or report is requested, the backend calls the Nebius Serverless AI endpoint and stores the generated result.
7. The UI renders the latest market state, detector alerts, incident details, and AI-generated explanations.

## Batch / Benchmark Path

```text
┌─────────────────────────────────────────────────────────────────────┐
│                  Nebius Serverless AI Job                            │
│                                                                     │
│  Run 100-1000 synthetic simulations                                  │
│  Inject spoofing-like / layering-like / quote-stuffing-like patterns │
│  Measure detector precision / recall / F1                            │
│  Generate benchmark report + charts                                  │
└─────────────────────────────────────────────────────────────────────┘
```

The batch path is intended for repeatable detector evaluation rather than live interaction. A serverless job runs many synthetic simulations, injects labeled abuse-like patterns, collects detector outputs, and compares them against the known scenario labels.

### Benchmark Outputs

- detector metrics: precision, recall, F1, false positives, and false negatives
- per-scenario summaries for spoofing-like, layering-like, and quote-stuffing-like patterns
- benchmark charts for report inclusion
- generated benchmark report describing detector behavior and observed failure modes
- persisted raw artifacts for later review and reproducibility

## Data Artifacts

| Artifact | Purpose |
| --- | --- |
| `events.jsonl` | Append-only stream of simulation events, agent actions, detector signals, and state changes. |
| `snapshots.parquet` | Structured order book and market snapshots optimized for offline analysis. |
| `incidents.json` | Detected incidents with metadata, timestamps, involved agents, scenario labels, and detector evidence. |
| `reports.md` | Human-readable AI-generated explanations, incident summaries, and benchmark reports. |

## Architectural Boundaries

- The UI should not directly call the simulation engine or Nebius AI endpoints. It should communicate through the FastAPI backend.
- The simulation engine should emit structured events and detector results without depending on UI concerns.
- The backend should be the integration boundary for live transport, persistence, scenario orchestration, and AI calls.
- Batch benchmark jobs should share simulation and detector code with the live path where practical, but should not depend on the interactive UI.
- Persisted artifacts should be treated as replay and audit inputs, not only as transient logs.
