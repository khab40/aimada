import asyncio
import subprocess
from pathlib import Path
from typing import Any

from app.arena.engine import SimulationEngine
from app.config import get_settings
from app.nebius.client import NebiusClient
from app.nebius.serverless_smoke import run_serverless_smoke_demo
from app.storage.local_store import LocalStore


def test_serverless_smoke_demo_writes_artifacts_and_leaderboard(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setenv("NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE", "")
    monkeypatch.setenv("NEBIUS_JOB_STATUS_COMMAND_TEMPLATE", "")
    monkeypatch.setenv("NEBIUS_JOB_LOGS_COMMAND_TEMPLATE", "")
    monkeypatch.setenv("NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE", "")
    monkeypatch.setenv("NEBIUS_JOB_OUTPUT_URI", "")
    get_settings.cache_clear()
    store = LocalStore(tmp_path)
    try:
        response = asyncio.run(
            run_serverless_smoke_demo(
                client=NebiusClient(incident_explainer_url="", investigation_team_url="", market_abuse_scenario_url=""),
                simulation=SimulationEngine(store=store, normal_agent_count=3),
                store=store,
                repo_root=Path(__file__).resolve().parents[2],
            )
        )
    finally:
        get_settings.cache_clear()

    artifact_names = {artifact.name for artifact in response.artifacts}

    assert response.mode == "real_nebius_pending"
    assert response.incident_id
    assert response.detector_alerts
    assert response.explanation is not None
    assert response.investigation is not None
    assert response.tournament.leaderboard
    assert response.serverless_job["status"] == "real_nebius_pending"
    assert "NEBIUS_JOB_*_COMMAND_TEMPLATE" not in response.serverless_job["message"]
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


def test_serverless_smoke_demo_reports_configured_nebius_job(monkeypatch: Any, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout='{"job_id":"job-smoke-123"}', stderr="")

    monkeypatch.setenv(
        "NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE",
        "submit-job {config_path} {subnet_id_arg} {parent_id_arg} {volume_arg}",
    )
    monkeypatch.setenv("NEBIUS_JOB_STATUS_COMMAND_TEMPLATE", "status-job {job_id}")
    monkeypatch.setenv("NEBIUS_JOB_LOGS_COMMAND_TEMPLATE", "logs-job {job_id}")
    monkeypatch.setenv("NEBIUS_JOB_ARTIFACTS_COMMAND_TEMPLATE", "")
    monkeypatch.setenv("NEBIUS_JOB_OUTPUT_URI", "")
    monkeypatch.setenv("NEBIUS_SUBNET_ID", "vpcsubnet-test")
    monkeypatch.setenv("NEBIUS_PARENT_ID", "project-test")
    monkeypatch.setenv("NEBIUS_JOB_OUTPUT_VOLUME", "s3://bucket:/job/outputs:rw")
    monkeypatch.setattr("app.nebius.detector_tournament.subprocess.run", fake_run)
    get_settings.cache_clear()
    store = LocalStore(tmp_path)
    try:
        response = asyncio.run(
            run_serverless_smoke_demo(
                client=NebiusClient(incident_explainer_url="", investigation_team_url="", market_abuse_scenario_url=""),
                simulation=SimulationEngine(store=store, normal_agent_count=3),
                store=store,
                repo_root=Path(__file__).resolve().parents[2],
            )
        )
    finally:
        get_settings.cache_clear()

    assert response.mode == "real_nebius"
    assert response.serverless_job["status"] == "queued"
    assert response.serverless_job["job_id"] == "job-smoke-123"
    assert response.serverless_job["templates_configured"] is True
    assert response.serverless_job["artifact_collection_configured"] is False
    assert response.cloud_tournament is not None
    assert response.cloud_tournament.tournament_id == response.serverless_job["cloud_tournament_id"]
    assert "NEBIUS_JOB_*_COMMAND_TEMPLATE" not in response.serverless_job["message"]
    assert "--subnet-id" in captured["argv"]
    assert "vpcsubnet-test" in captured["argv"]
    assert "--parent-id" in captured["argv"]
    assert "project-test" in captured["argv"]
    assert "--volume" in captured["argv"]
    assert "s3://bucket:/job/outputs:rw" in captured["argv"]
