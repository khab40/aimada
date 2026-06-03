# Accepted ARDs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete and verify the implementation work covered by accepted ARDs `ARD-0001` through `ARD-0006`. Although `ARD-0007` through `ARD-0009` are now accepted, their implementation remains out of scope for this accepted-core plan and should be handled by separate follow-up plans.

**Architecture:** The React/Vite frontend renders a live arena from backend-owned state. The FastAPI backend owns simulation lifecycle, WebSocket state transport, scenario launch, deterministic detector evidence, incident creation, and local artifacts. Nebius serverless jobs/endpoints and Judge Mode are accepted follow-up scopes, but remain outside this accepted-core plan.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, pytest, React, Vite, TypeScript, Docker Compose.

---

## ARD Scope

Approved for implementation:

- `docs/architecture/ARD-0001-overall-architecture.md`
- `docs/architecture/ARD-0002-websocket-state-schema.md`
- `docs/architecture/ARD-0003-detector-evidence-model.md`
- `docs/architecture/ARD-0004-benchmark-artifact-format.md`
- `docs/architecture/ARD-0005-nebius-endpoint-contract.md`
- `docs/architecture/ARD-0006-scenario-labeling-and-reproducibility.md`

Accepted after gate check:

- `docs/architecture/ARD-0007-nebius-serverless-ai-jobs.md`
- `docs/architecture/ARD-0008-nebius-serverless-ai-endpoints.md`
- `docs/architecture/ARD-0009-judge-mode-investigation-reports.md`

Serverless job behavior, deployed endpoint behavior, and Judge Mode routes/UI are now open for their own follow-up implementation plans. Do not implement them as part of this accepted-core plan.

## File Structure

Backend files:

- Modify: `backend/app/websocket/schemas.py` - define the versioned WebSocket message envelope.
- Modify: `backend/app/websocket/manager.py` - serialize `ArenaState` into `ArenaMessage` with `type`, `version`, `timestamp`, and `payload`.
- Modify: `backend/tests/test_websocket_stream.py` - verify envelope shape and payload compatibility.
- Modify: `backend/app/schemas/arena.py` - keep backend Pydantic types aligned with frontend `ArenaState`, detector evidence, and scenario labels.
- Modify: `backend/app/scenarios/base.py` - expose deterministic scenario label metadata.
- Modify: `backend/app/scenarios/controller.py` - return and finalize scenario labels for launches.
- Modify: `backend/app/arena/engine.py` - persist scenario labels and attach label fields to scenario events.
- Modify: `backend/app/storage/local_store.py` - provide append/read helpers for label artifacts.
- Modify: `backend/tests/test_scenario_controller_backend.py` - verify labels, deterministic stage windows, and event labeling.
- Modify: `backend/app/detectors/features.py` - normalize feature names required by ARD-0003.
- Modify: `backend/app/detectors/aggregate.py` - ensure detector output includes confidence, severity, evidence, and features.
- Modify: `backend/tests/test_detectors.py` - verify evidence model and deterministic scores.
- Modify: `backend/tests/test_incidents.py` - verify incidents include evidence and endpoint-ready payloads.

Frontend files:

- Modify: `frontend/src/types/arena.ts` - add the WebSocket envelope type and keep domain types aligned with backend schema.
- Modify: `frontend/src/hooks/useArenaSource.ts` - require versioned `arena_state` messages in WebSocket mode while keeping raw-state compatibility only as a defensive fallback.
- Modify: `frontend/src/pages/ArenaPage.tsx` - display source status/error state when WebSocket envelope parsing fails.
- Modify: `frontend/src/components/EvidencePanel.tsx` - render structured evidence consistently.
- Modify: `frontend/src/components/IncidentReplayDrawer.tsx` - render incident evidence and disclaimer from structured fields.

Docs and verification files:

- Modify: `docs/architecture/ARD-0007-nebius-serverless-ai-jobs.md` only as part of its separate follow-up plan; it is out of scope for this accepted-core implementation plan.
- Modify: `docs/architecture/ARD-0008-nebius-serverless-ai-endpoints.md` only as part of its separate follow-up plan; it is out of scope for this accepted-core implementation plan.
- Modify: `docs/architecture/ARD-0009-judge-mode-investigation-reports.md` only as part of its separate follow-up plan; it is out of scope for this accepted-core implementation plan.
- Modify: `docs/PHASES.md` only to mark verified exit criteria, not to change scope.

---

### Task 1: Enforce ARD Approval Gate

**Files:**
- Read: `docs/architecture/ARD-0001-overall-architecture.md`
- Read: `docs/architecture/ARD-0002-websocket-state-schema.md`
- Read: `docs/architecture/ARD-0003-detector-evidence-model.md`
- Read: `docs/architecture/ARD-0004-benchmark-artifact-format.md`
- Read: `docs/architecture/ARD-0005-nebius-endpoint-contract.md`
- Read: `docs/architecture/ARD-0006-scenario-labeling-and-reproducibility.md`
- Read: `docs/architecture/ARD-0007-nebius-serverless-ai-jobs.md`
- Read: `docs/architecture/ARD-0008-nebius-serverless-ai-endpoints.md`
- Read: `docs/architecture/ARD-0009-judge-mode-investigation-reports.md`

- [x] **Step 1: Confirm accepted ARDs**

Run:

```bash
rg -n "^Status:" docs/architecture/ARD-*.md
```

Expected:

```text
docs/architecture/ARD-0001-overall-architecture.md:Status: Accepted
docs/architecture/ARD-0002-websocket-state-schema.md:Status: Accepted
docs/architecture/ARD-0003-detector-evidence-model.md:Status: Accepted
docs/architecture/ARD-0004-benchmark-artifact-format.md:Status: Accepted
docs/architecture/ARD-0005-nebius-endpoint-contract.md:Status: Accepted
docs/architecture/ARD-0006-scenario-labeling-and-reproducibility.md:Status: Accepted
docs/architecture/ARD-0007-nebius-serverless-ai-jobs.md:Status: Accepted
docs/architecture/ARD-0008-nebius-serverless-ai-endpoints.md:Status: Accepted
docs/architecture/ARD-0009-judge-mode-investigation-reports.md:Status: Accepted
```

- [x] **Step 2: Record follow-up implementation scope**

Do not edit code for serverless jobs, deployed endpoint behavior, or Judge Mode in Task 1. Because `ARD-0007`, `ARD-0008`, and `ARD-0009` are accepted, their gates are open for follow-up plans.

- [x] **Step 3: Commit gate documentation if changed**

If this plan file is the only change:

```bash
git add docs/superpowers/plans/2026-06-03-accepted-ards-implementation.md
git commit -m "docs: add accepted ARDs implementation plan"
```

Expected: one docs-only commit.

---

### Task 2: Versioned WebSocket Envelope

**Files:**
- Modify: `backend/app/websocket/schemas.py`
- Modify: `backend/app/websocket/manager.py`
- Modify: `backend/tests/test_websocket_stream.py`
- Modify: `frontend/src/types/arena.ts`
- Modify: `frontend/src/hooks/useArenaSource.ts`

- [ ] **Step 1: Write failing backend test for ARD-0002 envelope**

Add this test to `backend/tests/test_websocket_stream.py`:

```python
def test_websocket_manager_sends_versioned_arena_message_envelope() -> None:
    async def run() -> None:
        websocket = FakeWebSocket()
        manager = WebSocketManager()
        engine = SimulationEngine()

        await manager.connect(websocket)
        await manager.send_state(websocket, await engine.get_state())

        message = websocket.messages[0]
        assert message["type"] == "arena_state"
        assert message["version"] == 1
        assert isinstance(message["timestamp"], str)
        assert message["payload"]["tick"] == 0
        assert message["payload"]["book"]["bids"]

    asyncio.run(run())
```

- [ ] **Step 2: Run the failing backend test**

Run:

```bash
cd backend && uv run pytest tests/test_websocket_stream.py::test_websocket_manager_sends_versioned_arena_message_envelope -v
```

Expected: FAIL because current messages do not include `version` and `timestamp`.

- [ ] **Step 3: Implement backend envelope schema**

Replace `backend/app/websocket/schemas.py` with:

```python
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ArenaMessage(BaseModel):
    type: Literal["arena_state"] = "arena_state"
    version: int = Field(default=1, ge=1)
    timestamp: str
    payload: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ArenaMessage":
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload,
        )
```

- [ ] **Step 4: Use the envelope from the WebSocket manager**

In `backend/app/websocket/manager.py`, import the schema and update `send_state`:

```python
from app.websocket.schemas import ArenaMessage
```

```python
    async def send_state(self, websocket: WebSocket, state: ArenaState) -> None:
        message = ArenaMessage.from_payload(state.model_dump(mode="json"))
        await websocket.send_json(message.model_dump(mode="json"))
```

- [ ] **Step 5: Run backend WebSocket tests**

Run:

```bash
cd backend && uv run pytest tests/test_websocket_stream.py -v
```

Expected: PASS.

- [ ] **Step 6: Add frontend envelope type**

In `frontend/src/types/arena.ts`, add:

```ts
export type ArenaWebSocketMessage = {
  type: "arena_state";
  version: number;
  timestamp: string;
  payload: ArenaState;
};
```

- [ ] **Step 7: Use the shared frontend type**

In `frontend/src/hooks/useArenaSource.ts`, replace the local `ArenaWebSocketMessage` type with:

```ts
import type { ArenaState, ArenaWebSocketMessage } from "@/types/arena";
```

Then keep parsing logic:

```ts
const message = JSON.parse(event.data) as ArenaWebSocketMessage | ArenaState;
const nextState = "payload" in message ? message.payload : message;
```

- [ ] **Step 8: Build frontend**

Run:

```bash
cd frontend && npm run build
```

Expected: PASS.

- [ ] **Step 9: Commit WebSocket envelope**

Run:

```bash
git add backend/app/websocket/schemas.py backend/app/websocket/manager.py backend/tests/test_websocket_stream.py frontend/src/types/arena.ts frontend/src/hooks/useArenaSource.ts
git commit -m "feat: add versioned arena websocket envelope"
```

---

### Task 3: Scenario Label Records

**Files:**
- Modify: `backend/app/schemas/arena.py`
- Modify: `backend/app/scenarios/base.py`
- Modify: `backend/app/scenarios/controller.py`
- Modify: `backend/app/arena/engine.py`
- Modify: `backend/app/storage/local_store.py`
- Modify: `backend/tests/test_scenario_controller_backend.py`

- [ ] **Step 1: Write failing test for scenario label shape**

Add this test to `backend/tests/test_scenario_controller_backend.py`:

```python
def test_scenario_launch_creates_reproducible_label_record() -> None:
    engine = SimulationEngine(seed=123)

    result = engine.launch_scenario("spoofing-like")
    state = engine.step()

    label = state["active_scenario"]["label"]
    assert result["accepted"] is True
    assert label["scenario_id"] == state["active_scenario"]["scenario_id"]
    assert label["scenario_family"] == "spoofing_like"
    assert label["seed"] == 123
    assert label["start_tick"] == 0
    assert label["expected_end_tick"] >= label["start_tick"]
    assert label["agent_ids"] == ["ABUSER_01"]
    assert label["parameters"]["scenario_name"] == "Spoofing-like Wall"
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
cd backend && uv run pytest tests/test_scenario_controller_backend.py::test_scenario_launch_creates_reproducible_label_record -v
```

Expected: FAIL because `active_scenario.label` does not exist yet.

- [ ] **Step 3: Add `ScenarioLabel` schema**

In `backend/app/schemas/arena.py`, add:

```python
class ScenarioLabel(BaseModel):
    label_id: str
    run_id: str
    scenario_id: str
    scenario_family: str
    scenario_name: str
    seed: int
    start_tick: int
    expected_end_tick: int | None = None
    actual_end_tick: int | None = None
    agent_ids: list[str]
    event_ids: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
```

Update `AttackTrackerState`:

```python
    label: ScenarioLabel | None = None
```

- [ ] **Step 4: Store scenario seed on engine**

Update `SimulationEngine.__init__` in `backend/app/arena/engine.py` to accept `seed: int = 42` and store:

```python
self.seed = seed
self.run_id = f"RUN-{seed:06d}"
```

If the constructor already has a seed parameter, keep its existing behavior and expose `self.seed` and `self.run_id` with the same values.

- [ ] **Step 5: Build label in scenario base**

In `backend/app/scenarios/base.py`, add a method:

```python
    def label_record(self, *, run_id: str, seed: int) -> ScenarioLabel:
        final_rule = self.stage_rules[-1]
        return ScenarioLabel(
            label_id=f"LABEL-{self.scenario_id}",
            run_id=run_id,
            scenario_id=self.scenario_id,
            scenario_family=self.scenario_family,
            scenario_name=self.scenario_name,
            seed=seed,
            start_tick=self.start_tick,
            expected_end_tick=self.start_tick + final_rule.at_tick,
            actual_end_tick=self.stage_ticks.get(AttackStage.DONE),
            agent_ids=[self.agent_id],
            parameters={"scenario_name": self.scenario_name},
        )
```

Also import:

```python
from app.schemas.arena import ScenarioLabel
```

- [ ] **Step 6: Attach label to tracker state**

Update `ScenarioBase.tracker_state()` to accept `run_id: str` and `seed: int`, then pass:

```python
label=self.label_record(run_id=run_id, seed=seed)
```

If existing callers require no arguments, add defaults:

```python
    def tracker_state(self, *, run_id: str = "RUN-000042", seed: int = 42) -> AttackTrackerState:
```

- [ ] **Step 7: Pass run id and seed from engine**

Where `SimulationEngine` calls `scenario.tracker_state()`, change it to:

```python
scenario.tracker_state(run_id=self.run_id, seed=self.seed)
```

- [ ] **Step 8: Persist scenario labels**

In `backend/app/arena/engine.py`, when a scenario starts or updates, persist the label if `self.store` is present:

```python
label = tracker.label
if label is not None and self.store is not None:
    self.store.append_jsonl("labels/scenario_labels.jsonl", label.model_dump(mode="json"))
```

- [ ] **Step 9: Run scenario tests**

Run:

```bash
cd backend && uv run pytest tests/test_scenario_controller_backend.py tests/test_scenario_agents.py -v
```

Expected: PASS.

- [ ] **Step 10: Commit scenario labels**

Run:

```bash
git add backend/app/schemas/arena.py backend/app/scenarios/base.py backend/app/scenarios/controller.py backend/app/arena/engine.py backend/tests/test_scenario_controller_backend.py
git commit -m "feat: add reproducible scenario labels"
```

---

### Task 4: Detector Evidence Contract

**Files:**
- Modify: `backend/app/detectors/features.py`
- Modify: `backend/app/detectors/aggregate.py`
- Modify: `backend/app/schemas/arena.py`
- Modify: `backend/tests/test_detectors.py`
- Modify: `backend/tests/test_incidents.py`

- [ ] **Step 1: Write failing test for required feature names**

Add this test to `backend/tests/test_detectors.py`:

```python
def test_detector_features_include_ard_required_names() -> None:
    engine = SimulationEngine(seed=123)
    engine.launch_scenario("quote-stuffing")

    for _ in range(5):
        state = engine.step()

    features = state["features"]
    required = {
        "spread_bps",
        "order_book_imbalance",
        "top_n_bid_depth",
        "top_n_ask_depth",
        "depth_change_pct",
        "wall_size_ratio",
        "order_lifetime_ms",
        "cancel_to_trade_ratio",
        "message_rate_per_sec",
    }
    assert required <= set(features)
```

- [ ] **Step 2: Run failing feature-name test**

Run:

```bash
cd backend && uv run pytest tests/test_detectors.py::test_detector_features_include_ard_required_names -v
```

Expected: FAIL if any ARD-required feature name is missing.

- [ ] **Step 3: Normalize feature aliases**

In `backend/app/detectors/features.py`, ensure the returned feature dictionary includes both existing UI aliases and ARD-required names:

```python
features["order_book_imbalance"] = features.get("imbalance", 0.0)
features["top_n_bid_depth"] = features.get("top_n_bid_depth", features.get("bid_depth_top_n", 0.0))
features["top_n_ask_depth"] = features.get("top_n_ask_depth", features.get("ask_depth_top_n", 0.0))
features["message_rate_per_sec"] = features.get("message_rate_per_sec", features.get("message_rate", 0.0))
```

Keep existing keys so the current frontend does not break.

- [ ] **Step 4: Write evidence payload test**

Add this test to `backend/tests/test_incidents.py`:

```python
def test_incident_evidence_is_endpoint_ready() -> None:
    async def run() -> None:
        engine = SimulationEngine(seed=123)
        engine.launch_scenario("quote-stuffing")

        for _ in range(5):
            engine.step()

        incident = await engine.get_incident("INC-000001")
        assert incident is not None
        assert incident.evidence

        first = incident.evidence[0]
        assert first.key
        assert first.label
        assert first.value is not None
        assert first.interpretation

    asyncio.run(run())
```

- [ ] **Step 5: Run incident evidence test**

Run:

```bash
cd backend && uv run pytest tests/test_incidents.py::test_incident_evidence_is_endpoint_ready -v
```

Expected: PASS after detector evidence includes complete fields.

- [ ] **Step 6: Run detector and incident suites**

Run:

```bash
cd backend && uv run pytest tests/test_detectors.py tests/test_incidents.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit detector evidence contract**

Run:

```bash
git add backend/app/detectors/features.py backend/app/detectors/aggregate.py backend/app/schemas/arena.py backend/tests/test_detectors.py backend/tests/test_incidents.py
git commit -m "feat: enforce detector evidence contract"
```

---

### Task 5: Accepted Benchmark Artifact Contract Smoke Test

**Files:**
- Modify: `serverless/jobs/run_batch_benchmark.py`
- Modify: `serverless/jobs/detector_tournament.py`
- Modify: `serverless/jobs/synthetic_dataset_factory.py`
- Modify: `serverless/jobs/README.md`
- Test: add or modify `backend/tests/test_benchmark_artifacts.py`

This task verifies the artifact shape from accepted `ARD-0004`. It must not add new Nebius cloud execution behavior because `ARD-0007` implementation remains out of scope for this accepted-core plan and should be handled by a separate follow-up plan.

- [ ] **Step 1: Write artifact-shape test**

Create `backend/tests/test_benchmark_artifacts.py`:

```python
import json
import subprocess
from pathlib import Path


def test_detector_tournament_writes_ard_0004_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "benchmark"
    completed = subprocess.run(
        [
            "python",
            "../serverless/jobs/detector_tournament.py",
            "--runs",
            "3",
            "--scenarios",
            "spoofing,layering",
            "--detectors",
            "baseline",
            "--output",
            str(output),
        ],
        cwd=".",
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert (output / "benchmark_report.md").exists()
    assert (output / "results.json").exists() or (output / "benchmark_results.json").exists()
    assert (output / "metrics.csv").exists() or (output / "detector_metrics.csv").exists()

    results_path = output / "benchmark_results.json"
    if not results_path.exists():
        results_path = output / "results.json"
    decoded = json.loads(results_path.read_text(encoding="utf-8"))
    assert decoded
```

- [ ] **Step 2: Run artifact-shape test**

Run:

```bash
cd backend && uv run pytest tests/test_benchmark_artifacts.py -v
```

Expected: PASS if current serverless job emits compatible artifacts; FAIL if names must be normalized to ARD-0004.

- [ ] **Step 3: Normalize artifact names only if test fails**

If the test fails because names are `results.json` and `metrics.csv`, update the job to write canonical copies:

```python
(output_dir / "benchmark_results.json").write_text(
    json.dumps(results, indent=2),
    encoding="utf-8",
)
(output_dir / "detector_metrics.csv").write_text(
    metrics_csv,
    encoding="utf-8",
)
```

Keep existing filenames if the UI already reads them.

- [ ] **Step 4: Run artifact-shape test again**

Run:

```bash
cd backend && uv run pytest tests/test_benchmark_artifacts.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit artifact contract smoke test**

Run:

```bash
git add backend/tests/test_benchmark_artifacts.py serverless/jobs/run_batch_benchmark.py serverless/jobs/detector_tournament.py serverless/jobs/synthetic_dataset_factory.py serverless/jobs/README.md
git commit -m "test: verify benchmark artifact contract"
```

---

### Task 6: Backend Endpoint Contract Fallback Verification

**Files:**
- Modify: `backend/app/nebius/client.py`
- Modify: `backend/app/api/routes_incidents.py`
- Modify: `backend/tests/test_incidents.py`

This task is allowed under accepted `ARD-0005` only for backend contract and fallback behavior. Do not implement new deployed endpoint behavior from `ARD-0008`.

- [ ] **Step 1: Write fallback response field test**

Add this test to `backend/tests/test_incidents.py`:

```python
def test_mock_explanation_preserves_ard_0005_response_fields() -> None:
    async def run() -> None:
        engine = SimulationEngine(seed=123)
        engine.launch_scenario("quote-stuffing")

        for _ in range(5):
            engine.step()

        incident = await engine.get_incident("INC-000001")
        assert incident is not None

        explanation = NebiusClient(incident_explainer_url="").explain_incident(incident)

        assert explanation.incident_id == "INC-000001"
        assert explanation.risk_level
        assert explanation.plain_english_summary
        assert explanation.evidence
        assert explanation.recommended_action

    asyncio.run(run())
```

- [ ] **Step 2: Run fallback response field test**

Run:

```bash
cd backend && uv run pytest tests/test_incidents.py::test_mock_explanation_preserves_ard_0005_response_fields -v
```

Expected: PASS.

- [ ] **Step 3: Add disclaimer if missing from response type**

If the test is extended to require `disclaimer`, add this field to `IncidentExplanationResponse`:

```python
disclaimer: str = (
    "Educational synthetic simulation only. This does not detect real market manipulation, "
    "does not provide trading signals, and must not be used for compliance decisions."
)
```

- [ ] **Step 4: Run incident tests**

Run:

```bash
cd backend && uv run pytest tests/test_incidents.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit endpoint fallback verification**

Run:

```bash
git add backend/app/nebius/client.py backend/app/api/routes_incidents.py backend/tests/test_incidents.py
git commit -m "test: verify explanation endpoint contract fallback"
```

---

### Task 7: Frontend State and Evidence Rendering Verification

**Files:**
- Modify: `frontend/src/types/arena.ts`
- Modify: `frontend/src/hooks/useArenaSource.ts`
- Modify: `frontend/src/components/EvidencePanel.tsx`
- Modify: `frontend/src/components/IncidentReplayDrawer.tsx`

- [ ] **Step 1: Add TypeScript type check script if missing**

If `frontend/package.json` has no typecheck script, add:

```json
"typecheck": "tsc --noEmit"
```

- [ ] **Step 2: Run frontend type check**

Run:

```bash
cd frontend && npm run typecheck
```

Expected: PASS if TypeScript config supports no-emit checking. If no script existed before Step 1, PASS after adding it.

- [ ] **Step 3: Verify frontend build**

Run:

```bash
cd frontend && npm run build
```

Expected: PASS.

- [ ] **Step 4: Commit frontend verification updates**

Run:

```bash
git add frontend/package.json frontend/src/types/arena.ts frontend/src/hooks/useArenaSource.ts frontend/src/components/EvidencePanel.tsx frontend/src/components/IncidentReplayDrawer.tsx
git commit -m "test: verify frontend arena state contract"
```

---

### Task 8: Full Accepted-ARD Verification

**Files:**
- Read: all files modified by Tasks 2 through 7.

- [ ] **Step 1: Run backend test suite**

Run:

```bash
cd backend && uv run pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend build**

Run:

```bash
cd frontend && npm run build
```

Expected: build completes successfully.

- [ ] **Step 3: Validate Docker Compose config**

Run:

```bash
docker compose config --quiet
```

Expected: exit code `0`.

- [ ] **Step 4: Run local smoke checks**

Run:

```bash
docker compose up -d --build
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/api/status
curl -fsS http://localhost:8000/api/arena/state
curl -fsS -X POST http://localhost:8000/api/simulation/start
curl -fsS -X POST http://localhost:8000/api/scenarios/spoofing-like
```

Expected: all commands exit `0`.

- [ ] **Step 5: Stop local stack**

Run:

```bash
docker compose down
```

Expected: containers stop cleanly.

- [ ] **Step 6: Commit verification notes if docs changed**

If `docs/PHASES.md` or README verification notes were updated:

```bash
git add docs/PHASES.md README.md
git commit -m "docs: record accepted ARD verification"
```

---

## Follow-up Plans

Create separate plans for the accepted follow-up scopes:

- `2026-06-03-nebius-serverless-jobs.md` for `ARD-0007`.
- `2026-06-03-nebius-serverless-endpoints.md` for `ARD-0008`.
- `2026-06-03-judge-mode-investigation-reports.md` for `ARD-0009`.

Each follow-up plan must be independently testable and must not mix job, endpoint, and Judge Mode implementation into one large batch.

## Self-Review

Spec coverage:

- `ARD-0001` is covered by Task 8 full-stack verification.
- `ARD-0002` is covered by Task 2 WebSocket envelope.
- `ARD-0003` is covered by Task 4 detector evidence contract.
- `ARD-0004` is covered by Task 5 artifact contract smoke test.
- `ARD-0005` is covered by Task 6 backend endpoint contract fallback.
- `ARD-0006` is covered by Task 3 scenario labels.
- `ARD-0007`, `ARD-0008`, and `ARD-0009` are accepted, but their implementation remains out of scope for this accepted-core plan and should be handled by separate follow-up plans.

Placeholder scan:

- No task contains open-ended implementation placeholders.
- Each code-changing step includes concrete code snippets or exact command expectations.

Type consistency:

- Backend envelope type is `ArenaMessage`.
- WebSocket message type is `arena_state`.
- Scenario label type is `ScenarioLabel`.
- Detector evidence type is `EvidenceItem`.
- Frontend envelope type is `ArenaWebSocketMessage`.
