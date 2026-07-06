from pathlib import Path
from types import SimpleNamespace

from fastapi import BackgroundTasks

from app.api.routes_nebius import read_detector_tournament, start_detector_tournament
from app.nebius.detector_tournament import DetectorTournamentStartRequest, get_tournament, start_tournament
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
    assert response.artifacts["metrics"].endswith("metrics.csv")
    assert loaded is not None
    assert loaded.tournament_id == response.tournament_id


def test_detector_tournament_nebius_mode_falls_back_without_submit_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE", raising=False)
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
    assert loaded.status == "queued"
