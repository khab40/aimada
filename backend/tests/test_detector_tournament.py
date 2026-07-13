import subprocess
from pathlib import Path
from types import SimpleNamespace

from fastapi import BackgroundTasks

from app.config import get_settings
from app.api.routes_nebius import read_detector_tournament, start_detector_tournament
from app.nebius.detector_tournament import (
    DetectorTournamentStartRequest,
    _parse_job_id,
    get_tournament,
    start_tournament,
)
from app.storage.local_store import LocalStore


def test_detector_tournament_runs_local_mock_and_persists(tmp_path: Path) -> None:
    store = LocalStore(tmp_path)
    response = start_tournament(
        DetectorTournamentStartRequest(
            number_of_scenarios=2,
            manipulation_types=["spoofing"],
            detector_set=["spoofing_like"],
            execution_mode="local_mock",
            random_seed=7,
        ),
        store=store,
        repo_root=Path(__file__).resolve().parents[2],
    )
    loaded = get_tournament(response.tournament_id, store=store)

    assert response.status == "completed"
    assert response.execution_mode == "local_mock"
    assert response.leaderboard
    assert response.leaderboard[0].false_positives >= 0
    assert response.leaderboard[0].false_negatives >= 0
    assert response.artifacts == {}
    assert response.fallback_reason
    assert loaded is not None
    assert loaded.tournament_id == response.tournament_id


def test_parse_job_id_accepts_nebius_cli_text_output() -> None:
    assert _parse_job_id("Job ID: aijob-e00chpkqr83hdbwgkr\n") == "aijob-e00chpkqr83hdbwgkr"


def test_detector_tournament_nebius_mode_falls_back_without_submit_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE", "")
    get_settings.cache_clear()
    try:
        response = start_tournament(
            DetectorTournamentStartRequest(
                number_of_scenarios=1,
                manipulation_types=["quote_stuffing"],
                detector_set=["quote_stuffing"],
                execution_mode="nebius",
            ),
            store=LocalStore(tmp_path),
            repo_root=Path(__file__).resolve().parents[2],
        )

        assert response.status == "completed"
        assert response.execution_mode == "local_mock"
        assert response.fallback_reason
    finally:
        get_settings.cache_clear()


def test_detector_tournament_nebius_submit_renders_object_storage_env(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake_run(argv: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout='{"job_id":"job-test"}', stderr="")

    monkeypatch.setenv(
        "NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE",
        "nebius ai job create --image {image} {object_storage_env_args}",
    )
    monkeypatch.setenv("NEBIUS_OBJECT_STORAGE_ACCESS_KEY_ID", "test-access")
    monkeypatch.setenv("NEBIUS_OBJECT_STORAGE_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setattr("app.nebius.detector_tournament.subprocess.run", fake_run)
    get_settings.cache_clear()
    try:
        response = start_tournament(
            DetectorTournamentStartRequest(
                number_of_scenarios=1,
                manipulation_types=["spoofing"],
                detector_set=["spoofing_like"],
                execution_mode="nebius",
            ),
            store=LocalStore(tmp_path),
            repo_root=Path(__file__).resolve().parents[2],
        )

        assert response.status == "queued"
        assert "AWS_ACCESS_KEY_ID=test-access" in captured["argv"]
        assert "AWS_SECRET_ACCESS_KEY=test-secret" in captured["argv"]
    finally:
        get_settings.cache_clear()


def test_detector_tournament_api_facade_round_trip(tmp_path: Path) -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(store=LocalStore(tmp_path))))
    response = start_detector_tournament(
        DetectorTournamentStartRequest(
            number_of_scenarios=1,
            manipulation_types=["layering"],
            detector_set=["layering_like"],
            execution_mode="local_mock",
        ),
        request,
        BackgroundTasks(),
    )
    loaded = read_detector_tournament(response.tournament_id, request)

    assert loaded.tournament_id == response.tournament_id
    assert loaded.status == "completed"
    assert loaded.execution_mode == "local_mock"
