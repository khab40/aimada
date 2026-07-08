import asyncio
from pathlib import Path

from app.arena.engine import SimulationEngine
from app.nebius.client import NebiusClient
from app.nebius.serverless_smoke import run_serverless_smoke_demo
from app.storage.local_store import LocalStore


def test_serverless_smoke_demo_writes_artifacts_and_leaderboard(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    response = asyncio.run(
        run_serverless_smoke_demo(
            client=NebiusClient(incident_explainer_url="", investigation_team_url="", market_abuse_scenario_url=""),
            simulation=SimulationEngine(store=store, normal_agent_count=3),
            store=store,
            repo_root=Path(__file__).resolve().parents[2],
        )
    )

    artifact_names = {artifact.name for artifact in response.artifacts}

    assert response.mode == "real_nebius_pending"
    assert response.incident_id
    assert response.detector_alerts
    assert response.explanation is not None
    assert response.investigation is not None
    assert response.tournament.leaderboard
    assert response.serverless_job["status"] == "real_nebius_pending"
    assert {
        "summary.json",
        "scenario.json",
        "simulation_events.json",
        "detector_alerts.json",
        "investigation_report.md",
        "tournament_result.json",
        "serverless_job.json",
        "manifest.json",
    } <= artifact_names
    assert (tmp_path / "serverless-smoke" / "manifest.json").exists()
