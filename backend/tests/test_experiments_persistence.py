import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from app.api.routes_experiments import (
    AttackExperimentRequest,
    BenchmarkRunRequest,
    create_experiment,
    delete_experiment,
    generate_experiment_attack_manifest,
    get_experiment,
    launch_attack_experiment,
    list_experiments,
    reports_summary,
    router,
    run_benchmark_experiment,
    run_experiment_local_batch,
    save_attack_experiment,
)
from app.arena.engine import SimulationEngine
from app.experiments.models import ExperimentCreateRequest
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
        history = request.app.state.store.read_jsonl("history/artifacts.jsonl")

        assert launched.experiment_id.startswith("EXP-")
        assert launched.launch_endpoint == "/api/scenarios/quote-stuffing"
        assert launched.attack.scenario_family == "quote_stuffing"
        assert launches
        assert attacks
        assert any(row["kind"] == "attack" for row in history)
        assert any(row["kind"] == "run" for row in history)

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
    assert summary.history_artifacts


def test_managed_experiment_create_list_get_delete(tmp_path: Path) -> None:
    request = _request(tmp_path)

    created = create_experiment(
        ExperimentCreateRequest(
            name="Phase 4.5 smoke",
            attack_count=12,
            batch_size=4,
            scenarios=["spoofing", "layering"],
            seed=7,
            nebius_mode="local_parallel_batch",
        ),
        request,
    )
    manifest = tmp_path / "experiments" / created.id / "experiment.json"

    assert created.id.startswith("EXP-")
    assert created.status == "manifest_generated"
    assert created.smart_batch_id is None
    assert created.attack_count == 12
    assert created.batch_size == 4
    assert created.scenarios == ["spoofing", "layering"]
    assert created.artifact_paths["manifest"] == str(manifest)
    assert manifest.exists()

    listed = list_experiments(request)
    fetched = get_experiment(created.id, request)
    summary = reports_summary(request)

    assert [experiment.id for experiment in listed] == [created.id]
    assert fetched.id == created.id
    assert any(row["id"] == created.id for row in summary.experiments)
    assert any(row["run_id"] == created.id for row in summary.history_artifacts)

    deleted = delete_experiment(created.id, request)

    assert deleted.deleted is True
    assert deleted.id == created.id
    assert not manifest.exists()
    assert list_experiments(request) == []


def test_attack_manifest_generation_is_deterministic_for_same_seed(tmp_path: Path) -> None:
    request = _request(tmp_path)
    experiment = create_experiment(
        ExperimentCreateRequest(
            name="Deterministic manifest",
            attack_count=10,
            batch_size=5,
            scenarios=["normal_market", "spoofing", "quote_stuffing"],
            seed=1234,
            nebius_mode="mock",
        ),
        request,
    )

    first_manifest = generate_experiment_attack_manifest(experiment.id, request)
    first_rows = _read_jsonl(Path(first_manifest.path))
    second_manifest = generate_experiment_attack_manifest(experiment.id, request)
    second_rows = _read_jsonl(Path(second_manifest.path))

    assert first_rows == second_rows
    assert first_manifest.attack_count == 10
    assert second_manifest.attack_count == 10


def test_attack_manifest_generation_respects_attack_count(tmp_path: Path) -> None:
    request = _request(tmp_path)
    for attack_count in [10, 100, 1000]:
        experiment = create_experiment(
            ExperimentCreateRequest(
                name=f"Count manifest {attack_count}",
                attack_count=attack_count,
                batch_size=20,
                scenarios=["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"],
                seed=99,
            ),
            request,
        )

        response = generate_experiment_attack_manifest(experiment.id, request)
        rows = _read_jsonl(Path(response.path))
        refreshed = get_experiment(experiment.id, request)

        assert response.attack_count == attack_count
        assert len(rows) == attack_count
        assert refreshed.status == "manifest_generated"
        assert refreshed.artifact_paths["attacks"] == response.path


def test_attack_manifest_expected_labels_are_correct(tmp_path: Path) -> None:
    request = _request(tmp_path)
    experiment = create_experiment(
        ExperimentCreateRequest(
            name="Labels manifest",
            attack_count=10,
            batch_size=5,
            scenarios=["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"],
            seed=7,
        ),
        request,
    )

    response = generate_experiment_attack_manifest(experiment.id, request)
    rows = _read_jsonl(Path(response.path))
    expected_families = {
        "normal_market": None,
        "spoofing": "spoofing_like",
        "layering": "layering_like",
        "quote_stuffing": "quote_stuffing",
        "pump_and_cancel": "liquidity_shock",
    }

    assert {row["scenario"] for row in rows} == set(expected_families)
    for row in rows:
        assert row["expected_has_attack"] is (row["scenario"] != "normal_market")
        assert row["expected_detector_family"] == expected_families[row["scenario"]]


def test_experiment_run_local_batch_generates_attacks_and_persists_job(tmp_path: Path) -> None:
    request = _request(tmp_path)
    experiment = create_experiment(
        ExperimentCreateRequest(
            name="Small local batch",
            attack_count=3,
            batch_size=2,
            scenarios=["normal_market", "spoofing"],
            seed=21,
        ),
        request,
    )

    response = run_experiment_local_batch(experiment.id, request)
    refreshed = get_experiment(experiment.id, request)
    jobs = _read_jsonl(tmp_path / "experiments" / experiment.id / "jobs.jsonl")
    attacks = _read_jsonl(tmp_path / "experiments" / experiment.id / "attacks.jsonl")
    output_dir = tmp_path / "experiments" / experiment.id / "local-batch"

    assert response.status == "completed"
    assert response.runs == 3
    assert response.batch_size == 2
    assert response.scenarios == ["normal_market", "spoofing"]
    assert response.elapsed_seconds >= 0
    assert len(jobs) == 1
    assert jobs[0]["id"] == response.id
    assert jobs[0]["mode"] == "local_parallel_batch"
    assert len(attacks) == 3
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "detector_metrics.csv").exists()
    assert refreshed.status == "completed"
    assert refreshed.smart_batch_id == response.id
    assert refreshed.artifact_paths["jobs"] == str(tmp_path / "experiments" / experiment.id / "jobs.jsonl")
    assert refreshed.artifact_paths["local_batch_manifest"] == str(output_dir / "manifest.json")
    assert refreshed.metrics


def test_managed_experiment_routes_are_registered_on_experiment_api() -> None:
    routes = {(method, route.path) for route in router.routes for method in route.methods}

    assert ("POST", "/api/experiments") in routes
    assert ("GET", "/api/experiments") in routes
    assert ("POST", "/api/experiments/{experiment_id}/generate-manifest") in routes
    assert ("POST", "/api/experiments/{experiment_id}/run-local-batch") in routes
    assert ("GET", "/api/experiments/{experiment_id}") in routes
    assert ("DELETE", "/api/experiments/{experiment_id}") in routes


def test_simulation_ticks_are_persisted_for_history_replay(tmp_path: Path) -> None:
    request = _request(tmp_path)

    request.app.state.simulation.step()
    request.app.state.simulation.step()
    summary = reports_summary(request)

    assert len(summary.history_ticks) == 2
    assert summary.history_ticks[-1]["kind"] == "exchange_tick"
    assert summary.history_ticks[-1]["payload"]["book"]["bids"]


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
