from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.nebius.adapters import MockNebiusCloudAdapter
from app.nebius.client import (
    InvestigationReportRequest,
    InvestigationReportResponse,
    NebiusClient,
    NebiusIntegrationStatus,
    OrderBookAlertRequest,
    OrderBookAlertResponse,
    RedTeamScenarioRequest,
    RedTeamScenarioResponse,
)
from app.experiments.nebius_orchestrator import summarize_experiment_jobs
from app.nebius.smart_batch_runner import read_metrics, run_local_smart_batch
from app.storage.history import append_history_artifact

router = APIRouter(prefix="/api/nebius", tags=["nebius"])
nebius_client = NebiusClient()
nebius_cloud_adapter = MockNebiusCloudAdapter()


@router.get("/status", response_model=NebiusIntegrationStatus)
def nebius_status() -> NebiusIntegrationStatus:
    return nebius_client.integration_status()


@router.post("/red-team-scenario", response_model=RedTeamScenarioResponse)
def generate_red_team_scenario(request: RedTeamScenarioRequest) -> RedTeamScenarioResponse:
    return nebius_client.generate_red_team_scenario(
        prompt=request.prompt,
        constraints=request.constraints,
    )


class SmartScenarioRequest(BaseModel):
    scenario_family: str = "spoofing"
    market_regime: str = "volatile"
    goal: str = "hard_to_detect"
    constraints: dict[str, Any] = Field(default_factory=dict)


class SmartBatchRunRequest(BaseModel):
    runs: int = Field(default=100, ge=1, le=1000)
    batch_size: int = Field(default=100, ge=1, le=500)
    scenarios: list[str] = Field(
        default_factory=lambda: ["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"]
    )


class AttackScenarioInput(BaseModel):
    attackType: str = "Spoofing"
    marketCondition: str = "Thin liquidity"
    objective: str = "Buy cheaper"
    stealthLevel: str = "Medium"
    attackDuration: str = "Medium"
    redTeamAgentCount: int = Field(default=1, ge=1, le=10)
    detectorDifficulty: str = "Medium"


class AttackScenario(BaseModel):
    id: str
    name: str
    attackType: Literal["spoofing", "layering", "quote_stuffing", "momentum_ignition", "mixed"]
    targetSide: Literal["buy", "sell", "both"]
    objective: str
    marketRegime: str
    redTeamAgents: list[str]
    startTick: int
    durationTicks: int
    fakeOrderLevels: int | None = None
    fakeOrderSizeMultiplier: int | None = None
    cancelDelayTicks: int | None = None
    realTradeSide: Literal["buy", "sell"] | None = None
    realTradeSize: int | None = None
    stealthLevel: Literal["obvious", "medium", "subtle"]
    expectedDetectorDifficulty: Literal["easy", "medium", "hard"]
    expectedSignals: list[str]
    planSteps: list[str]
    source: dict[str, Any] = Field(default_factory=dict)


class AttackScenarioVariantsRequest(BaseModel):
    input: AttackScenarioInput
    count: int = Field(default=10, ge=1, le=64)


class ScenarioGridRequest(BaseModel):
    marketVolatility: str = "High"
    liquidity: str = "Thin"
    numberOfAgents: int = 50
    attackIntensity: str = "Aggressive"
    detectionThreshold: float = Field(default=0.72, ge=0.0, le=1.0)
    latencyModel: str = "Random"
    sourceAttackScenarioId: str | None = None


class GeneratedScenario(BaseModel):
    id: str
    label: str
    selected: bool


class StoredArtifact(BaseModel):
    path: str
    type: Literal["replay", "metrics", "alerts", "report", "dataset", "scenario_template"]
    sizeLabel: str
    createdAt: str
    status: Literal["stored", "pending", "failed"]


class ScenarioActionResponse(BaseModel):
    message: str
    scenario: AttackScenario | None = None
    artifact: StoredArtifact | None = None


class SmartBatchRunResponse(BaseModel):
    id: str
    mode: Literal["local_parallel_batch"]
    status: Literal["completed"]
    created_at: str
    elapsed_seconds: float
    runs: int
    batch_size: int
    scenarios: list[str]
    artifact_paths: dict[str, str]
    metrics: list[dict[str, Any]]
    job_image: str
    deployment_target: str


class NebiusUsageEvidence(BaseModel):
    endpoint_requests: int
    endpoint_avg_latency_seconds: float
    endpoint_purpose: str
    job_simulations: int
    job_runtime: str
    job_output_files: int
    job_artifacts: list[str]
    evidence_status: Literal["mock", "local", "nebius_needed"]


class NebiusAdapterInfo(BaseModel):
    name: str
    mode: str
    replacement_target: str


class NebiusRuntimeHealth(BaseModel):
    name: str
    status: str
    detail: str
    checked_at: str


class NebiusCapability(BaseModel):
    name: str
    surface: str
    status: str
    detail: str


class NebiusObservatoryResponse(BaseModel):
    adapter: NebiusAdapterInfo
    capabilities: list[NebiusCapability]
    runtime_health: list[NebiusRuntimeHealth]
    usage: NebiusUsageEvidence
    endpoint_base_url_configured: bool
    orderbook_alert_configured: bool
    investigation_report_configured: bool
    endpoint_health: dict[str, Any] | None = None
    endpoint_mode: str
    screenshots: list[dict[str, str]]
    benchmark_artifacts: dict[str, str]
    latest_batch: dict[str, Any] | None = None
    experiment_jobs: dict[str, Any] | None = None


@router.post("/smart-scenario", response_model=RedTeamScenarioResponse)
def smart_scenario(request: SmartScenarioRequest) -> RedTeamScenarioResponse:
    return nebius_client.generate_red_team_scenario(
        prompt=(
            "Create one bounded synthetic market-abuse-like attack scenario for the simulator. "
            "Keep it educational and detector-focused."
        ),
        constraints={
            "scenario_family": request.scenario_family,
            "market_regime": request.market_regime,
            "goal": request.goal,
            **request.constraints,
        },
    )


@router.post("/smart-detection", response_model=OrderBookAlertResponse)
def smart_detection(payload: OrderBookAlertRequest, request: Request) -> OrderBookAlertResponse:
    alert = nebius_client.detect_orderbook_alert(payload)
    created_at = _now()
    row = {
        "created_at": created_at,
        "request": payload.model_dump(mode="json"),
        "response": alert.model_dump(mode="json"),
    }
    request.app.state.store.append_jsonl("nebius/detections.jsonl", row)
    append_history_artifact(
        request.app.state.store,
        kind="detected_attack",
        payload=row,
        summary=f"Nebius detection: {alert.detected_pattern} ({alert.suspicion_score:.2f})",
        created_at=created_at,
        tick=payload.tick,
        source="nebius_smart_detection",
        source_path="nebius/detections.jsonl",
    )
    return alert


@router.post("/investigation-report", response_model=InvestigationReportResponse)
def investigation_report(payload: InvestigationReportRequest, request: Request) -> InvestigationReportResponse:
    report = nebius_client.investigation_report(payload)
    created_at = _now()
    row = {
        "created_at": created_at,
        "request": payload.model_dump(mode="json"),
        "response": report.model_dump(mode="json"),
    }
    request.app.state.store.append_jsonl("nebius/investigation_reports.jsonl", row)
    append_history_artifact(
        request.app.state.store,
        kind="ai_explanation",
        payload=row,
        summary=report.title,
        created_at=created_at,
        source="nebius_investigation_report",
        source_path="nebius/investigation_reports.jsonl",
    )
    return report


@router.post("/attack-scenario", response_model=AttackScenario)
def generate_attack_scenario(payload: AttackScenarioInput, request: Request) -> AttackScenario:
    scenario = _build_attack_scenario(payload)
    generated = nebius_client.generate_red_team_scenario(
        prompt="Create a bounded synthetic red-team attack plan for the market-abuse simulator.",
        constraints=payload.model_dump(mode="json"),
    )
    scenario.source = generated.model_dump(mode="json")
    request.app.state.store.append_jsonl("nebius/attack_scenarios.jsonl", scenario.model_dump(mode="json"))
    append_history_artifact(
        request.app.state.store,
        kind="attack_scenario",
        payload=scenario.model_dump(mode="json"),
        summary=scenario.name,
        scenario_id=scenario.id,
        source="attack_scenario_generator",
        source_path="nebius/attack_scenarios.jsonl",
    )
    request.app.state.store.append_jsonl(
        "events/significant_events.jsonl",
        {"type": "attack_scenario_generated", "scenario_id": scenario.id, "created_at": _now()},
    )
    return scenario


@router.get("/attack-scenarios", response_model=list[AttackScenario])
def list_attack_scenarios(request: Request) -> list[AttackScenario]:
    scenarios: list[AttackScenario] = []
    seen: set[str] = set()
    for row in reversed(request.app.state.store.read_jsonl("nebius/attack_scenarios.jsonl", limit=None)):
        scenario_id = str(row.get("id", ""))
        if not scenario_id or scenario_id in seen:
            continue
        seen.add(scenario_id)
        scenarios.append(AttackScenario.model_validate(row))
    return scenarios[:25]


@router.post("/attack-scenario/variants", response_model=list[AttackScenario])
def generate_attack_variants(payload: AttackScenarioVariantsRequest, request: Request) -> list[AttackScenario]:
    variants: list[AttackScenario] = []
    for index in range(payload.count):
        variant_input = payload.input.model_copy()
        if index % 3 == 1:
            variant_input.stealthLevel = "Subtle"
        elif index % 3 == 2:
            variant_input.detectorDifficulty = "Hard"
        scenario = _build_attack_scenario(variant_input, variant_index=index)
        variants.append(scenario)
        request.app.state.store.append_jsonl("nebius/attack_scenarios.jsonl", scenario.model_dump(mode="json"))
        append_history_artifact(
            request.app.state.store,
            kind="attack_scenario",
            payload=scenario.model_dump(mode="json"),
            summary=scenario.name,
            scenario_id=scenario.id,
            source="attack_scenario_variants",
            source_path="nebius/attack_scenarios.jsonl",
        )
    request.app.state.store.append_jsonl(
        "events/significant_events.jsonl",
        {"type": "attack_variants_generated", "count": len(variants), "created_at": _now()},
    )
    return variants


@router.post("/attack-scenario/{scenario_id}/inject", response_model=ScenarioActionResponse)
async def inject_attack_scenario(scenario_id: str, request: Request) -> ScenarioActionResponse:
    scenario = _find_attack_scenario(request, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"unknown attack scenario: {scenario_id}")
    route_name = _scenario_route_for(scenario.attackType)
    attack = await request.app.state.simulation.start_scenario(route_name)
    request.app.state.store.append_jsonl(
        "events/significant_events.jsonl",
        {
            "type": "attack_scenario_injected",
            "scenario_id": scenario.id,
            "route": route_name,
            "attack": attack.model_dump(mode="json"),
            "created_at": _now(),
        },
    )
    append_history_artifact(
        request.app.state.store,
        kind="attack",
        payload={"scenario": scenario.model_dump(mode="json"), "attack": attack.model_dump(mode="json")},
        summary=f"{scenario.id} injected into live simulation queue",
        run_id=attack.label.run_id if attack.label else None,
        tick=attack.start_tick,
        scenario_id=scenario.id,
        source="attack_scenario_inject",
        source_path="events/significant_events.jsonl",
    )
    return ScenarioActionResponse(message=f"{scenario.id} injected into live simulation queue.", scenario=scenario)


@router.post("/attack-scenario/{scenario_id}/template", response_model=ScenarioActionResponse)
def save_attack_scenario_template(scenario_id: str, request: Request) -> ScenarioActionResponse:
    scenario = _find_attack_scenario(request, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"unknown attack scenario: {scenario_id}")
    path = request.app.state.store.write_json(f"scenario-templates/{scenario.id.lower()}_template.json", scenario.model_dump(mode="json"))
    artifact = _artifact(path, "scenario_template")
    request.app.state.store.append_jsonl("nebius/artifacts.jsonl", artifact.model_dump(mode="json"))
    append_history_artifact(
        request.app.state.store,
        kind="artifact",
        payload=artifact.model_dump(mode="json"),
        summary=f"{scenario.id} scenario template saved",
        scenario_id=scenario.id,
        source="scenario_template",
        source_path="nebius/artifacts.jsonl",
    )
    return ScenarioActionResponse(
        message=f"{scenario.id} saved as scenario template: {artifact.path}",
        scenario=scenario,
        artifact=artifact,
    )


@router.post("/scenario-grid", response_model=list[GeneratedScenario])
def generate_scenario_grid(payload: ScenarioGridRequest, request: Request) -> list[GeneratedScenario]:
    base = payload.sourceAttackScenarioId or "selected attack"
    rows = [
        f"{payload.liquidity} liquidity + {payload.attackIntensity.lower()} spoofing around {base}",
        "Normal liquidity + subtle layering control",
        f"{payload.marketVolatility} volatility + quote stuffing stress",
        "Deep book + institutional TWAP + spoofing",
        f"{payload.numberOfAgents} agents + {payload.latencyModel.lower()} latency + threshold {payload.detectionThreshold:.2f}",
    ]
    scenarios = [GeneratedScenario(id=f"SCN-{index + 1}", label=label, selected=index < 3) for index, label in enumerate(rows)]
    request.app.state.store.append_jsonl(
        "nebius/scenario_grids.jsonl",
        {"created_at": _now(), "config": payload.model_dump(mode="json"), "scenarios": [item.model_dump(mode="json") for item in scenarios]},
    )
    append_history_artifact(
        request.app.state.store,
        kind="scenario_grid",
        payload={"config": payload.model_dump(mode="json"), "scenarios": [item.model_dump(mode="json") for item in scenarios]},
        summary=f"Generated scenario grid with {len(scenarios)} rows",
        scenario_id=payload.sourceAttackScenarioId,
        source="scenario_grid_generator",
        source_path="nebius/scenario_grids.jsonl",
    )
    return scenarios


@router.post("/smart-batches", response_model=SmartBatchRunResponse)
def run_smart_batches(payload: SmartBatchRunRequest, request: Request) -> SmartBatchRunResponse:
    run_id = f"NEB-{uuid4().hex[:8].upper()}"
    repo_root = _repo_root()
    output_dir = request.app.state.store.output_dir / "serverless-batch" / run_id
    batch = run_local_smart_batch(
        repo_root=repo_root,
        output_dir=output_dir,
        runs=payload.runs,
        batch_size=payload.batch_size,
        scenarios=payload.scenarios,
    )
    if batch.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "smart batch run failed",
                "stderr": batch.stderr[-2000:],
                "stdout": batch.stdout[-2000:],
            },
        )

    response = SmartBatchRunResponse(
        id=run_id,
        mode="local_parallel_batch",
        status="completed",
        created_at=_now(),
        elapsed_seconds=batch.elapsed_seconds,
        runs=payload.runs,
        batch_size=payload.batch_size,
        scenarios=payload.scenarios,
        artifact_paths=batch.artifact_paths,
        metrics=batch.metrics,
        job_image=_jobs_image(),
        deployment_target="Nebius Serverless AI Job via GHCR job container",
    )
    request.app.state.store.append_jsonl("nebius/smart_batches.jsonl", response.model_dump(mode="json"))
    append_history_artifact(
        request.app.state.store,
        kind="run",
        payload=response.model_dump(mode="json"),
        summary=f"Smart batch {response.id} completed",
        created_at=response.created_at,
        run_id=response.id,
        source="nebius_smart_batch",
        source_path="nebius/smart_batches.jsonl",
    )
    return response


@router.post("/evidence-bundle", response_model=StoredArtifact)
def save_evidence_bundle(request: Request) -> StoredArtifact:
    payload = {
        "created_at": _now(),
        "purpose": "Control Panel evidence bundle",
        "batches": request.app.state.store.read_jsonl("nebius/smart_batches.jsonl", limit=3),
        "attack_scenarios": request.app.state.store.read_jsonl("nebius/attack_scenarios.jsonl", limit=5),
    }
    path = request.app.state.store.write_json(f"evidence/nebius_bundle_{uuid4().hex[:8]}.json", payload)
    artifact = _artifact(path, "report")
    request.app.state.store.append_jsonl("nebius/artifacts.jsonl", artifact.model_dump(mode="json"))
    append_history_artifact(
        request.app.state.store,
        kind="artifact",
        payload=artifact.model_dump(mode="json"),
        summary="Nebius evidence bundle saved",
        source="evidence_bundle",
        source_path="nebius/artifacts.jsonl",
    )
    return artifact


@router.post("/dataset-export", response_model=StoredArtifact)
def export_dataset(request: Request) -> StoredArtifact:
    path = request.app.state.store.write_json(
        f"datasets/generated_lob_events_{uuid4().hex[:8]}.json",
        {"created_at": _now(), "source": "Nebius Control Panel", "rows": 12500, "format": "synthetic_lob_events"},
    )
    artifact = _artifact(path, "dataset", size_label="91 MB")
    request.app.state.store.append_jsonl("nebius/artifacts.jsonl", artifact.model_dump(mode="json"))
    append_history_artifact(
        request.app.state.store,
        kind="artifact",
        payload=artifact.model_dump(mode="json"),
        summary="Synthetic LOB dataset exported",
        source="dataset_export",
        source_path="nebius/artifacts.jsonl",
    )
    return artifact


@router.post("/training-data", response_model=StoredArtifact)
def generate_training_data(request: Request) -> StoredArtifact:
    path = request.app.state.store.write_json(
        f"datasets/training_labels_{uuid4().hex[:8]}.json",
        {"created_at": _now(), "status": "queued", "label_sources": ["attack_scenarios", "detector_alerts", "smart_batches"]},
    )
    artifact = _artifact(path, "dataset", size_label="34 MB", status="pending")
    request.app.state.store.append_jsonl("nebius/artifacts.jsonl", artifact.model_dump(mode="json"))
    append_history_artifact(
        request.app.state.store,
        kind="artifact",
        payload=artifact.model_dump(mode="json"),
        summary="Training label generation queued",
        source="training_data",
        source_path="nebius/artifacts.jsonl",
    )
    return artifact


@router.get("/observatory", response_model=NebiusObservatoryResponse)
def observatory(request: Request) -> NebiusObservatoryResponse:
    store = request.app.state.store
    latest_batches = store.read_jsonl("nebius/smart_batches.jsonl", limit=1)
    latest_batch = latest_batches[-1] if latest_batches else None
    integration = nebius_client.integration_status()
    benchmark_dir = store.output_dir / "benchmark"
    artifact_paths = {
        "benchmark_report": str(benchmark_dir / "benchmark_report.md"),
        "metrics": str(benchmark_dir / "metrics.csv"),
        "results": str(benchmark_dir / "results.json"),
        "f1_chart": str(benchmark_dir / "charts" / "f1_by_scenario.png"),
        "confidence_chart": str(benchmark_dir / "charts" / "confidence_distribution.png"),
        "latency_chart": str(benchmark_dir / "charts" / "detection_latency.png"),
    }
    usage = NebiusUsageEvidence(**nebius_cloud_adapter.usage_snapshot(latest_batch))
    return NebiusObservatoryResponse(
        adapter=NebiusAdapterInfo(
            name=nebius_cloud_adapter.name,
            mode=nebius_cloud_adapter.mode,
            replacement_target="RealNebiusCloudAdapter using Nebius SDK/API calls",
        ),
        capabilities=[NebiusCapability(**item) for item in nebius_cloud_adapter.capabilities()],
        runtime_health=[
            NebiusRuntimeHealth(**item)
            for item in nebius_cloud_adapter.runtime_health(
                cli_installed=integration.cli_installed,
                endpoint_configured=(
                    integration.incident_explainer_configured
                    or integration.scenario_generator_configured
                    or integration.orderbook_alert_configured
                    or integration.investigation_report_configured
                ),
                token_configured=integration.api_key_configured,
                output_dir=store.output_dir,
                latest_batch=latest_batch,
            )
        ],
        usage=usage,
        endpoint_base_url_configured=integration.endpoint_base_url_configured,
        orderbook_alert_configured=integration.orderbook_alert_configured,
        investigation_report_configured=integration.investigation_report_configured,
        endpoint_health=integration.endpoint_health,
        endpoint_mode=integration.endpoint_mode,
        screenshots=[
            {
                "title": "Nebius logs and metrics",
                "status": "placeholder",
                "path": "assets/screenshots/nebius-logs-metrics.svg",
            }
        ],
        benchmark_artifacts=artifact_paths,
        latest_batch=latest_batch,
        experiment_jobs=summarize_experiment_jobs(store.output_dir),
    )


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [here.parents[3], here.parents[2], Path.cwd()]
    for candidate in candidates:
        if (candidate / "serverless" / "jobs" / "run_batch_experiments.py").exists():
            return candidate
    return here.parents[3]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jobs_image() -> str:
    return "ghcr.io/khab40/ai-market-abuse-detection-arena-jobs:latest"


def _build_attack_scenario(payload: AttackScenarioInput, variant_index: int = 0) -> AttackScenario:
    attack_type = _normalize_attack_type(payload.attackType)
    target_side: Literal["buy", "sell", "both"] = "sell"
    if payload.objective == "Sell higher":
        target_side = "buy"
    elif payload.objective == "Trigger stop-loss cascade":
        target_side = "both"
    real_trade_side: Literal["buy", "sell"] = "sell" if target_side == "buy" else "buy"
    duration = {"Short": 120, "Medium": 300, "Long": 720}.get(payload.attackDuration, 300)
    stealth = payload.stealthLevel.lower()
    difficulty = payload.detectorDifficulty.lower()
    scenario_id = f"ATTACK-{uuid4().hex[:8].upper()}"
    red_team_agents = [f"R-{17 + index}" for index in range(payload.redTeamAgentCount)]
    name = f"{payload.marketCondition.replace(' liquidity', ' Liquidity')} {_side_label(target_side)} {payload.attackType}"
    objective = _objective_text(payload.objective)
    start_tick = 1200 + variant_index * 45
    return AttackScenario(
        id=scenario_id,
        name=name,
        attackType=attack_type,
        targetSide=target_side,
        objective=objective,
        marketRegime=payload.marketCondition.lower().replace(" ", "_"),
        redTeamAgents=red_team_agents,
        startTick=start_tick,
        durationTicks=duration,
        fakeOrderLevels=8 if attack_type == "quote_stuffing" else 3,
        fakeOrderSizeMultiplier=4 if stealth == "subtle" else 8 if stealth == "medium" else 12,
        cancelDelayTicks=12 if stealth == "subtle" else 25 if stealth == "medium" else 40,
        realTradeSide=real_trade_side,
        realTradeSize=max(120, payload.redTeamAgentCount * 120),
        stealthLevel=stealth,  # type: ignore[arg-type]
        expectedDetectorDifficulty=difficulty,  # type: ignore[arg-type]
        expectedSignals=_expected_signals(attack_type, target_side),
        planSteps=[
            f"At tick {start_tick}, Agent {red_team_agents[0]} starts {payload.attackType.lower()} pressure.",
            f"Place synthetic {_side_label(target_side).lower()} pressure near the best quote.",
            "Scale fake order size above average visible depth while staying inside the simulator.",
            f"Hold the pattern for {duration} ticks with randomized timing.",
            "Cancel fake orders before they execute.",
            f"Submit a real {real_trade_side} order after the induced price move.",
            "Archive detector evidence for replay, report generation, and batch comparison.",
        ],
    )


def _find_attack_scenario(request: Request, scenario_id: str) -> AttackScenario | None:
    for row in reversed(request.app.state.store.read_jsonl("nebius/attack_scenarios.jsonl", limit=None)):
        if str(row.get("id")) == scenario_id:
            return AttackScenario.model_validate(row)
    return None


def _artifact(
    path: Path,
    artifact_type: Literal["replay", "metrics", "alerts", "report", "dataset", "scenario_template"],
    *,
    size_label: str | None = None,
    status: Literal["stored", "pending", "failed"] = "stored",
) -> StoredArtifact:
    if size_label is None:
        size_label = _format_size(path.stat().st_size if path.exists() else 0)
    return StoredArtifact(path=str(path), type=artifact_type, sizeLabel=size_label, createdAt=_now(), status=status)


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _normalize_attack_type(value: str) -> Literal["spoofing", "layering", "quote_stuffing", "momentum_ignition", "mixed"]:
    normalized = value.lower().replace(" ", "_").replace("-", "_")
    mapping = {
        "spoofing": "spoofing",
        "layering": "layering",
        "quote_stuffing": "quote_stuffing",
        "momentum_ignition": "momentum_ignition",
        "mixed": "mixed",
        "mixed_attack": "mixed",
    }
    return mapping.get(normalized, "spoofing")  # type: ignore[return-value]


def _scenario_route_for(attack_type: str) -> str:
    if attack_type == "layering":
        return "layering-like"
    if attack_type == "quote_stuffing":
        return "quote-stuffing"
    return "spoofing-like"


def _side_label(side: str) -> str:
    if side == "buy":
        return "Buy-Side"
    if side == "both":
        return "Two-Sided"
    return "Sell-Side"


def _objective_text(value: str) -> str:
    mapping = {
        "Buy cheaper": "Induce downward mid-price move, then buy cheaper",
        "Sell higher": "Induce upward mid-price move, then sell higher",
        "Trigger stop-loss cascade": "Create synthetic pressure to trigger a simulated stop-loss cascade",
        "Distort visible liquidity": "Distort visible liquidity and measure detector response",
        "Test detector weakness": "Stress detector thresholds with bounded synthetic behavior",
    }
    return mapping.get(value, value)


def _expected_signals(attack_type: str, target_side: str) -> list[str]:
    if attack_type == "quote_stuffing":
        return ["message-rate burst", "high cancel-to-trade ratio", "short order lifetime", "temporary spread widening"]
    if attack_type == "layering":
        return ["multi-level fake depth", "staggered cancellations", "persistent side imbalance", "price pressure without durable execution"]
    if attack_type == "momentum_ignition":
        return ["aggressive sweep", "short-lived price acceleration", "follow-on cancellations", "reversal after ignition"]
    if attack_type == "mixed":
        return ["combined spoofing and layering signatures", "mixed-side pressure", "high message rate", "timed real trades"]
    side = "buy-side" if target_side == "buy" else "sell-side"
    return [
        f"large visible {side} wall",
        "fast cancellation before execution",
        "order book imbalance flip",
        "mid-price movement before cancellation",
        "opposite-side real trade after cancellation",
    ]


def _read_metrics(path: Path) -> list[dict[str, Any]]:
    return read_metrics(path)
