# Nebius Serverless Use Cases

Status: Draft

Date: 2026-07-06

## Product Position

AIMADA is a Nebius AI Serverless-powered market surveillance platform for synthetic market workloads. It does not analyze real markets and does not provide compliance decisions. The platform value is a complete synthetic workflow:

1. Generate suspicious market workload.
2. Replay it in Arena.
3. Produce detector output and incidents.
4. Investigate with Nebius AI Serverless Endpoint.
5. Generate new scenarios with Nebius AI Serverless Endpoint.
6. Run detector tournaments with Nebius Serverless Jobs.

## Actors

| Actor | Needs |
| --- | --- |
| Demo Operator | Run a reliable local or cloud-backed product demo without Google Auth. |
| Surveillance Reviewer | Read synthetic incident explanations and evidence. |
| Scenario Designer | Generate bounded suspicious workload scenarios. |
| Detector Engineer | Compare detector behavior over many labeled synthetic runs. |
| Technical Judge | Inspect API contracts, artifacts, fallback behavior, and Nebius integration points. |

## Use Case 1: AI Investigation Team

### Objective

Turn detector alerts into structured investigation reports through Nebius AI Serverless Endpoint.

### Reused Code

- `POST /api/nebius/investigation-report`
- `POST /api/experiments/{experiment_id}/run-investigations`
- `NebiusClient.investigation_report()`
- `serverless/endpoint/app.py` route `POST /investigation-report`
- `backend/app/experiments/investigation_pipeline.py`

### Flow

```mermaid
sequenceDiagram
    participant UI as AI Command Center
    participant API as FastAPI
    participant Store as LocalStore
    participant Endpoint as Nebius AI Serverless Endpoint

    UI->>API: POST /api/experiments/{id}/run-investigations
    API->>Store: read alerts and metrics
    API->>Endpoint: POST /investigation-report
    Endpoint-->>API: typed report JSON
    API->>Store: write experiments/{id}/investigations/*.json
    API-->>UI: investigation_count, investigation_mode
```

### Payload Example

```json
{
  "scenario_trace": {"id": "Spoofing Attack #042", "source": "arena"},
  "alerts": [{"alert_id": "batch-000017-wall", "detector": "wall detector", "confidence": 0.91}],
  "metrics": {"precision": 0.82, "f1": 0.79}
}
```

### Acceptance Criteria

- Works with mock fallback.
- Shows real/fallback mode.
- Writes investigation artifacts.
- Keeps synthetic safety framing.

## Use Case 2: AI Scenario Generator

### Objective

Generate bounded synthetic scenarios that can be launched in Arena and reused in tournaments.

### Reused Code

- `POST /api/nebius/attack-scenario`
- `POST /api/nebius/attack-scenario/variants`
- `POST /api/nebius/attack-scenario/{scenario_id}/inject`
- `NebiusClient.generate_red_team_scenario()`
- `serverless/endpoint/app.py` route `POST /generate-smart-scenario`
- `frontend/src/pages/AttackScenarioGeneratorPage.tsx`

### Flow

```mermaid
sequenceDiagram
    participant UI as Scenario Setup
    participant API as FastAPI
    participant Endpoint as Nebius AI Serverless Endpoint
    participant Arena as Arena

    UI->>API: POST /api/nebius/attack-scenario
    API->>Endpoint: POST /generate-smart-scenario
    Endpoint-->>API: scenario JSON
    API-->>UI: AttackScenario
    UI->>API: POST /api/nebius/attack-scenario/{id}/inject
    API-->>Arena: launch workload
```

### Payload Example

```json
{
  "attackType": "Spoofing",
  "marketCondition": "Thin liquidity",
  "objective": "Buy cheaper",
  "stealthLevel": "Medium",
  "attackDuration": "Medium",
  "redTeamAgentCount": 1,
  "detectorDifficulty": "Medium"
}
```

### Acceptance Criteria

- Scenario is launchable.
- Raw endpoint response stored in `source`.
- Mock fallback still produces scenario.
- Advanced tuning stays hidden by default.

## Use Case 3: AI Detector Tournament

### Objective

Run many synthetic workloads and compare detector precision, recall, F1, latency, and artifacts through Nebius Serverless Jobs.

### Reused Code

- `POST /api/experiments`
- `POST /api/experiments/{id}/run-local-batch`
- `POST /api/experiments/{id}/render-nebius-job-config`
- `POST /api/experiments/{id}/submit-nebius`
- `POST /api/experiments/{id}/collect-nebius-artifacts`
- `POST /api/experiments/{id}/aggregate`
- `serverless/jobs/run_batch_experiments.py`
- `serverless/jobs/nebius_job_config.yaml`

### Flow

```mermaid
sequenceDiagram
    participant UI as AI Command Center
    participant API as Experiment API
    participant Job as Nebius Serverless Job
    participant Store as Artifacts

    UI->>API: POST /api/experiments
    UI->>API: POST /api/experiments/{id}/render-nebius-job-config
    UI->>API: POST /api/experiments/{id}/submit-nebius
    API->>Job: run_batch_experiments.py
    Job->>Store: write JSONL/CSV/MD artifacts
    UI->>API: POST /api/experiments/{id}/collect-nebius-artifacts
    UI->>API: POST /api/experiments/{id}/aggregate
```

### Payload Example

```json
{
  "name": "AI-MADA detector tournament",
  "attack_count": 100,
  "batch_size": 20,
  "scenarios": ["normal_market", "spoofing", "layering", "quote_stuffing"],
  "seed": 42
}
```

### Artifact Contract

| Artifact | Purpose |
| --- | --- |
| `order_book_events.jsonl` | Synthetic event stream |
| `trades.jsonl` | Synthetic trade events |
| `attack_labels.jsonl` | Ground-truth scenario labels |
| `blue_team_alerts.jsonl` | Detector alerts |
| `detector_metrics.csv` | Precision, recall, F1, latency inputs |
| `generated_report.md` | Human-readable run report |
| `manifest.json` | Run metadata and artifact paths |

### Acceptance Criteria

- Local fallback and serverless job write same artifact names.
- Pending job state is explicit when submit template missing.
- Aggregation generates summary and leaderboard.
- Artifacts are downloadable from command center.

## Demo Narrative

1. Start in `/nebius`.
2. Show `Powered by Nebius AI Serverless` badge once.
3. Generate scenario.
4. Replay in Arena.
5. Produce detector alert.
6. Run AI Investigation.
7. Create Detector Tournament.
8. Run local fallback or submit serverless job.
9. Show artifacts, metrics, leaderboard, and fallback/real mode labels.

## Non-Goals

- No real market surveillance claims.
- No trading signal generation.
- No browser-side Nebius API key.
- No Google Auth dependency for local demo.
- No rewrite of simulator, detectors, jobs, or report pipeline.
