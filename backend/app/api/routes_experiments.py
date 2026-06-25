import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from app.experiments.aggregator import AggregationResult, ExperimentSummary, LeaderboardRow
from app.experiments.artifact_normalizer import ArtifactNormalizationResponse
from app.experiments.attack_manifest import AttackManifestResponse
from app.experiments.investigation_pipeline import InvestigationRecord, InvestigationRunResponse
from app.experiments.manager import ExperimentManager
from app.experiments.models import (
    Experiment,
    ExperimentCreateRequest,
    ExperimentDeleteResponse,
    ExperimentLocalBatchRunResponse,
)
from app.experiments.nebius_orchestrator import (
    ExperimentJobRecord,
    NebiusArtifactCollectionResponse,
    NebiusExperimentOrchestrator,
)
from app.experiments.repository import ExperimentRepository
from app.nebius.client import NebiusClient
from app.schemas.arena import AttackTrackerState, BenchmarkResult, MarketRegime
from app.storage.history import append_history_artifact, history_window
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
    nebius_batches: list[dict[str, Any]]
    nebius_artifacts: list[dict[str, Any]]
    incidents: list[dict[str, Any]]
    explanations: list[dict[str, Any]]
    attacks: list[dict[str, Any]]
    significant_events: list[dict[str, Any]]
    evidence_screenshots: list[dict[str, Any]]
    promoted_runs: list[dict[str, Any]]
    nebius_detections: list[dict[str, Any]]
    nebius_investigation_reports: list[dict[str, Any]]
    history_artifacts: list[dict[str, Any]]
    history_ticks: list[dict[str, Any]]


class HistoryReplayResponse(BaseModel):
    window_hours: float
    generated_at: str
    filters: dict[str, Any]
    tick_count: int
    artifact_count: int
    ticks: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]


class ArtifactReadResponse(BaseModel):
    path: str
    name: str
    content_type: str
    content: str


class ArtifactExportRequest(BaseModel):
    path: str
    format: Literal["markdown", "pdf"]


class ArtifactExportResponse(BaseModel):
    path: str
    download_url: str
    format: Literal["markdown", "pdf"]


class BenchmarkCompareRequest(BaseModel):
    run_ids: list[str]


class BenchmarkCompareResponse(BaseModel):
    run_ids: list[str]
    rows: list[dict[str, Any]]


class IncidentReplayResponse(BaseModel):
    incident_id: str
    incident: dict[str, Any] | None
    events: list[dict[str, Any]]
    labels: list[dict[str, Any]]
    ticks: list[dict[str, Any]]


class ScreenshotAttachmentRequest(BaseModel):
    title: str = "Nebius logs and metrics"
    path: str = "assets/screenshots/nebius-logs-metrics.svg"


class ScreenshotAttachmentResponse(BaseModel):
    id: str
    title: str
    path: str
    created_at: str


class PromoteEvidenceResponse(BaseModel):
    run_id: str
    path: str
    download_url: str


class ClearReportsRequest(BaseModel):
    confirmation: str


class ClearReportsResponse(BaseModel):
    deleted_files: list[str]
    deleted_dirs: list[str]
    message: str


@router.post("", response_model=Experiment)
def create_experiment(payload: ExperimentCreateRequest, request: Request) -> Experiment:
    return _experiment_manager(request).create(payload)


@router.post("/", response_model=Experiment, include_in_schema=False)
def create_experiment_trailing(payload: ExperimentCreateRequest, request: Request) -> Experiment:
    return create_experiment(payload, request)


@router.get("", response_model=list[Experiment])
def list_experiments(request: Request) -> list[Experiment]:
    return _experiment_manager(request).list()


@router.get("/", response_model=list[Experiment], include_in_schema=False)
def list_experiments_trailing(request: Request) -> list[Experiment]:
    return list_experiments(request)


@router.post("/attacks", response_model=SavedExperiment)
def save_attack_experiment(payload: AttackExperimentRequest, request: Request) -> SavedExperiment:
    experiment = SavedExperiment(
        id=f"EXP-{uuid4().hex[:8].upper()}",
        kind="attack_builder",
        created_at=_now(),
        config=payload,
    )
    _store(request).append_jsonl("experiments/attack_experiments.jsonl", experiment.model_dump(mode="json"))
    append_history_artifact(
        _store(request),
        kind="run",
        payload=experiment.model_dump(mode="json"),
        summary=f"Attack experiment {experiment.id} saved",
        created_at=experiment.created_at,
        run_id=experiment.id,
        source="attack_builder",
        source_path="experiments/attack_experiments.jsonl",
    )
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
    append_history_artifact(
        _store(request),
        kind="run",
        payload={
            "experiment_id": experiment.id,
            "launch_endpoint": launch_endpoint,
            "attack": attack.model_dump(mode="json"),
        },
        summary=f"Attack experiment {experiment.id} launched",
        run_id=experiment.id,
        tick=attack.start_tick,
        scenario_id=attack.scenario_id,
        source="attack_builder_launch",
        source_path="experiments/attack_launches.jsonl",
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
    append_history_artifact(
        _store(request),
        kind="run",
        payload=response.model_dump(mode="json"),
        summary=f"Benchmark run {response.id} completed",
        created_at=response.created_at,
        run_id=response.id,
        source="benchmark_runner",
        source_path="experiments/benchmark_runs.jsonl",
    )
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


@router.post("/{experiment_id}/generate-manifest", response_model=AttackManifestResponse)
def generate_experiment_attack_manifest(experiment_id: str, request: Request) -> AttackManifestResponse:
    try:
        response = _experiment_manager(request).generate_attack_manifest(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    return response


@router.post("/{experiment_id}/run-local-batch", response_model=ExperimentLocalBatchRunResponse)
def run_experiment_local_batch(experiment_id: str, request: Request) -> ExperimentLocalBatchRunResponse:
    try:
        response = _experiment_manager(request).run_local_batch(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    if response.status == "failed":
        raise HTTPException(status_code=502, detail=response.model_dump(mode="json"))
    return response


@router.post("/{experiment_id}/normalize-artifacts", response_model=ArtifactNormalizationResponse)
def normalize_experiment_artifacts(experiment_id: str, request: Request) -> ArtifactNormalizationResponse:
    try:
        response = _experiment_manager(request).normalize_artifacts(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    return response


@router.post("/{experiment_id}/run-investigations", response_model=InvestigationRunResponse)
def run_experiment_investigations(
    experiment_id: str,
    request: Request,
    top_k: int = 7,
) -> InvestigationRunResponse:
    try:
        response = _experiment_manager(request).run_investigations(
            experiment_id,
            client=NebiusClient(),
            top_k=top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    return response


@router.get("/{experiment_id}/investigations", response_model=list[InvestigationRecord])
def list_experiment_investigations(experiment_id: str, request: Request) -> list[InvestigationRecord]:
    try:
        response = _experiment_manager(request).list_investigations(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    return response


@router.post("/{experiment_id}/aggregate", response_model=AggregationResult)
def aggregate_experiment_outputs(experiment_id: str, request: Request) -> AggregationResult:
    try:
        response = _experiment_manager(request).aggregate(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    return response


@router.get("/{experiment_id}/summary", response_model=ExperimentSummary)
def get_experiment_summary(experiment_id: str, request: Request) -> ExperimentSummary:
    try:
        response = _experiment_manager(request).summary(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail=f"experiment summary not found: {experiment_id}")
    return response


@router.get("/{experiment_id}/leaderboard", response_model=list[LeaderboardRow])
def get_experiment_leaderboard(experiment_id: str, request: Request) -> list[LeaderboardRow]:
    try:
        response = _experiment_manager(request).leaderboard(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail=f"experiment leaderboard not found: {experiment_id}")
    return response


@router.get("/{experiment_id}/report", response_class=PlainTextResponse)
def get_experiment_report(experiment_id: str, request: Request) -> PlainTextResponse:
    try:
        path = _experiment_manager(request).report_path(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if path is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"experiment report not found: {experiment_id}")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")


@router.post("/{experiment_id}/submit-nebius", response_model=ExperimentJobRecord)
def submit_experiment_nebius(experiment_id: str, request: Request) -> ExperimentJobRecord:
    try:
        job = _nebius_orchestrator(request).submit(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    return job


@router.get("/{experiment_id}/jobs", response_model=list[ExperimentJobRecord])
def list_experiment_jobs(experiment_id: str, request: Request) -> list[ExperimentJobRecord]:
    try:
        jobs = _nebius_orchestrator(request).list_jobs(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if jobs is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    return jobs


@router.post("/{experiment_id}/refresh-jobs", response_model=list[ExperimentJobRecord])
def refresh_experiment_jobs(experiment_id: str, request: Request) -> list[ExperimentJobRecord]:
    try:
        jobs = _nebius_orchestrator(request).refresh(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if jobs is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    return jobs


@router.post("/{experiment_id}/collect-nebius-artifacts", response_model=NebiusArtifactCollectionResponse)
def collect_experiment_nebius_artifacts(
    experiment_id: str,
    request: Request,
) -> NebiusArtifactCollectionResponse:
    try:
        response = _nebius_orchestrator(request).collect_artifacts(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    return response


@router.get("/reports", response_model=ReportsSummary)
def reports_summary(request: Request) -> ReportsSummary:
    store = _store(request)
    return ReportsSummary(
        experiments=[
            *[experiment.model_dump(mode="json") for experiment in _experiment_manager(request).list()],
            *store.read_jsonl("experiments/attack_experiments.jsonl", limit=25),
        ],
        benchmark_runs=store.read_jsonl("experiments/benchmark_runs.jsonl", limit=25),
        nebius_batches=store.read_jsonl("nebius/smart_batches.jsonl", limit=25),
        nebius_artifacts=store.read_jsonl("nebius/artifacts.jsonl", limit=50),
        incidents=store.read_jsonl("incidents/incidents.jsonl", limit=50),
        explanations=store.read_jsonl("incidents/explanations.jsonl", limit=50),
        attacks=store.read_jsonl("attacks/attacks.jsonl", limit=50),
        significant_events=store.read_jsonl("events/significant_events.jsonl", limit=100),
        evidence_screenshots=store.read_jsonl("evidence/screenshots.jsonl", limit=25),
        promoted_runs=store.read_jsonl("evidence/promoted_runs.jsonl", limit=25),
        nebius_detections=store.read_jsonl("nebius/detections.jsonl", limit=50),
        nebius_investigation_reports=store.read_jsonl("nebius/investigation_reports.jsonl", limit=50),
        history_artifacts=store.read_jsonl("history/artifacts.jsonl", limit=200),
        history_ticks=store.read_jsonl("history/ticks.jsonl", limit=120),
    )


@router.get("/history/replay", response_model=HistoryReplayResponse)
def replay_history_window(
    request: Request,
    window_hours: float = 1.0,
    limit: int = 5000,
    scenario_id: str | None = None,
    incident_id: str | None = None,
) -> HistoryReplayResponse:
    replay = history_window(
        _store(request),
        window_hours=window_hours,
        limit=max(1, min(limit, 20_000)),
        scenario_id=scenario_id,
        incident_id=incident_id,
    )
    return HistoryReplayResponse(**replay)


@router.post("/reports/clear", response_model=ClearReportsResponse)
def clear_reports(payload: ClearReportsRequest, request: Request) -> ClearReportsResponse:
    if payload.confirmation != "DELETE REPORTS":
        raise HTTPException(status_code=400, detail="confirmation must equal DELETE REPORTS")

    store = _store(request)
    deleted_files: list[str] = []
    deleted_dirs: list[str] = []
    for relative_path in _report_index_files():
        path = store.output_dir / relative_path
        if path.exists() and path.is_file():
            path.unlink()
            deleted_files.append(str(path))

    for relative_dir in _report_artifact_dirs():
        path = store.output_dir / relative_dir
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            deleted_dirs.append(str(path))

    return ClearReportsResponse(
        deleted_dirs=deleted_dirs,
        deleted_files=deleted_files,
        message=f"Cleared {len(deleted_files)} report indexes and {len(deleted_dirs)} artifact directories.",
    )


@router.get("/artifacts/read", response_model=ArtifactReadResponse)
def read_artifact(path: str, request: Request) -> ArtifactReadResponse:
    artifact_path = _resolve_readable_artifact(request, path)
    content = artifact_path.read_text(encoding="utf-8", errors="replace")
    return ArtifactReadResponse(
        path=str(artifact_path),
        name=artifact_path.name,
        content_type=_content_type(artifact_path),
        content=content[:200_000],
    )


@router.get("/artifacts/download")
def download_artifact(path: str, request: Request) -> FileResponse:
    artifact_path = _resolve_readable_artifact(request, path)
    return FileResponse(
        artifact_path,
        media_type=_content_type(artifact_path),
        filename=artifact_path.name,
    )


@router.post("/artifacts/export", response_model=ArtifactExportResponse)
def export_artifact(payload: ArtifactExportRequest, request: Request) -> ArtifactExportResponse:
    source = _resolve_readable_artifact(request, payload.path)
    exports_dir = _store(request).output_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{source.stem}-{uuid4().hex[:8]}"
    if payload.format == "markdown":
        target = exports_dir / f"{stem}.md"
        target.write_text(_artifact_to_markdown(source), encoding="utf-8")
    else:
        target = exports_dir / f"{stem}.pdf"
        _write_simple_pdf(target, _artifact_to_markdown(source))
    return ArtifactExportResponse(
        path=str(target),
        download_url=f"/api/experiments/artifacts/download?path={target}",
        format=payload.format,
    )


@router.post("/benchmark-runs/compare", response_model=BenchmarkCompareResponse)
def compare_benchmark_runs(payload: BenchmarkCompareRequest, request: Request) -> BenchmarkCompareResponse:
    runs = _store(request).read_jsonl("experiments/benchmark_runs.jsonl", limit=None)
    selected = [run for run in runs if str(run.get("id")) in set(payload.run_ids)]
    rows: list[dict[str, Any]] = []
    for run in selected:
        for result in run.get("results", []):
            if isinstance(result, dict):
                rows.append(
                    {
                        "run_id": run.get("id"),
                        "scenario": result.get("scenario"),
                        "precision": result.get("precision"),
                        "recall": result.get("recall"),
                        "f1": result.get("f1"),
                        "avg_detection_latency_ms": result.get("avg_detection_latency_ms"),
                    }
                )
    return BenchmarkCompareResponse(run_ids=[str(run.get("id")) for run in selected], rows=rows)


@router.get("/incidents/{incident_id}/replay", response_model=IncidentReplayResponse)
def replay_incident_window(incident_id: str, request: Request) -> IncidentReplayResponse:
    store = _store(request)
    incidents = store.read_jsonl("incidents/incidents.jsonl", limit=None)
    incident = next((row for row in incidents if str(row.get("id")) == incident_id), None)
    scenario_id = str(incident.get("scenario_id")) if incident else ""
    events = [
        row
        for row in store.read_jsonl("events/events.jsonl", limit=None)
        if str(row.get("incident_id")) == incident_id or (scenario_id and str(row.get("scenario_id")) == scenario_id)
    ][-80:]
    labels = [
        row
        for row in store.read_jsonl("labels/scenario_labels.jsonl", limit=None)
        if scenario_id and str(row.get("scenario_id")) == scenario_id
    ]
    ticks = [
        row
        for row in store.read_jsonl("history/ticks.jsonl", limit=None)
        if str(row.get("incident_id")) == incident_id or (scenario_id and str(row.get("scenario_id")) == scenario_id)
    ][-240:]
    return IncidentReplayResponse(incident_id=incident_id, incident=incident, events=events, labels=labels, ticks=ticks)


@router.post("/evidence/screenshots", response_model=ScreenshotAttachmentResponse)
def attach_screenshot(payload: ScreenshotAttachmentRequest, request: Request) -> ScreenshotAttachmentResponse:
    screenshot = ScreenshotAttachmentResponse(
        id=f"SHOT-{uuid4().hex[:8].upper()}",
        title=payload.title,
        path=payload.path,
        created_at=_now(),
    )
    _store(request).append_jsonl("evidence/screenshots.jsonl", screenshot.model_dump(mode="json"))
    append_history_artifact(
        _store(request),
        kind="artifact",
        payload=screenshot.model_dump(mode="json"),
        summary=f"Screenshot evidence attached: {screenshot.title}",
        created_at=screenshot.created_at,
        source="evidence_screenshot",
        source_path="evidence/screenshots.jsonl",
    )
    return screenshot


@router.post("/benchmark-runs/{run_id}/promote", response_model=PromoteEvidenceResponse)
def promote_run_to_evidence(run_id: str, request: Request) -> PromoteEvidenceResponse:
    store = _store(request)
    runs = store.read_jsonl("experiments/benchmark_runs.jsonl", limit=None)
    run = next((row for row in runs if str(row.get("id")) == run_id), None)
    if run is None:
        smart_batches = store.read_jsonl("nebius/smart_batches.jsonl", limit=None)
        run = next((row for row in smart_batches if str(row.get("id")) == run_id), None)
    if run is None:
        raise HTTPException(status_code=404, detail=f"unknown benchmark run: {run_id}")
    target_dir = store.output_dir / "challenge-submission"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{run_id}-evidence.md"
    artifact_paths = run.get("artifact_paths", {}) if isinstance(run.get("artifact_paths"), dict) else {}
    lines = [
        f"# Challenge Submission Evidence: {run_id}",
        "",
        f"- Promoted at: {_now()}",
        f"- Mode: {run.get('mode')}",
        f"- Status: {run.get('status')}",
        "",
        "## Artifacts",
        "",
    ]
    for key, value in artifact_paths.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Results", ""])
    for result in run.get("results", []):
        lines.append(f"- {result}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    store.append_jsonl(
        "evidence/promoted_runs.jsonl",
        {"run_id": run_id, "created_at": _now(), "path": str(target), "source": run},
    )
    append_history_artifact(
        store,
        kind="artifact",
        payload={"run_id": run_id, "path": str(target), "source": run},
        summary=f"Run {run_id} promoted to evidence",
        run_id=run_id,
        source="promote_run_to_evidence",
        source_path="evidence/promoted_runs.jsonl",
    )
    return PromoteEvidenceResponse(
        run_id=run_id,
        path=str(target),
        download_url=f"/api/experiments/artifacts/download?path={target}",
    )


@router.get("/{experiment_id}", response_model=Experiment)
def get_experiment(experiment_id: str, request: Request) -> Experiment:
    try:
        experiment = _experiment_manager(request).get(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    return experiment


@router.delete("/{experiment_id}", response_model=ExperimentDeleteResponse)
def delete_experiment(experiment_id: str, request: Request) -> ExperimentDeleteResponse:
    try:
        deleted = _experiment_manager(request).delete(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"unknown experiment: {experiment_id}")
    return ExperimentDeleteResponse(id=experiment_id.upper(), deleted=True)


def _store(request: Request) -> LocalStore:
    return request.app.state.store


def _experiment_manager(request: Request) -> ExperimentManager:
    return ExperimentManager(ExperimentRepository(_store(request)))


def _nebius_orchestrator(request: Request) -> NebiusExperimentOrchestrator:
    return NebiusExperimentOrchestrator(ExperimentRepository(_store(request)), getattr(request.app.state, "settings", None))


def _resolve_readable_artifact(request: Request, raw_path: str) -> Path:
    repo_root = _repo_root().resolve()
    output_root = _store(request).output_dir.resolve()
    path = Path(raw_path)
    if not path.is_absolute():
        path = (repo_root / path).resolve()
    else:
        path = path.resolve()

    allowed_roots = [output_root, repo_root / "assets" / "screenshots"]
    if not any(path == root or root in path.parents for root in allowed_roots):
        raise HTTPException(status_code=403, detail="artifact path is outside readable artifact roots")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"artifact not found: {raw_path}")
    return path


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "text/markdown"
    if suffix == ".csv":
        return "text/csv"
    if suffix in {".json", ".jsonl"}:
        return "application/json"
    if suffix == ".pdf":
        return "application/pdf"
    if suffix == ".svg":
        return "image/svg+xml"
    return "text/plain"


def _artifact_to_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".md":
        return text
    fence = "json" if path.suffix.lower() in {".json", ".jsonl"} else "csv" if path.suffix.lower() == ".csv" else "text"
    return f"# Exported Artifact: {path.name}\n\nSource: `{path}`\n\n```{fence}\n{text[:100_000]}\n```\n"


def _write_simple_pdf(path: Path, markdown: str) -> None:
    lines = markdown.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").splitlines()[:54]
    stream_lines = ["BT", "/F1 10 Tf", "50 780 Td", "14 TL"]
    for line in lines:
        stream_lines.append(f"({line[:95]}) Tj")
        stream_lines.append("T*")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines).encode("latin-1", errors="replace")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj\n",
        f"5 0 obj << /Length {len(stream)} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(content))
        content.extend(obj)
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(bytes(content))


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [here.parents[3], here.parents[2], Path.cwd()]
    for candidate in candidates:
        if (candidate / "serverless" / "jobs" / "detector_tournament.py").exists():
            return candidate
    return here.parents[3]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _report_index_files() -> list[str]:
    return [
        "experiments/attack_experiments.jsonl",
        "experiments/attack_launches.jsonl",
        "experiments/benchmark_runs.jsonl",
        "red-team/generated_scenarios.jsonl",
        "nebius/smart_batches.jsonl",
        "nebius/artifacts.jsonl",
        "nebius/detections.jsonl",
        "nebius/investigation_reports.jsonl",
        "incidents/incidents.jsonl",
        "incidents/explanations.jsonl",
        "attacks/attacks.jsonl",
        "events/events.jsonl",
        "events/significant_events.jsonl",
        "labels/scenario_labels.jsonl",
        "history/artifacts.jsonl",
        "history/ticks.jsonl",
        "evidence/screenshots.jsonl",
        "evidence/promoted_runs.jsonl",
    ]


def _report_artifact_dirs() -> list[str]:
    return [
        "benchmark",
        "serverless-batch",
        "exports",
        "challenge-submission",
        "evidence",
        "datasets",
    ]


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
