from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.schemas.arena import AttackTrackerState, BenchmarkResult, MarketRegime
from app.storage.local_store import LocalStore

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


class AttackExperimentRequest(BaseModel):
    scenario_type: str
    wall_size_multiplier: float
    lifetime_seconds: int
    distance_from_mid_bps: int
    cancel_style: Literal["instant", "gradual", "partial"]
    noise_cover: Literal["none", "low", "high"]
    predicted_detection_risk: float = Field(ge=0.0, le=1.0)


class SavedExperiment(BaseModel):
    id: str
    kind: Literal["attack_builder"]
    created_at: str
    config: AttackExperimentRequest


class LabLaunchResponse(BaseModel):
    experiment_id: str
    launch_endpoint: str
    attack: AttackTrackerState


class BenchmarkRunRequest(BaseModel):
    runs: int
    market_regime: str
    scenarios: list[str]
    detectors: str


class BenchmarkRunResponse(BaseModel):
    id: str
    mode: Literal["mock_nebius_serverless_job"]
    status: Literal["queued", "running", "generating_report", "completed"]
    created_at: str
    command: list[str]
    results: list[BenchmarkResult]
    artifact_paths: dict[str, str]


class ReportsSummary(BaseModel):
    experiments: list[dict[str, Any]]
    benchmark_runs: list[dict[str, Any]]
    incidents: list[dict[str, Any]]
    attacks: list[dict[str, Any]]
    significant_events: list[dict[str, Any]]


@router.post("/attacks", response_model=SavedExperiment)
def save_attack_experiment(payload: AttackExperimentRequest, request: Request) -> SavedExperiment:
    experiment = SavedExperiment(
        id=f"EXP-{uuid4().hex[:8].upper()}",
        kind="attack_builder",
        created_at=_now(),
        config=payload,
    )
    _store(request).append_jsonl("experiments/attack_experiments.jsonl", experiment.model_dump(mode="json"))
    _store(request).append_jsonl(
        "events/significant_events.jsonl",
        {
            "type": "experiment_saved",
            "experiment_id": experiment.id,
            "scenario_type": payload.scenario_type,
            "created_at": experiment.created_at,
        },
    )
    return experiment


@router.post("/attacks/launch", response_model=LabLaunchResponse)
async def launch_attack_experiment(payload: AttackExperimentRequest, request: Request) -> LabLaunchResponse:
    experiment = save_attack_experiment(payload, request)
    scenario_name = _scenario_to_route_name(payload.scenario_type)
    try:
        attack = await request.app.state.simulation.start_scenario(scenario_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    launch_endpoint = _scenario_launch_endpoint(payload.scenario_type)
    _store(request).append_jsonl(
        "experiments/attack_launches.jsonl",
        {
            "experiment_id": experiment.id,
            "created_at": _now(),
            "launch_endpoint": launch_endpoint,
            "attack": attack.model_dump(mode="json"),
        },
    )
    return LabLaunchResponse(
        experiment_id=experiment.id,
        launch_endpoint=launch_endpoint,
        attack=attack,
    )


@router.post("/benchmark-runs", response_model=BenchmarkRunResponse)
def run_benchmark_experiment(payload: BenchmarkRunRequest, request: Request) -> BenchmarkRunResponse:
    run_id = f"JOB-{uuid4().hex[:8].upper()}"
    normalized_scenarios = [_normalize_scenario(scenario) for scenario in payload.scenarios]
    results = _mock_benchmark_results(normalized_scenarios)
    command = [
        "python",
        "detector_tournament.py",
        "--runs",
        str(payload.runs),
        "--scenarios",
        ",".join(normalized_scenarios),
        "--detectors",
        payload.detectors,
        "--output",
        f"/job/outputs/benchmark/{run_id}",
    ]
    response = BenchmarkRunResponse(
        id=run_id,
        mode="mock_nebius_serverless_job",
        status="completed",
        created_at=_now(),
        command=command,
        results=results,
        artifact_paths={
            "benchmark_report": f"outputs/benchmark/{run_id}/benchmark_report.md",
            "metrics": f"outputs/benchmark/{run_id}/metrics.csv",
            "results": f"outputs/benchmark/{run_id}/results.json",
        },
    )
    _store(request).append_jsonl("experiments/benchmark_runs.jsonl", response.model_dump(mode="json"))
    _store(request).append_jsonl(
        "events/significant_events.jsonl",
        {
            "type": "benchmark_run_completed",
            "run_id": run_id,
            "runs": payload.runs,
            "scenarios": normalized_scenarios,
            "created_at": response.created_at,
        },
    )
    return response


@router.get("/reports", response_model=ReportsSummary)
def reports_summary(request: Request) -> ReportsSummary:
    store = _store(request)
    return ReportsSummary(
        experiments=store.read_jsonl("experiments/attack_experiments.jsonl", limit=25),
        benchmark_runs=store.read_jsonl("experiments/benchmark_runs.jsonl", limit=25),
        incidents=store.read_jsonl("incidents/incidents.jsonl", limit=50),
        attacks=store.read_jsonl("attacks/attacks.jsonl", limit=50),
        significant_events=store.read_jsonl("events/significant_events.jsonl", limit=100),
    )


def _store(request: Request) -> LocalStore:
    return request.app.state.store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scenario_to_route_name(value: str) -> str:
    normalized = _normalize_scenario(value)
    mapping = {
        "spoofing": "spoofing-like",
        "layering": "layering-like",
        "quote_stuffing": "quote-stuffing",
        "liquidity_evaporation": "liquidity-evaporation",
    }
    return mapping.get(normalized, "spoofing-like")


def _scenario_launch_endpoint(value: str) -> str:
    return f"/api/scenarios/{_scenario_to_route_name(value)}"


def _normalize_scenario(value: str) -> str:
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "spoofing_like": "spoofing",
        "spoofing_like_wall": "spoofing",
        "layering_like": "layering",
        "quote_stuffing_like": "quote_stuffing",
        "liquidity_shock": "liquidity_evaporation",
    }
    return mapping.get(normalized, normalized)


def _mock_benchmark_results(scenarios: list[str]) -> list[BenchmarkResult]:
    defaults = {
        "spoofing": BenchmarkResult(scenario="Spoofing", precision=0.91, recall=0.86, f1=0.88, avg_detection_latency_ms=840),
        "layering": BenchmarkResult(scenario="Layering", precision=0.84, recall=0.79, f1=0.81, avg_detection_latency_ms=980),
        "quote_stuffing": BenchmarkResult(scenario="Quote stuffing", precision=0.96, recall=0.92, f1=0.94, avg_detection_latency_ms=410),
        "liquidity_evaporation": BenchmarkResult(scenario="Liquidity evaporation", precision=0.89, recall=0.83, f1=0.86, avg_detection_latency_ms=760),
    }
    return [defaults[scenario] for scenario in scenarios if scenario in defaults]
