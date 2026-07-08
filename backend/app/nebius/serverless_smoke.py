import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.api.routes_incidents import build_compact_replay_payload, persist_explanation_result
from app.arena.engine import SimulationEngine
from app.config import get_settings
from app.nebius.client import IncidentExplanationResponse, NebiusClient
from app.nebius.detector_tournament import (
    DetectorTournamentResponse,
    DetectorTournamentStartRequest,
    start_tournament,
)
from app.nebius.investigation_team import AIInvestigationTeamRequest, AIInvestigationTeamResponse
from app.nebius.scenario_generator import MarketAbuseScenarioGenerationRequest
from app.schemas.arena import ArenaState, DetectorScore, Incident
from app.storage.local_store import LocalStore


SmokeMode = Literal["local", "real_nebius_pending", "real_nebius", "error"]


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
    serverless_job: dict[str, Any]
    artifacts: list[SmokeArtifact]
    benefits: list[str] = Field(default_factory=list)


async def run_serverless_smoke_demo(
    *,
    client: NebiusClient,
    simulation: SimulationEngine,
    store: LocalStore,
    repo_root: Path,
) -> ServerlessSmokeResponse:
    settings = get_settings()
    created_at = _now()
    artifact_dir = store.output_dir / "serverless-smoke"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    scenario_request = MarketAbuseScenarioGenerationRequest(
        manipulation_type="spoofing",
        difficulty="medium",
        symbol="AIMD",
        duration_ticks=120,
        liquidity_regime="thin",
        volatility_regime="high",
        seed=42,
    )
    scenario = client.generate_market_abuse_scenario(scenario_request)

    await simulation.reset()
    simulation.launch_scenario("spoofing-like")
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
            manipulation_types=["spoofing", "layering"],
            difficulty_mix={"easy": 0.33, "medium": 0.34, "hard": 0.33},
            detector_set=["spoofing_like", "layering_like", "quote_stuffing", "liquidity_shock"],
            random_seed=42,
            execution_mode="local",
        ),
        store=store,
        repo_root=repo_root,
    )
    cloud_tournament = (
        start_tournament(
            DetectorTournamentStartRequest(
                number_of_scenarios=9,
                manipulation_types=["spoofing", "layering"],
                difficulty_mix={"easy": 0.33, "medium": 0.34, "hard": 0.33},
                detector_set=["spoofing_like", "layering_like", "quote_stuffing", "liquidity_shock"],
                random_seed=42,
                execution_mode="nebius",
            ),
            store=store,
            repo_root=repo_root,
        )
        if _job_templates_configured(settings)
        else None
    )
    serverless_job = _serverless_job_status(settings, local_tournament, cloud_tournament)
    mode: SmokeMode = (
        "error"
        if serverless_job["status"] == "failed"
        else "real_nebius"
        if cloud_tournament is not None
        else "real_nebius_pending"
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
            "mode": mode,
            "story": "AI-generated spoofing incident -> LOB simulation -> detector alert -> LLM explanation -> AI investigation -> detector tournament -> artifacts.",
            "scenario_id": scenario.scenario_id,
            "incident_id": incident.id if incident else None,
            "detector_alert_count": len(detector_alerts),
            "tournament_id": local_tournament.tournament_id,
            "serverless_job_status": serverless_job["status"],
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
            "job_templates_configured": _job_templates_configured(settings),
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
        serverless_job=serverless_job,
        artifacts=artifacts,
        benefits=[
            "Burst compute for detector tournaments",
            "Isolated reproducible detector runs",
            "No always-on infrastructure for benchmark batches",
            "Scalable tournament evaluation",
            "AI endpoint for interactive analyst support",
        ],
    )


async def _run_simulation_window(simulation: SimulationEngine, *, max_ticks: int) -> ArenaState:
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
    configured = _job_templates_configured(settings)
    if not configured:
        return {
            "status": "real_nebius_pending",
            "execution_mode": "nebius_serverless_job",
            "job_id": None,
            "message": "NEBIUS_JOB_*_COMMAND_TEMPLATE values are not configured; local tournament artifact is available.",
            "local_tournament_id": tournament.tournament_id,
            "templates_configured": False,
        }
    if cloud_tournament is not None:
        return {
            "status": cloud_tournament.status,
            "execution_mode": cloud_tournament.execution_mode,
            "job_id": cloud_tournament.metrics.get("nebius_job_id") if isinstance(cloud_tournament.metrics, dict) else None,
            "message": cloud_tournament.summary,
            "local_tournament_id": tournament.tournament_id,
            "cloud_tournament_id": cloud_tournament.tournament_id,
            "templates_configured": True,
            "artifacts": cloud_tournament.artifacts,
        }
    return {
        "status": "real_nebius_pending",
        "execution_mode": "nebius_serverless_job",
        "job_id": None,
        "message": "Nebius command templates are configured but no cloud tournament was submitted.",
        "local_tournament_id": tournament.tournament_id,
        "templates_configured": True,
    }


def _job_templates_configured(settings: Any) -> bool:
    return bool(
        settings.nebius_job_submit_command_template
        and settings.nebius_job_status_command_template
        and settings.nebius_job_logs_command_template
        and settings.nebius_job_artifacts_command_template
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
        "# AIMADA Nebius Serverless Smoke Demo",
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
