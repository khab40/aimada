import csv
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
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
    mode: Literal["local_serverless_job"]
    status: Literal["queued", "running", "generating_report", "completed"]
    created_at: str
    command: list[str]
    results: list[BenchmarkResult]
    artifact_paths: dict[str, str]


class ReportsSummary(BaseModel):
    experiments: list[dict[str, Any]]
    benchmark_runs: list[dict[str, Any]]
    incidents: list[dict[str, Any]]
    explanations: list[dict[str, Any]]
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
    if not normalized_scenarios:
        raise HTTPException(status_code=400, detail="select at least one scenario")

    runs = max(1, min(payload.runs, 1000))
    detectors = _detector_set(payload.detectors)
    repo_root = _repo_root()
    output_dir = _store(request).output_dir / "benchmark" / run_id
    command = [
        sys.executable,
        str(repo_root / "serverless" / "jobs" / "detector_tournament.py"),
        "--runs",
        str(runs),
        "--scenarios",
        ",".join(normalized_scenarios),
        "--detectors",
        ",".join(detectors),
        "--output",
        str(output_dir),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
        cwd=repo_root,
        text=True,
        timeout=60,
    )
    if completed.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "serverless detector tournament failed",
                "stderr": completed.stderr[-2000:],
                "stdout": completed.stdout[-2000:],
            },
        )

    results = _read_benchmark_results(output_dir / "metrics.csv")
    response = BenchmarkRunResponse(
        id=run_id,
        mode="local_serverless_job",
        status="completed",
        created_at=_now(),
        command=command,
        results=results,
        artifact_paths={
            "benchmark_report": str(output_dir / "benchmark_report.md"),
            "metrics": str(output_dir / "metrics.csv"),
            "results": str(output_dir / "results.json"),
        },
    )
    _store(request).append_jsonl("experiments/benchmark_runs.jsonl", response.model_dump(mode="json"))
    _store(request).append_jsonl(
        "events/significant_events.jsonl",
        {
            "type": "benchmark_run_completed",
            "run_id": run_id,
            "runs": runs,
            "scenarios": normalized_scenarios,
            "detectors": detectors,
            "mode": response.mode,
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
        explanations=store.read_jsonl("incidents/explanations.jsonl", limit=50),
        attacks=store.read_jsonl("attacks/attacks.jsonl", limit=50),
        significant_events=store.read_jsonl("events/significant_events.jsonl", limit=100),
    )


def _store(request: Request) -> LocalStore:
    return request.app.state.store


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [here.parents[3], here.parents[2], Path.cwd()]
    for candidate in candidates:
        if (candidate / "serverless" / "jobs" / "detector_tournament.py").exists():
            return candidate
    return here.parents[3]


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


def _detector_set(value: str) -> list[str]:
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    detector_sets = {
        "baseline": ["spoofing_like", "layering_like", "quote_stuffing", "liquidity_shock"],
        "tuned": ["spoofing_like", "layering_like", "quote_stuffing", "liquidity_shock"],
        "hybrid": ["spoofing_like", "layering_like", "quote_stuffing", "liquidity_shock"],
    }
    return detector_sets.get(normalized, detector_sets["tuned"])


def _read_benchmark_results(metrics_path: Path) -> list[BenchmarkResult]:
    expected_detectors = {
        "spoofing-like": "spoofing_like",
        "layering-like": "layering_like",
        "quote-stuffing": "quote_stuffing",
        "liquidity-evaporation": "liquidity_shock",
    }
    rows: list[dict[str, str]] = []
    with metrics_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    selected_rows: list[dict[str, str]] = []
    for row in rows:
        if row.get("detector") == expected_detectors.get(row.get("scenario", "")):
            selected_rows.append(row)
    if not selected_rows:
        selected_rows = rows

    return [
        BenchmarkResult(
            scenario=_display_scenario(row.get("scenario", "unknown")),
            precision=float(row.get("precision") or 0),
            recall=float(row.get("recall") or 0),
            f1=float(row.get("f1") or 0),
            avg_detection_latency_ms=_optional_float(row.get("avg_detection_latency_ms")),
        )
        for row in selected_rows
    ]


def _optional_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _display_scenario(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()
