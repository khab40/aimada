# Nebius AI Serverless Build Plan

Status: Implemented

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
- E2E smoke route: `POST /api/nebius/serverless-smoke/run`
- E2E smoke service: `backend/app/nebius/serverless_smoke.py`

## Platform Narrative

AIMADA generates synthetic suspicious market workloads. Nebius AI Serverless investigates incidents, generates bounded scenarios, and runs detector tournaments. The browser never calls Nebius directly; FastAPI owns endpoint URLs, API keys, request shaping, persistence, and fallback labeling.

## Polished Challenge Demo Path

The judging path is intentionally one story:

`AI-generated spoofing incident -> LOB simulation -> rule-based detector alert -> LLM incident explanation -> AI investigation report -> detector tournament as Nebius Serverless Job -> artifacts and leaderboard`.

Use:

```http
POST /api/nebius/serverless-smoke/run
```

The route reuses existing clients and simulation code, then writes:

- `outputs/serverless-smoke/summary.json`
- `outputs/serverless-smoke/scenario.json`
- `outputs/serverless-smoke/simulation_events.json`
- `outputs/serverless-smoke/detector_alerts.json`
- `outputs/serverless-smoke/investigation_report.md`
- `outputs/serverless-smoke/tournament_result.json`
- `outputs/serverless-smoke/serverless_job.json`
- `outputs/serverless-smoke/manifest.json`

If `NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE`, `NEBIUS_JOB_STATUS_COMMAND_TEMPLATE`, `NEBIUS_JOB_LOGS_COMMAND_TEMPLATE`, and `NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE` are absent, `serverless_job.json` reports `real_nebius_pending`. It does not fake cloud success.

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

Make scenario setup AI-assisted. Nebius AI Serverless generates bounded synthetic market-abuse scenarios that can be replayed in Arena and reused by benchmark jobs.

### Current Code To Reuse

- `NebiusClient.generate_red_team_scenario()` in `backend/app/nebius/client.py`
- `POST /api/nebius/smart-scenario`
- `POST /api/nebius/attack-scenario`
- `POST /api/nebius/attack-scenario/variants`
- `POST /api/nebius/attack-scenario/{scenario_id}/inject`
- `POST /generate-scenario` and `POST /generate-smart-scenario` in `serverless/endpoint/app.py`
- `AttackScenarioGeneratorPage.tsx`
- `AttackBuilder.tsx`
- `SimulationEngine.launch_scenario()` in `backend/app/arena/engine.py`

### Backend Changes

- Keep existing `AttackScenarioInput`, `AttackScenario`, and `ScenarioGridRequest` models in `routes_nebius.py`.
- Add `backend/app/nebius/scenario_generator.py` for the canonical Phase 2 schema:
  - `MarketAbuseScenarioGenerationRequest`
  - `ScenarioEvent`
  - `ScenarioGroundTruth`
  - `ExpectedDetectorBehavior`
  - `CanonicalMarketAbuseScenario`
- Add promoted route:

```http
POST /api/nebius/scenario-generator/generate
```

- Keep current `/api/nebius/attack-scenario*` routes as compatibility paths.
- Persist canonical scenarios to `nebius/generated_market_abuse_scenarios.jsonl`.
- Also persist an `AttackScenario` projection to `nebius/attack_scenarios.jsonl` so the existing inject path remains the replay bridge.

### Serverless Endpoint / Job Changes

- Add endpoint:

```http
POST /generate-market-abuse-scenario
```

- Keep `/generate-scenario` and `/generate-smart-scenario` as aliases/compatibility routes.
- Keep model prompts in `serverless/endpoint/prompts.py`.
- Validate generated values against the canonical enum contract before returning to backend.
- No Serverless Job dependency in Phase 2; jobs consume generated scenario ids later.

### Frontend Changes

- Keep Scenario Setup as secondary flow.
- From `/nebius`, link to `/attack-scenarios?runtime=<mode>`.
- `AttackScenarioGeneratorPage.tsx` should show only demo-relevant controls by default:
  - manipulation type
  - difficulty
  - symbol
  - duration
  - liquidity regime
  - volatility regime
  - generate
  - run in Arena
  - send to AI Investigation
- Primary button label: `Generate AI Scenario`.
- Generated result should show badge text: `Powered by Nebius AI Serverless Endpoint`.
- Advanced controls stay behind `VITE_ENABLE_ADVANCED_ATTACK_CONTROLS`.

### Data Contracts

Generate:

```http
POST /api/nebius/scenario-generator/generate
Content-Type: application/json
```

```json
{
  "manipulation_type": "spoofing",
  "difficulty": "medium",
  "symbol": "AIMD",
  "duration_ticks": 120,
  "liquidity_regime": "thin",
  "volatility_regime": "high",
  "seed": 42
}
```

Response:

```json
{
  "scenario_id": "ai-spoofing-aimd-120-001",
  "title": "Spoofing Pressure Near Mid",
  "description": "Synthetic spoofing workload with visible bid-side depth that cancels before execution.",
  "manipulation_type": "spoofing",
  "difficulty": "medium",
  "symbol": "AIMD",
  "duration_ticks": 120,
  "ground_truth": {
    "label": "spoofing",
    "manipulation_windows": [{"start_tick": 20, "end_tick": 96}],
    "manipulator_agent_ids": ["AI-SPOOF-001"],
    "expected_detector_targets": ["wall_size_ratio", "cancel_to_trade_ratio"],
    "positive_event_ids": ["evt-0020-place", "evt-0024-cancel"]
  },
  "events": [
    {
      "event_id": "evt-0020-place",
      "tick": 20,
      "event_type": "place_order",
      "agent_id": "AI-SPOOF-001",
      "symbol": "AIMD",
      "side": "buy",
      "price": 99.75,
      "quantity": 750,
      "order_id": "ord-0020-a",
      "metadata": {"intent": "visible_depth_pressure"}
    }
  ],
  "expected_detector_behavior": {
    "primary_signals": ["wall_size_ratio", "cancel_to_trade_ratio"],
    "expected_risk_score": 0.76,
    "false_positive_risk": "medium"
  },
  "explanation": "The workload creates transient visible depth and rapid cancellation without real execution.",
  "source": {
    "mode": "mock",
    "provider": "nebius_serverless",
    "endpoint": "/generate-market-abuse-scenario",
    "model": "deterministic-template"
  }
}
```

Inject:

```http
POST /api/nebius/attack-scenario/{scenario_id}/inject
```

Replay mapping:

| Generated type | Existing Arena route |
| --- | --- |
| `spoofing` | `spoofing-like` |
| `layering` | `layering-like` |
| `quote_stuffing` | `quote-stuffing` |
| `wash_trading` | `mixed` projection until direct event replay exists |

### Fallback / Mock Behavior

- Missing endpoint URL, API key, or invalid model JSON returns deterministic scenario with `source.mode: "mock"`.
- Deterministic templates are keyed by manipulation type, difficulty, symbol, duration, liquidity regime, volatility regime, and seed.
- Generated scenario stays launchable because backend writes the compatibility `AttackScenario` projection before returning.
- Ground truth is never dropped in fallback.
- UI must show local template mode when response source is mock or fallback.

### Demo Script

1. Open `/nebius`.
2. Choose `Scenario Generator`.
3. Select `Spoofing`, `Medium`, `AIMD`, `120 ticks`, `Thin`, `High`.
4. Generate scenario.
5. Confirm `Powered by Nebius AI Serverless Endpoint` and source mode.
6. Run in Arena.
7. Send resulting incident to AI Investigation.

### Acceptance Criteria

- Scenario generation works without credentials.
- Generated scenario can be injected into Arena through existing replay path.
- Response stores source mode and ground truth.
- UI shows `Powered by Nebius AI Serverless Endpoint`.
- Advanced controls hidden by default.
- Existing `/api/nebius/attack-scenario*` and `/generate-smart-scenario` behavior remains.

### Risks And Shortcuts

- Risk: generated scenario contains unsupported enum. Shortcut: backend validates canonical schema and falls back to deterministic templates.
- Risk: canonical events are richer than current Arena replay. Shortcut: store events now and project to existing scenario names for replay.
- Risk: `wash_trading` has no dedicated Arena route. Shortcut: replay through `mixed` projection until a direct event replay adapter exists.
- Risk: scenario generator over-promises harm. Shortcut: endpoint prompt and safety note keep synthetic educational scope.
- Risk: too many controls in demo. Shortcut: keep advanced panel feature-flagged.

## Phase 3: AI Detector Tournament Via Nebius Serverless Jobs

### Objective

Run repeatable detector tournaments as Nebius Serverless Jobs. Jobs generate or replay synthetic workloads, run detectors, compare predictions to synthetic ground truth, write artifacts, and return metrics to the command center.

### Current Code To Reuse

- `serverless/jobs/detector_tournament.py`
- `serverless/jobs/run_batch_experiments.py`
- `serverless/jobs/render_job_config.py`
- `serverless/jobs/nebius_job_config.yaml`
- `backend/app/nebius/smart_batch_runner.py`
- `backend/app/experiments/manager.py`
- `backend/app/experiments/nebius_orchestrator.py`
- `POST /api/experiments/benchmark-runs`
- `POST /api/experiments`
- `POST /api/experiments/{id}/run-local-batch`
- `POST /api/experiments/{id}/render-nebius-job-config`
- `POST /api/experiments/{id}/submit-nebius`
- `POST /api/experiments/{id}/refresh-jobs`
- `POST /api/experiments/{id}/collect-nebius-artifacts`
- `POST /api/experiments/{id}/aggregate`

### Backend Changes

- Add Nebius facade routes:

```http
POST /api/nebius/tournament/start
GET /api/nebius/tournament/{id}
GET /api/nebius/tournament/{id}/artifacts
```

- Keep existing experiment APIs working; facade wraps them instead of replacing them.
- Use deterministic mock output for `local_mock` so the backend never runs batch work for the default demo.
- Use capped local `detector_tournament.py` only for explicit `execution_mode=local`.
- Use Managed Experiment ids as job correlation ids for real Nebius Serverless Jobs.
- Render job config into `experiments/{experiment_id}/nebius_job_config.rendered.yaml`.
- Record job state in `experiments/{experiment_id}/jobs.jsonl`.
- Normalize collected artifacts into `experiments/{experiment_id}/artifacts/`.
- Persist facade state under `nebius/tournaments/{tournament_id}/` and append compact rows to `nebius/tournaments.jsonl`.

### Serverless Job Changes

- Use `serverless/jobs/detector_tournament.py` for detector-set comparison:
  - `metrics.csv`
  - `results.json`
  - `benchmark_report.md`
  - `charts/f1_by_scenario.png`
  - `charts/confidence_distribution.png`
  - `charts/detection_latency.png`
- Keep `run_batch_experiments.py` for artifact-heavy managed tournaments:
  - `order_book_events.jsonl`
  - `trades.jsonl`
  - `attack_labels.jsonl`
  - `blue_team_alerts.jsonl`
  - `detector_metrics.csv`
  - `generated_report.md`
  - `manifest.json`
- Keep `--runs`, `--scenarios`, `--detectors`, and `--output` CLI args for `detector_tournament.py`.
- Keep `--runs`, `--batch-size`, `--scenarios`, and `--output` CLI args for `run_batch_experiments.py`.
- Use `serverless/jobs/nebius_job_config.yaml` as base config.

### Frontend Changes

- Keep Detector Tournament inside `NebiusControlPanelPage.tsx`.
- Add a simple `Start Tournament` flow over existing advanced controls.
- Visible controls:
  - number of scenarios
  - manipulation types
  - difficulty mix preset
  - detector set
  - random seed
  - execution mode
- Keep advanced actions available:
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

Start tournament:

```http
POST /api/nebius/tournament/start
Content-Type: application/json
```

```json
{
  "number_of_scenarios": 100,
  "manipulation_types": ["spoofing", "layering", "quote_stuffing"],
  "difficulty_mix": {
    "easy": 0.2,
    "medium": 0.5,
    "hard": 0.2,
    "adversarial": 0.1
  },
  "detector_set": ["spoofing_like", "layering_like", "quote_stuffing"],
  "random_seed": 42,
  "execution_mode": "local"
}
```

Response:

```json
{
  "tournament_id": "TRN-20260706-0001",
  "status": "completed",
  "started_at": "2026-07-06T10:00:00Z",
  "completed_at": "2026-07-06T10:01:12Z",
  "detectors": ["spoofing_like", "layering_like", "quote_stuffing"],
  "leaderboard": [
    {
      "detector": "spoofing_like",
      "scenario": "spoofing",
      "precision": 1.0,
      "recall": 0.75,
      "f1": 0.8571,
      "avg_detection_latency_ms": 1200
    }
  ],
  "metrics": {
    "total_scenarios": 100,
    "total_alerts": 87,
    "macro_f1": 0.81
  },
  "artifacts": {
    "results": "outputs/benchmark/TRN-20260706-0001/results.json",
    "metrics": "outputs/benchmark/TRN-20260706-0001/metrics.csv",
    "report": "outputs/benchmark/TRN-20260706-0001/benchmark_report.md"
  },
  "summary": "Local detector tournament completed with deterministic synthetic ground truth."
}
```

### Fallback / Mock Behavior

- If job submit template is missing, `submit-nebius` records `real_nebius_pending`.
- `local_mock` facade path returns deterministic leaderboard rows without artifacts.
- Explicit `local` facade path runs capped `detector_tournament.py` and returns local leaderboard/artifacts.
- Managed local batch path runs `run_local_smart_batch()` and writes canonical experiment artifact names.
- Aggregation reads local and collected cloud artifacts through the same experiment artifact paths.

### Demo Script

1. Open `/nebius`.
2. Start Detector Tournament.
3. Set `number_of_scenarios=100`.
4. Select `spoofing`, `layering`, `quote_stuffing`.
5. Choose balanced difficulty mix and detector set.
6. Run Local Demo tournament.
7. Show leaderboard, macro F1, latency, and artifacts.
8. Switch to Cloud.
9. Render or submit serverless job.
10. Show pending template status or collect artifacts when job outputs are available.

### Acceptance Criteria

- UI can start a tournament.
- Local/mock tournament produces leaderboard and artifacts.
- Serverless job config renders from experiment settings.
- Missing Nebius submit config does not break demo.
- Aggregation produces summary and leaderboard.
- UI separates endpoint status from job status.

### Risks And Shortcuts

- Risk: remote job setup unavailable during demo. Shortcut: show rendered config and pending job record.
- Risk: artifact paths differ between local and remote. Shortcut: normalize into experiment artifact contract.
- Risk: `wash_trading` is not a native simulator scenario. Shortcut: map to `pump_and_cancel` or manifest metadata until direct replay exists.
- Risk: difficulty mix is not native simulator physics. Shortcut: store it in manifest and use it to weight scenario selection first.
- Risk: large runs cost too much. Shortcut: default demo uses `attack_count=100`, `batch_size=20`; hard cap existing APIs.

## Cross-Phase API Map

| Phase | Browser action | Backend API | Nebius surface | Persistence |
| --- | --- | --- | --- | --- |
| Investigation | Run AI Investigation | `POST /api/nebius/investigation-report` or `POST /api/experiments/{id}/run-investigations` | Endpoint `/investigation-report` | `nebius/investigation_reports.jsonl`, `experiments/{id}/investigations/` |
| Scenario Generator | Generate scenario | `POST /api/nebius/attack-scenario` | Endpoint `/generate-smart-scenario` | `nebius/attack_scenarios.jsonl` |
| Detector Tournament | Start tournament | `POST /api/nebius/tournament/start` | Serverless Job `detector_tournament.py` or `run_batch_experiments.py` | `nebius/tournaments/{id}/`, experiment artifact paths |

## Environment Variables

Endpoint:

```text
NEBIUS_ENDPOINT_BASE_URL
NEBIUS_INCIDENT_EXPLAINER_URL
NEBIUS_SCENARIO_GENERATOR_URL
NEBIUS_ORDERBOOK_ALERT_URL
NEBIUS_INVESTIGATION_REPORT_URL
ENDPOINT_TOKEN
NEBIUS_ENDPOINT_MODE=mock|local_vllm
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
