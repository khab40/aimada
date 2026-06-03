import asyncio
from pathlib import Path
from types import SimpleNamespace

from app.api.routes_experiments import (
    AttackExperimentRequest,
    BenchmarkRunRequest,
    launch_attack_experiment,
    reports_summary,
    run_benchmark_experiment,
    save_attack_experiment,
)
from app.arena.engine import SimulationEngine
from app.storage.local_store import LocalStore


def _request(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                store=LocalStore(tmp_path),
                simulation=SimulationEngine(store=LocalStore(tmp_path)),
            )
        )
    )


def _attack_payload() -> AttackExperimentRequest:
    return AttackExperimentRequest(
        cancel_style="instant",
        distance_from_mid_bps=12,
        lifetime_seconds=5,
        noise_cover="low",
        predicted_detection_risk=0.81,
        scenario_type="quote stuffing",
        wall_size_multiplier=8,
    )


def test_save_attack_experiment_persists_jsonl(tmp_path: Path) -> None:
    request = _request(tmp_path)

    saved = save_attack_experiment(_attack_payload(), request)
    rows = request.app.state.store.read_jsonl("experiments/attack_experiments.jsonl")

    assert saved.id.startswith("EXP-")
    assert rows
    assert rows[0]["id"] == saved.id


def test_launch_attack_experiment_starts_arena_and_records_launch(tmp_path: Path) -> None:
    async def run() -> None:
        request = _request(tmp_path)

        launched = await launch_attack_experiment(_attack_payload(), request)
        launches = request.app.state.store.read_jsonl("experiments/attack_launches.jsonl")
        attacks = request.app.state.store.read_jsonl("attacks/attacks.jsonl")

        assert launched.experiment_id.startswith("EXP-")
        assert launched.launch_endpoint == "/api/scenarios/quote-stuffing"
        assert launched.attack.scenario_family == "quote_stuffing"
        assert launches
        assert attacks

    asyncio.run(run())


def test_run_benchmark_experiment_persists_run_and_report_summary(tmp_path: Path) -> None:
    request = _request(tmp_path)

    run = run_benchmark_experiment(
        BenchmarkRunRequest(
            detectors="tuned",
            market_regime="volatile",
            runs=100,
            scenarios=["spoofing", "quote stuffing"],
        ),
        request,
    )
    summary = reports_summary(request)

    assert run.id.startswith("JOB-")
    assert run.results
    assert summary.benchmark_runs
    assert summary.significant_events
