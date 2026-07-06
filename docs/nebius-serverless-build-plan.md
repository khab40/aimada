# Nebius AI Serverless Build Plan

Status: Draft

Date: 2026-07-06

## Goal

Reposition AIMADA as a Nebius AI Serverless-powered market surveillance platform. The simulator, detectors, incidents, reports, and benchmark artifacts stay in place, but Nebius AI Serverless becomes the central execution layer for investigation, scenario generation, and detector tournaments.

This plan does not propose a rewrite. It reuses existing code paths:

- Frontend command surface: `frontend/src/pages/NebiusControlPanelPage.tsx`
- Frontend API client: `frontend/src/api/client.ts`
- Backend Nebius routes: `backend/app/api/routes_nebius.py`
- Backend experiment routes: `backend/app/api/routes_experiments.py`
- Nebius client and fallbacks: `backend/app/nebius/client.py`
- Batch investigation pipeline: `backend/app/experiments/investigation_pipeline.py`
- Managed experiment orchestration: `backend/app/experiments/manager.py`, `backend/app/experiments/nebius_orchestrator.py`
- Serverless endpoint: `serverless/endpoint/app.py`
- Serverless jobs: `serverless/jobs/run_batch_experiments.py`, `serverless/jobs/render_job_config.py`, `serverless/jobs/nebius_job_config.yaml`

## Platform Narrative

AIMADA generates synthetic suspicious market workloads. Nebius AI Serverless investigates incidents, generates bounded scenarios, and runs detector tournaments. The browser never calls Nebius directly; FastAPI owns endpoint URLs, API keys, request shaping, persistence, and fallback labeling.

## Phase 1: AI Investigation Team Via Nebius AI Serverless Endpoint

### Objective

Make AI Investigation the first Nebius value path: detector evidence from Arena or Managed Experiments is sent to a Nebius AI Serverless endpoint and returned as a structured investigation report.

### Current Code To Reuse

- `NebiusClient.investigation_report()` in `backend/app/nebius/client.py`
- `POST /api/nebius/investigation-report` in `backend/app/api/routes_nebius.py`
- `POST /api/experiments/{experiment_id}/run-investigations` in `backend/app/api/routes_experiments.py`
- `run_batch_investigations()` in `backend/app/experiments/investigation_pipeline.py`
- `POST /investigation-report` in `serverless/endpoint/app.py`
- UI actions in `frontend/src/pages/NebiusControlPanelPage.tsx`

### Backend Changes

- Keep `POST /api/nebius/investigation-report` as the direct endpoint path.
- Promote `POST /api/experiments/{experiment_id}/run-investigations?top_k=7` as the demo path for batch-generated alerts.
- Persist outputs under:
  - `nebius/investigation_reports.jsonl`
  - `experiments/{experiment_id}/investigations/*.json`
  - `experiments/{experiment_id}/experiment_summary.json`
- Add request correlation fields if missing: `experiment_id`, `alert_id`, `scenario`, `detector`, `run_id`.

### Serverless Endpoint Changes

- Reuse `serverless/endpoint/app.py`.
- Keep `POST /investigation-report` contract.
- Ensure endpoint returns JSON with:
  - `title`
  - `summary`
  - `timeline`
  - `detector_findings`
  - `limitations`
  - `recommended_next_steps`
  - `model_mode`
  - `model`
  - `latency_ms`

### Frontend Changes

- Keep `/nebius` as canonical command center route.
- Primary call sites:
  - `runManagedExperimentInvestigations()` from `frontend/src/api/client.ts`
  - AI Investigation section in `NebiusControlPanelPage.tsx`
- Display mode labels from response:
  - `mode: "nebius"` means real endpoint.
  - `mode: "mock"` means deterministic fallback.
- Surface stored investigation count from `ExperimentSummary.investigation_count`.

### Data Contracts

Backend API:

```http
POST /api/nebius/investigation-report
Content-Type: application/json
```

```json
{
  "scenario_trace": {
    "id": "Spoofing Attack #042",
    "active_window": "last 60 seconds",
    "source": "arena"
  },
  "alerts": [
    {
      "alert_id": "batch-000017-SpoofingWallDetector",
      "run_id": "batch-000017",
      "tick": 12,
      "scenario": "spoofing",
      "detector": "SpoofingWallDetector",
      "confidence": 0.91,
      "evidence": ["large wall near mid", "rapid cancel"]
    }
  ],
  "metrics": {
    "precision": 0.82,
    "recall": 0.76,
    "f1": 0.79,
    "cancel_to_trade_ratio": 5.4
  }
}
```

Response:

```json
{
  "mode": "nebius",
  "endpoint": "https://<endpoint>/investigation-report",
  "title": "Synthetic investigation report: spoofing",
  "summary": "Detector evidence indicates a spoofing-like synthetic pattern.",
  "timeline": ["tick 8: wall appears", "tick 12: alert fired"],
  "detector_findings": ["confidence 0.91 from wall persistence"],
  "limitations": ["synthetic data only"],
  "recommended_next_steps": ["review replay window", "compare detector thresholds"]
}
```

### Fallback / Mock Behavior

- Missing `NEBIUS_INVESTIGATION_REPORT_URL` or `NEBIUS_ENDPOINT_BASE_URL` returns `mode: "mock"` from `NebiusClient._mock_investigation_report()`.
- Endpoint with `NEBIUS_ENDPOINT_MODE=mock` returns `model_mode: "deterministic_fallback"`.
- UI must show fallback labels and must not imply real market surveillance.

### Demo Script

1. Open `/nebius`.
2. Create or refresh a detector tournament.
3. Run Local Demo tournament.
4. Click `Run AI Investigation`.
5. Show investigation count and artifacts.
6. Switch runtime to Cloud.
7. Re-run endpoint health, then investigation path.

### Acceptance Criteria

- `POST /api/nebius/investigation-report` works with no credentials and returns typed fallback.
- `POST /api/experiments/{id}/run-investigations` writes investigation artifacts.
- UI shows investigation output and mode.
- No Google Auth required for local demo.
- Endpoint failures are labeled as fallback, not hidden.

### Risks And Shortcuts

- Risk: alert payload too large. Shortcut: send top `top_k=7` alerts and compact evidence.
- Risk: LLM returns non-JSON. Shortcut: keep deterministic endpoint fallback and response validation.
- Risk: no real endpoint during demo. Shortcut: show `/api/nebius/status` and fallback mode clearly.

## Phase 2: AI Scenario Generator Via Nebius AI Serverless Endpoint

### Objective

Make scenario setup AI-assisted. Nebius AI Serverless generates bounded synthetic attack scenarios that can be injected into Arena and benchmark jobs.

### Current Code To Reuse

- `NebiusClient.generate_red_team_scenario()` in `backend/app/nebius/client.py`
- `POST /api/nebius/smart-scenario`
- `POST /api/nebius/attack-scenario`
- `POST /api/nebius/attack-scenario/variants`
- `POST /api/nebius/attack-scenario/{scenario_id}/inject`
- `POST /generate-smart-scenario` in `serverless/endpoint/app.py`
- `AttackScenarioGeneratorPage.tsx`
- `AttackBuilder.tsx`

### Backend Changes

- Keep existing `AttackScenarioInput`, `AttackScenario`, and `ScenarioGridRequest` models in `routes_nebius.py`.
- Add a promoted route alias only if product copy needs it; do not break current `/api/nebius/*` routes.
- Persist generated scenarios to `nebius/attack_scenarios.jsonl`.
- Keep `inject` path as bridge into Arena workload generation.

### Serverless Endpoint / Job Changes

- Reuse `POST /generate-smart-scenario`.
- Keep model prompt in `serverless/endpoint/prompts.py`.
- Validate generated values against the current bounded enum contract before returning to backend.
- No Serverless Job dependency in Phase 2; jobs consume generated scenario ids later.

### Frontend Changes

- Keep Scenario Setup as secondary flow.
- From `/nebius`, link to `/attack-scenarios?runtime=<mode>`.
- `AttackScenarioGeneratorPage.tsx` should show only demo-relevant controls by default:
  - manipulation type
  - difficulty
  - duration
  - generate
  - run in Arena
  - send to AI Investigation
- Advanced controls stay behind `VITE_ENABLE_ADVANCED_ATTACK_CONTROLS`.

### Data Contracts

Generate:

```http
POST /api/nebius/attack-scenario
Content-Type: application/json
```

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

Response:

```json
{
  "id": "scenario-20260706-001",
  "name": "Spoofing pressure near mid",
  "attackType": "spoofing",
  "targetSide": "buy",
  "objective": "Buy cheaper",
  "marketRegime": "Thin liquidity",
  "redTeamAgents": ["R-17"],
  "startTick": 20,
  "durationTicks": 80,
  "stealthLevel": "medium",
  "expectedDetectorDifficulty": "medium",
  "expectedSignals": ["wall_size_ratio", "cancel_to_trade_ratio"],
  "planSteps": ["place large visible bid", "cancel before execution"],
  "source": {
    "mode": "nebius",
    "endpoint": "https://<endpoint>/generate-smart-scenario"
  }
}
```

Inject:

```http
POST /api/nebius/attack-scenario/{scenario_id}/inject
```

### Fallback / Mock Behavior

- Missing `NEBIUS_SCENARIO_GENERATOR_URL` returns deterministic scenario with `mode: "mock"`.
- Generated scenario still stays launchable because backend builds `AttackScenario` before attaching source metadata.
- UI must show local template mode when response source is mock.

### Demo Script

1. Open `/nebius`.
2. Choose `Scenario Generator`.
3. Select `Spoofing`, `Medium`, `Medium`.
4. Generate scenario.
5. Run in Arena.
6. Send resulting incident to AI Investigation.

### Acceptance Criteria

- Scenario generation works without credentials.
- Generated scenario can be injected into Arena.
- Response stores source mode.
- Advanced controls hidden by default.
- No route removes existing `/api/nebius/attack-scenario*` behavior.

### Risks And Shortcuts

- Risk: generated scenario contains unsupported enum. Shortcut: backend maps to current `AttackScenario` contract and stores raw source separately.
- Risk: scenario generator over-promises harm. Shortcut: endpoint prompt and safety note keep synthetic educational scope.
- Risk: too many controls in demo. Shortcut: keep advanced panel feature-flagged.

## Phase 3: AI Detector Tournament Via Nebius Serverless Jobs

### Objective

Run repeatable detector tournaments as Nebius Serverless Jobs. Jobs generate synthetic workloads, run detectors, write artifacts, and return metrics to the command center.

### Current Code To Reuse

- `serverless/jobs/run_batch_experiments.py`
- `serverless/jobs/render_job_config.py`
- `serverless/jobs/nebius_job_config.yaml`
- `backend/app/nebius/smart_batch_runner.py`
- `backend/app/experiments/manager.py`
- `backend/app/experiments/nebius_orchestrator.py`
- `POST /api/experiments`
- `POST /api/experiments/{id}/run-local-batch`
- `POST /api/experiments/{id}/render-nebius-job-config`
- `POST /api/experiments/{id}/submit-nebius`
- `POST /api/experiments/{id}/refresh-jobs`
- `POST /api/experiments/{id}/collect-nebius-artifacts`
- `POST /api/experiments/{id}/aggregate`

### Backend Changes

- Keep local batch as exact fallback path.
- Use Managed Experiment ids as job correlation ids.
- Render job config into `experiments/{experiment_id}/nebius_job_config.rendered.yaml`.
- Record job state in `experiments/{experiment_id}/jobs.jsonl`.
- Normalize collected artifacts into `experiments/{experiment_id}/artifacts/`.

### Serverless Job Changes

- Keep `run_batch_experiments.py` artifact contract:
  - `order_book_events.jsonl`
  - `trades.jsonl`
  - `attack_labels.jsonl`
  - `blue_team_alerts.jsonl`
  - `detector_metrics.csv`
  - `generated_report.md`
  - `manifest.json`
- Keep `--runs`, `--batch-size`, `--scenarios`, and `--output` CLI args.
- Use `serverless/jobs/nebius_job_config.yaml` as base config.

### Frontend Changes

- Keep Detector Tournament inside `NebiusControlPanelPage.tsx`.
- Primary actions:
  - create benchmark
  - generate manifest
  - run local demo tournament
  - render job config
  - submit serverless job
  - refresh job status
  - collect cloud artifacts
  - aggregate
- Show endpoint status and job status in one compact badge strip.

### Data Contracts

Create experiment:

```http
POST /api/experiments
Content-Type: application/json
```

```json
{
  "name": "AI-MADA detector tournament",
  "attack_count": 100,
  "batch_size": 20,
  "scenarios": ["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"],
  "seed": 42
}
```

Run local fallback:

```http
POST /api/experiments/{experiment_id}/run-local-batch
```

Submit serverless job:

```http
POST /api/experiments/{experiment_id}/submit-nebius
```

Artifact manifest:

```json
{
  "runs": 100,
  "batch_size": 20,
  "scenarios": ["normal_market", "spoofing"],
  "artifacts": {
    "order_book_event_logs": "outputs/.../order_book_events.jsonl",
    "attack_labels": "outputs/.../attack_labels.jsonl",
    "blue_team_alerts": "outputs/.../blue_team_alerts.jsonl",
    "detector_metrics": "outputs/.../detector_metrics.csv",
    "generated_report": "outputs/.../generated_report.md"
  }
}
```

### Fallback / Mock Behavior

- If job submit template is missing, `submit-nebius` records `real_nebius_pending`.
- Local path runs `run_local_smart_batch()` and writes the same artifact names.
- Aggregation reads local and collected cloud artifacts through the same experiment artifact paths.

### Demo Script

1. Open `/nebius`.
2. Create detector tournament.
3. Generate manifest.
4. Run Local Demo tournament.
5. Aggregate and show leaderboard.
6. Render job config.
7. Submit serverless job or show pending template status.
8. Collect artifacts when job outputs are available.

### Acceptance Criteria

- Local tournament produces canonical artifacts.
- Serverless job config renders from experiment settings.
- Missing Nebius submit config does not break demo.
- Aggregation produces summary and leaderboard.
- UI separates endpoint status from job status.

### Risks And Shortcuts

- Risk: remote job setup unavailable during demo. Shortcut: show rendered config and pending job record.
- Risk: artifact paths differ between local and remote. Shortcut: normalize into experiment artifact contract.
- Risk: large runs cost too much. Shortcut: default demo uses `attack_count=100`, `batch_size=20`; hard cap existing APIs.

## Cross-Phase API Map

| Phase | Browser action | Backend API | Nebius surface | Persistence |
| --- | --- | --- | --- | --- |
| Investigation | Run AI Investigation | `POST /api/nebius/investigation-report` or `POST /api/experiments/{id}/run-investigations` | Endpoint `/investigation-report` | `nebius/investigation_reports.jsonl`, `experiments/{id}/investigations/` |
| Scenario Generator | Generate scenario | `POST /api/nebius/attack-scenario` | Endpoint `/generate-smart-scenario` | `nebius/attack_scenarios.jsonl` |
| Detector Tournament | Submit job | `POST /api/experiments/{id}/submit-nebius` | Serverless Job `run_batch_experiments.py` | `experiments/{id}/jobs.jsonl`, artifact paths |

## Environment Variables

Endpoint:

```text
NEBIUS_ENDPOINT_BASE_URL
NEBIUS_INCIDENT_EXPLAINER_URL
NEBIUS_SCENARIO_GENERATOR_URL
NEBIUS_ORDERBOOK_ALERT_URL
NEBIUS_INVESTIGATION_REPORT_URL
NEBIUS_API_KEY
NEBIUS_ENDPOINT_MODE=mock|ai
NEBIUS_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
```

Jobs:

```text
NEBIUS_JOB_IMAGE
NEBIUS_JOB_SUBMIT_TEMPLATE
NEBIUS_JOB_OUTPUT_ROOT
NEBIUS_TENANT_ID
```

Demo feature flags:

```text
ENABLE_GOOGLE_AUTH=false
ENABLE_ADVANCED_ATTACK_CONTROLS=false
ENABLE_LEGACY_PAGES=false
```

## Definition Of Done

- `/nebius` is the default command center and primary product surface.
- AI Investigation uses Nebius endpoint or typed fallback.
- Scenario Generator uses Nebius endpoint or typed fallback.
- Detector Tournament uses local-compatible artifact contract and can submit/render serverless jobs.
- Every fallback is visible in UI and persisted in response mode/status.
- Existing simulator, detectors, reports, and jobs code remain reused.
