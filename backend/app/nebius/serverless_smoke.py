import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from app.api.routes_incidents import build_compact_replay_payload, persist_explanation_result
from app.config import get_settings
from app.experiments.manager import ExperimentManager
from app.experiments.models import Experiment, ExperimentCreateRequest, utc_now
from app.experiments.nebius_orchestrator import ExperimentJobRecord
from app.experiments.repository import ExperimentRepository
from app.nebius.client import IncidentExplanationResponse, NebiusClient
from app.nebius.detector_tournament import (
    DetectorTournamentMetrics,
    DetectorTournamentResponse,
    DetectorTournamentStartRequest,
    start_tournament,
)
from app.nebius.investigation_team import AIInvestigationTeamRequest, AIInvestigationTeamResponse
from app.nebius.evidence_archive import NebiusEvidenceArchive, NebiusEvidenceRecord
from app.nebius.scenario_generator import MarketAbuseScenarioGenerationRequest
from app.schemas.arena import ArenaState, DetectorScore, Incident
from app.storage.local_store import LocalStore


SmokeMode = Literal["local", "real_nebius_pending", "real_nebius", "error"]
SmokeExecutionMode = Literal["local", "nebius"]


class ArenaSimulationClient(Protocol):
    @property
    def state(self) -> ArenaState: ...

    async def reset(self) -> ArenaState: ...

    def launch_scenario(self, scenario_name: str) -> dict[str, object]: ...

    async def _advance_tick_async(self, running: bool = True) -> None: ...


class ServerlessSmokeRequest(BaseModel):
    execution_mode: SmokeExecutionMode = "local"


class ServerlessSmokeUsage(BaseModel):
    duration_seconds: float
    endpoint_calls: int
    endpoint_avg_latency_seconds: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    job_runs: int
    workloads: int
    simulation_events: int
    artifact_count: int
    artifact_bytes: int
    endpoint_cost_usd: float
    job_cost_usd: float
    estimated_cost_usd: float
    cost_basis: str


class SmokeArtifact(BaseModel):
    name: str
    path: str
    download_url: str


class ServerlessSmokeResponse(BaseModel):
    mode: SmokeMode
    summary: str
    scenario_id: str
    incident_id: str | None = None
    detector_alerts: list[dict[str, Any]]
    explanation: IncidentExplanationResponse | None = None
    investigation: AIInvestigationTeamResponse | None = None
    tournament: DetectorTournamentResponse
    cloud_tournament: DetectorTournamentResponse | None = None
    serverless_job: dict[str, Any]
    artifacts: list[SmokeArtifact]
    benefits: list[str] = Field(default_factory=list)
    experiment_id: str
    evidence_id: str
    evidence_s3_status: Literal["uploaded", "local_only", "upload_failed"]
    evidence_source_uri: str | None = None
    usage: ServerlessSmokeUsage


class ServerlessSmokeFinalizeResponse(BaseModel):
    experiment: Experiment
    evidence: NebiusEvidenceRecord
    usage: ServerlessSmokeUsage


async def run_serverless_smoke_demo(
    *,
    client: NebiusClient,
    simulation: ArenaSimulationClient,
    store: LocalStore,
    repo_root: Path,
    execution_mode: SmokeExecutionMode = "local",
    tournament_metrics: DetectorTournamentMetrics | None = None,
) -> ServerlessSmokeResponse:
    settings = get_settings()
    started_at = perf_counter()
    created_at = _now()
    repository = ExperimentRepository(store)
    manager = ExperimentManager(repository)
    experiment = manager.create(
        ExperimentCreateRequest(
            name=f"Polished E2E demo · {created_at[:19]}",
            attack_count=9,
            batch_size=9,
            scenarios=["spoofing_like_wall", "layering_like"],
            seed=42,
            nebius_mode="local_parallel_batch" if execution_mode == "local" else "real_nebius_pending",
        )
    )
    archive = NebiusEvidenceArchive(store, settings)
    evidence_before = {record.evidence_id for record in archive.list_records(limit=10_000)}
    artifact_dir = store.output_dir / "serverless-smoke" / experiment.id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    scenario_request = MarketAbuseScenarioGenerationRequest(
        manipulation_type="spoofing_like_wall",
        difficulty="medium",
        symbol="AIMD",
        duration_ticks=120,
        liquidity_regime="thin",
        volatility_regime="high",
        seed=42,
    )
    scenario = client.generate_market_abuse_scenario(scenario_request)

    await simulation.reset()
    simulation.launch_scenario("spoofing_like_wall")
    state = await _run_simulation_window(simulation, max_ticks=90)
    incident = _select_incident(state)
    detector_alerts = [_score_to_dict(score) for score in state.detectors.alerts]
    if not detector_alerts:
        detector_alerts = [_score_to_dict(score) for score in state.detectors.scores if score.confidence >= 0.5]

    explanation = None
    investigation = None
    replay_payload: dict[str, Any] = {}
    if incident is not None:
        replay_payload = build_compact_replay_payload(incident, state)
        explanation = persist_explanation_result(
            store=store,
            incident=incident,
            explanation=client.explain_incident(incident, replay_payload=replay_payload),
            replay_payload=replay_payload,
        )
        investigation = client.analyze_investigation_team(
            AIInvestigationTeamRequest(
                incident=incident.model_dump(mode="json"),
                detector_outputs=detector_alerts,
                order_book_context=replay_payload.get("book", {}),
                trades=_trade_events(state),
                market_metrics=replay_payload.get("features", {}),
            )
        )

    local_tournament = start_tournament(
        DetectorTournamentStartRequest(
            number_of_scenarios=9,
            manipulation_types=["spoofing_like_wall", "layering_like"],
            difficulty_mix={"easy": 0.33, "medium": 0.34, "hard": 0.33},
            detector_set=["spoofing_like", "layering_like", "quote_stuffing", "liquidity_shock"],
            random_seed=42,
            execution_mode="local",
        ),
        store=store,
        repo_root=repo_root,
        observer=tournament_metrics,
    )
    cloud_tournament = (
        start_tournament(
            DetectorTournamentStartRequest(
                number_of_scenarios=9,
                    manipulation_types=["spoofing_like_wall", "layering_like"],
                difficulty_mix={"easy": 0.33, "medium": 0.34, "hard": 0.33},
                detector_set=["spoofing_like", "layering_like", "quote_stuffing", "liquidity_shock"],
                random_seed=42,
                execution_mode="nebius",
            ),
            store=store,
            repo_root=repo_root,
            observer=tournament_metrics,
        )
        if execution_mode == "nebius" and _job_submit_configured(settings)
        else None
    )
    serverless_job = (
        {
            "status": "completed",
            "execution_mode": "local_mock",
            "job_id": local_tournament.tournament_id,
            "message": "Local Mock tournament completed without cloud resources.",
            "local_tournament_id": local_tournament.tournament_id,
            "templates_configured": False,
            "artifact_collection_configured": False,
            "cloud_output_uri": None,
            "artifacts": local_tournament.artifacts,
        }
        if execution_mode == "local"
        else _serverless_job_status(settings, local_tournament, cloud_tournament)
    )
    mode: SmokeMode = "local" if execution_mode == "local" else (
        "error" if serverless_job["status"] == "failed" else "real_nebius" if cloud_tournament is not None else "real_nebius_pending"
    )

    investigation_markdown = _investigation_markdown(
        created_at=created_at,
        incident=incident,
        explanation=explanation,
        investigation=investigation,
        tournament=local_tournament,
        serverless_job=serverless_job,
    )
    artifact_payloads: dict[str, Any] = {
        "summary.json": {
            "created_at": created_at,
            "experiment_id": experiment.id,
            "mode": mode,
            "story": "AI-generated spoofing incident -> LOB simulation -> detector alert -> LLM explanation -> AI investigation -> detector tournament -> artifacts.",
            "scenario_id": scenario.scenario_id,
            "incident_id": incident.id if incident else None,
            "detector_alert_count": len(detector_alerts),
            "tournament_id": local_tournament.tournament_id,
            "serverless_job_status": serverless_job["status"],
            "serverless_job_output_uri": serverless_job.get("cloud_output_uri"),
            "artifact_collection_configured": serverless_job.get("artifact_collection_configured"),
            "normal_baseline": "Covered by local simulation events and false-positive fields in tournament rows.",
        },
        "scenario.json": scenario.model_dump(mode="json"),
        "simulation_events.json": [event.model_dump(mode="json") for event in state.events],
        "detector_alerts.json": detector_alerts,
        "tournament_result.json": local_tournament.model_dump(mode="json"),
        "serverless_job.json": serverless_job,
        "manifest.json": {
            "created_at": created_at,
            "artifacts": [
                "summary.json",
                "scenario.json",
                "simulation_events.json",
                "detector_alerts.json",
                "investigation_report.md",
                "tournament_result.json",
                "serverless_job.json",
            ],
            "required_modes": ["local", "real_nebius_pending", "real_nebius", "error"],
            "job_templates_configured": _job_submit_configured(settings),
            "artifact_collection_configured": _artifact_collection_configured(settings),
            "job_output_uri": getattr(settings, "nebius_job_output_uri", None),
            "object_storage_endpoint_url": getattr(settings, "nebius_object_storage_endpoint_url", None),
        },
    }
    for name, payload in artifact_payloads.items():
        _write_json(artifact_dir / name, payload)
    (artifact_dir / "investigation_report.md").write_text(investigation_markdown, encoding="utf-8")

    artifacts = [
        SmokeArtifact(
            name=name,
            path=str(artifact_dir / name),
            download_url=f"/api/experiments/artifacts/download?path={artifact_dir / name}",
        )
        for name in [
            "summary.json",
            "scenario.json",
            "simulation_events.json",
            "detector_alerts.json",
            "investigation_report.md",
            "tournament_result.json",
            "serverless_job.json",
            "manifest.json",
        ]
    ]
    artifact_paths = {artifact.name.rsplit(".", 1)[0]: artifact.path for artifact in artifacts}
    duration_seconds = round(perf_counter() - started_at, 4)
    session_endpoint_records = [
        record
        for record in archive.list_records(limit=10_000)
        if record.evidence_id not in evidence_before and record.kind == "endpoint_call"
    ]
    endpoint_calls = len(session_endpoint_records)
    endpoint_latency_total = sum(record.latency_seconds or 0.0 for record in session_endpoint_records)
    prompt_tokens = sum(record.prompt_tokens for record in session_endpoint_records)
    completion_tokens = sum(record.completion_tokens for record in session_endpoint_records)
    total_tokens = sum(record.total_tokens for record in session_endpoint_records)
    endpoint_cost = sum(record.estimated_cost_usd or 0.0 for record in session_endpoint_records)
    job_runs = 1 + int(cloud_tournament is not None)
    job_cost = (
        duration_seconds / 3600 * settings.nebius_job_cost_per_hour_usd
        if execution_mode == "nebius"
        and cloud_tournament is not None
        and cloud_tournament.status in {"completed", "failed"}
        and settings.nebius_job_cost_per_hour_usd > 0
        else 0.0
    )
    artifact_bytes = sum(Path(artifact.path).stat().st_size for artifact in artifacts)
    usage = ServerlessSmokeUsage(
        duration_seconds=duration_seconds,
        endpoint_calls=endpoint_calls,
        endpoint_avg_latency_seconds=round(endpoint_latency_total / endpoint_calls, 4) if endpoint_calls else 0.0,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        job_runs=job_runs,
        workloads=9 * job_runs,
        simulation_events=len(state.events),
        artifact_count=len(artifacts),
        artifact_bytes=artifact_bytes,
        endpoint_cost_usd=round(endpoint_cost, 8),
        job_cost_usd=round(job_cost, 8),
        estimated_cost_usd=round(endpoint_cost + job_cost, 8),
        cost_basis=(
            "Local Mock uses no metered cloud resources."
            if execution_mode == "local"
            else "Configured token and job-hour rates."
            if settings.nebius_job_cost_per_hour_usd > 0 or endpoint_cost > 0
            else "Usage measured; cloud pricing rates are not configured."
        ),
    )
    cloud_pending = execution_mode == "nebius" and (
        cloud_tournament is None or cloud_tournament.status not in {"completed", "failed"}
    )
    final_status = "failed" if mode == "error" else "submitted" if cloud_pending else "completed"
    initial_job_status = (
        cloud_tournament.status
        if cloud_tournament is not None
        else "real_nebius_pending"
        if cloud_pending
        else "failed"
        if mode == "error"
        else "completed"
    )
    evidence = archive.record(
        kind="job",
        operation="polished_e2e_demo",
        status="running" if cloud_pending else "completed" if mode != "error" else "failed",
        request_payload={"execution_mode": execution_mode, "experiment_id": experiment.id},
        response_payload={
            "mode": mode,
            "scenario_id": scenario.scenario_id,
            "incident_id": incident.id if incident else None,
            "usage": usage.model_dump(mode="json"),
        },
        run_id=experiment.id,
        evidence_files=artifact_paths,
    )
    job = ExperimentJobRecord(
        job_id=f"E2E-{experiment.id.removeprefix('EXP-')}",
        experiment_id=experiment.id,
        backend="nebius_serverless_job" if execution_mode == "nebius" else "local_parallel_batch",
        status=initial_job_status,
        batch_start=0,
        batch_end=9,
        attack_count=9,
        created_at=created_at,
        updated_at=utc_now(),
        message=f"Polished E2E demo completed in {mode} mode.",
        artifact_paths=artifact_paths,
    )
    store.append_jsonl(f"experiments/{experiment.id}/jobs.jsonl", job.model_dump(mode="json"))
    updated_experiment = experiment.model_copy(
        update={
            "status": final_status,
            "smart_batch_id": local_tournament.tournament_id,
            "artifact_dir": str(artifact_dir),
            "artifact_paths": {
                **artifact_paths,
                "jobs": str(repository.experiment_dir(experiment.id) / "jobs.jsonl"),
                "e2e_evidence": evidence.artifact_paths.get("metadata", ""),
            },
            "metrics": [{"kind": "polished_e2e_usage", **usage.model_dump(mode="json")}],
            "updated_at": utc_now(),
        }
    )
    repository.save(updated_experiment)
    store.append_jsonl(
        "nebius/serverless_smoke_runs.jsonl",
        {
            "created_at": created_at,
            "mode": mode,
            "scenario_id": scenario.scenario_id,
            "incident_id": incident.id if incident else None,
            "artifact_dir": str(artifact_dir),
            "tournament_id": local_tournament.tournament_id,
            "serverless_job": serverless_job,
        },
    )
    return ServerlessSmokeResponse(
        mode=mode,
        summary="Serverless smoke demo completed locally with honest Nebius job status.",
        scenario_id=scenario.scenario_id,
        incident_id=incident.id if incident else None,
        detector_alerts=detector_alerts,
        explanation=explanation,
        investigation=investigation,
        tournament=local_tournament,
        cloud_tournament=cloud_tournament,
        serverless_job=serverless_job,
        artifacts=artifacts,
        benefits=[
            "Burst compute for detector tournaments",
            "Isolated reproducible detector runs",
            "No always-on infrastructure for benchmark batches",
            "Scalable tournament evaluation",
            "AI endpoint for interactive analyst support",
        ],
        experiment_id=experiment.id,
        evidence_id=evidence.evidence_id,
        evidence_s3_status=evidence.s3_status,
        evidence_source_uri=evidence.source_uri,
        usage=usage,
    )


def finalize_serverless_smoke_demo(
    *,
    experiment_id: str,
    tournament: DetectorTournamentResponse,
    store: LocalStore,
) -> ServerlessSmokeFinalizeResponse:
    if tournament.status not in {"completed", "failed"}:
        raise ValueError("Nebius tournament is not finished")
    repository = ExperimentRepository(store)
    experiment = repository.get(experiment_id)
    if experiment is None:
        raise LookupError(f"experiment {experiment_id} not found")

    settings = get_settings()
    previous_usage = next(
        (
            ServerlessSmokeUsage.model_validate(metric)
            for metric in experiment.metrics
            if metric.get("kind") == "polished_e2e_usage"
        ),
        None,
    )
    cloud_runtime = _tournament_duration_seconds(tournament)
    usage = _final_cloud_usage(previous_usage, cloud_runtime=cloud_runtime, settings=settings)
    cloud_artifacts = {f"cloud_{name}": path for name, path in tournament.artifacts.items()}
    archive = NebiusEvidenceArchive(store, settings)
    evidence = archive.record(
        kind="job",
        operation="polished_e2e_cloud_results",
        status=tournament.status,
        request_payload={"experiment_id": experiment_id, "tournament_id": tournament.tournament_id},
        response_payload={
            "tournament": tournament.model_dump(mode="json"),
            "usage": usage.model_dump(mode="json"),
        },
        run_id=experiment_id,
        evidence_files=cloud_artifacts,
    )
    artifact_paths = {
        **experiment.artifact_paths,
        **cloud_artifacts,
        "e2e_cloud_evidence": evidence.artifact_paths.get("metadata", ""),
    }
    updated = experiment.model_copy(
        update={
            "status": "completed" if tournament.status == "completed" else "failed",
            "smart_batch_id": tournament.tournament_id,
            "artifact_paths": artifact_paths,
            "metrics": [
                *[metric for metric in experiment.metrics if metric.get("kind") != "polished_e2e_usage"],
                {"kind": "polished_e2e_usage", **usage.model_dump(mode="json")},
                {"kind": "polished_e2e_cloud_tournament", **tournament.metrics},
            ],
            "updated_at": utc_now(),
        }
    )
    repository.save(updated)
    store.append_jsonl(
        f"experiments/{experiment.id}/jobs.jsonl",
        ExperimentJobRecord(
            job_id=tournament.tournament_id,
            experiment_id=experiment.id,
            backend="nebius_serverless_job",
            status=tournament.status,
            batch_start=0,
            batch_end=experiment.attack_count,
            attack_count=experiment.attack_count,
            created_at=tournament.started_at,
            updated_at=tournament.completed_at or utc_now(),
            message=tournament.summary,
            artifact_paths=cloud_artifacts,
        ).model_dump(mode="json"),
    )
    return ServerlessSmokeFinalizeResponse(experiment=updated, evidence=evidence, usage=usage)


def _final_cloud_usage(
    previous: ServerlessSmokeUsage | None,
    *,
    cloud_runtime: float,
    settings: Any,
) -> ServerlessSmokeUsage:
    base = previous or ServerlessSmokeUsage(
        duration_seconds=0,
        endpoint_calls=0,
        endpoint_avg_latency_seconds=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        job_runs=1,
        workloads=0,
        simulation_events=0,
        artifact_count=0,
        artifact_bytes=0,
        endpoint_cost_usd=0,
        job_cost_usd=0,
        estimated_cost_usd=0,
        cost_basis="Usage measured; cloud pricing rates are not configured.",
    )
    token_cost = (
        base.prompt_tokens / 1_000_000 * settings.nebius_input_token_cost_per_million_usd
        + base.completion_tokens / 1_000_000 * settings.nebius_output_token_cost_per_million_usd
    )
    job_cost = cloud_runtime / 3600 * settings.nebius_job_cost_per_hour_usd
    rates_configured = any(
        rate > 0
        for rate in (
            settings.nebius_input_token_cost_per_million_usd,
            settings.nebius_output_token_cost_per_million_usd,
            settings.nebius_job_cost_per_hour_usd,
        )
    )
    return base.model_copy(
        update={
            "duration_seconds": round(max(base.duration_seconds, cloud_runtime), 4),
            "endpoint_cost_usd": round(token_cost, 8),
            "job_cost_usd": round(job_cost, 8),
            "estimated_cost_usd": round(token_cost + job_cost, 8),
            "cost_basis": (
                "Configured token and Nebius job-hour rates."
                if rates_configured
                else "Usage measured; cloud pricing rates are not configured."
            ),
        }
    )


def _tournament_duration_seconds(tournament: DetectorTournamentResponse) -> float:
    if not tournament.completed_at:
        return 0.0
    try:
        started = datetime.fromisoformat(tournament.started_at.replace("Z", "+00:00"))
        completed = datetime.fromisoformat(tournament.completed_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return max(0.0, (completed - started).total_seconds())


async def _run_simulation_window(simulation: ArenaSimulationClient, *, max_ticks: int) -> ArenaState:
    state = simulation.state
    for _ in range(max_ticks):
        await simulation._advance_tick_async(running=True)
        state = simulation.state
        if state.incidents:
            break
    return state


def _select_incident(state: ArenaState) -> Incident | None:
    incidents = state.incidents or []
    if not incidents:
        return None
    return max(incidents, key=lambda item: item.confidence)


def _score_to_dict(score: DetectorScore) -> dict[str, Any]:
    return score.model_dump(mode="json")


def _trade_events(state: ArenaState) -> list[dict[str, Any]]:
    return [
        event.model_dump(mode="json", exclude_none=True)
        for event in state.events
        if event.message and "consumed small top-of-book quantity" in event.message
    ][:20]


def _serverless_job_status(
    settings: Any,
    tournament: DetectorTournamentResponse,
    cloud_tournament: DetectorTournamentResponse | None,
) -> dict[str, Any]:
    configured = _job_submit_configured(settings)
    artifact_collection_configured = _artifact_collection_configured(settings)
    if not configured:
        return {
            "status": "real_nebius_pending",
            "execution_mode": "nebius_serverless_job",
            "job_id": None,
            "message": "Nebius job submit/status/log commands are not configured for this backend process.",
            "local_tournament_id": tournament.tournament_id,
            "templates_configured": False,
            "artifact_collection_configured": artifact_collection_configured,
            "cloud_output_uri": _cloud_output_uri(settings),
        }
    if cloud_tournament is not None:
        return {
            "status": cloud_tournament.status,
            "execution_mode": cloud_tournament.execution_mode,
            "job_id": cloud_tournament.metrics.get("nebius_job_id") if isinstance(cloud_tournament.metrics, dict) else None,
            "message": _cloud_job_message(cloud_tournament, artifact_collection_configured=artifact_collection_configured),
            "local_tournament_id": tournament.tournament_id,
            "cloud_tournament_id": cloud_tournament.tournament_id,
            "templates_configured": True,
            "artifact_collection_configured": artifact_collection_configured,
            "cloud_output_uri": _cloud_tournament_output_uri(cloud_tournament, settings),
            "artifacts": cloud_tournament.artifacts,
        }
    return {
        "status": "real_nebius_pending",
        "execution_mode": "nebius_serverless_job",
        "job_id": None,
        "message": "Nebius command templates are configured but no cloud tournament was submitted.",
        "local_tournament_id": tournament.tournament_id,
        "templates_configured": True,
        "artifact_collection_configured": artifact_collection_configured,
        "cloud_output_uri": _cloud_output_uri(settings),
    }


def _job_submit_configured(settings: Any) -> bool:
    return bool(
        settings.nebius_job_submit_command_template
        and settings.nebius_job_status_command_template
        and settings.nebius_job_logs_command_template
    )


def _artifact_collection_configured(settings: Any) -> bool:
    return bool(
        settings.nebius_job_artifacts_command_template
        or getattr(settings, "nebius_job_output_uri", None)
    )


def _cloud_output_uri(settings: Any) -> str | None:
    base_uri = str(getattr(settings, "nebius_job_output_uri", "") or "").rstrip("/")
    if not base_uri:
        return None
    return f"{base_uri}/tournaments"


def _cloud_tournament_output_uri(cloud_tournament: DetectorTournamentResponse, settings: Any) -> str | None:
    configured = cloud_tournament.metrics.get("cloud_output_uri")
    return str(configured) if configured else _cloud_output_uri(settings)


def _cloud_job_message(
    cloud_tournament: DetectorTournamentResponse,
    *,
    artifact_collection_configured: bool,
) -> str:
    if artifact_collection_configured:
        return cloud_tournament.summary
    return (
        f"{cloud_tournament.summary} Cloud artifact sync is pending an output URI; "
        "set a Nebius output volume plus NEBIUS_JOB_OUTPUT_URI when you want the UI to collect job artifacts."
    )


def _investigation_markdown(
    *,
    created_at: str,
    incident: Incident | None,
    explanation: IncidentExplanationResponse | None,
    investigation: AIInvestigationTeamResponse | None,
    tournament: DetectorTournamentResponse,
    serverless_job: dict[str, Any],
) -> str:
    lines = [
        "# LOB Arena Nebius Serverless Smoke Demo",
        "",
        f"- Created: {created_at}",
        f"- Incident: {incident.id if incident else 'not created'}",
        f"- Serverless job status: {serverless_job['status']}",
        "",
        "## Incident Explanation",
        explanation.plain_english_summary if explanation else "No incident explanation was produced.",
        "",
        "## AI Investigation",
        investigation.executive_summary if investigation else "No AI investigation was produced.",
        "",
        "## Detector Tournament",
        f"Tournament `{tournament.tournament_id}` completed with {len(tournament.leaderboard)} leaderboard rows.",
    ]
    return "\n".join(lines) + "\n"


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
