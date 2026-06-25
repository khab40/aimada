import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from app.api.routes_experiments import (
    AttackExperimentRequest,
    BenchmarkRunRequest,
    aggregate_experiment_outputs,
    create_experiment,
    delete_experiment,
    generate_experiment_attack_manifest,
    get_experiment,
    get_experiment_leaderboard,
    get_experiment_report,
    get_experiment_summary,
    launch_attack_experiment,
    list_experiment_investigations,
    list_experiments,
    normalize_experiment_artifacts,
    reports_summary,
    router,
    run_benchmark_experiment,
    run_experiment_investigations,
    run_experiment_local_batch,
    save_attack_experiment,
    list_experiment_jobs,
    refresh_experiment_jobs,
    submit_experiment_nebius,
)
from app.api.routes_nebius import observatory
from app.arena.engine import SimulationEngine
from app.experiments.manager import ExperimentManager
from app.experiments.models import ExperimentCreateRequest
from app.experiments.repository import ExperimentRepository
from app.nebius.client import InvestigationReportRequest, InvestigationReportResponse
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
    assert jobs[0]["job_id"] == response.id
    assert jobs[0]["backend"] == "local_parallel_batch"
    assert jobs[0]["status"] == "completed"
    assert len(attacks) == 3
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "detector_metrics.csv").exists()
    assert refreshed.status == "completed"
    assert refreshed.smart_batch_id == response.id
    assert refreshed.artifact_paths["jobs"] == str(tmp_path / "experiments" / experiment.id / "jobs.jsonl")
    assert refreshed.artifact_paths["local_batch_manifest"] == str(output_dir / "manifest.json")
    assert refreshed.metrics


def test_normalize_artifacts_copies_fake_local_batch_outputs(tmp_path: Path) -> None:
    request = _request(tmp_path)
    experiment = create_experiment(
        ExperimentCreateRequest(
            name="Normalize fake batch",
            attack_count=3,
            batch_size=2,
            scenarios=["normal_market", "spoofing"],
            seed=51,
        ),
        request,
    )
    local_batch_dir = tmp_path / "experiments" / experiment.id / "local-batch"
    local_batch_dir.mkdir(parents=True)
    fake_files = {
        "order_book_events.jsonl": '{"event":"book"}\n',
        "trades.jsonl": '{"trade":"t1"}\n',
        "attack_labels.jsonl": '{"label":"spoofing"}\n',
        "blue_team_alerts.jsonl": '{"alert":"a1"}\n',
        "detector_metrics.csv": "scenario,runs,alerts,precision,recall,f1,avg_detection_latency_ms\nspoofing,1,1,1,1,1,500\n",
        "generated_report.md": "# Report\n",
        "manifest.json": '{"runs":3}\n',
    }
    for name, content in fake_files.items():
        (local_batch_dir / name).write_text(content, encoding="utf-8")

    response = normalize_experiment_artifacts(experiment.id, request)
    refreshed = get_experiment(experiment.id, request)
    artifact_index = json.loads((tmp_path / "experiments" / experiment.id / "artifact_index.json").read_text(encoding="utf-8"))

    assert response.copied_count == 7
    assert response.missing == []
    assert (local_batch_dir / "order_book_events.jsonl").exists()
    assert (tmp_path / "experiments" / experiment.id / "events.jsonl").read_text(encoding="utf-8") == '{"event":"book"}\n'
    assert (tmp_path / "experiments" / experiment.id / "labels.jsonl").read_text(encoding="utf-8") == '{"label":"spoofing"}\n'
    assert (tmp_path / "experiments" / experiment.id / "alerts.jsonl").read_text(encoding="utf-8") == '{"alert":"a1"}\n'
    assert (tmp_path / "experiments" / experiment.id / "benchmark_report.md").read_text(encoding="utf-8") == "# Report\n"
    assert (tmp_path / "experiments" / experiment.id / "batch_manifest.json").read_text(encoding="utf-8") == '{"runs":3}\n'
    assert artifact_index["experiment_id"] == experiment.id
    assert {entry["key"] for entry in artifact_index["artifacts"]} == {
        "events",
        "trades",
        "labels",
        "alerts",
        "detector_metrics",
        "benchmark_report",
        "batch_manifest",
    }
    assert refreshed.artifact_paths["events"] == str(tmp_path / "experiments" / experiment.id / "events.jsonl")
    assert refreshed.artifact_paths["artifact_index"] == str(tmp_path / "experiments" / experiment.id / "artifact_index.json")


def test_run_investigations_uses_mocked_nebius_client_for_top_alerts(tmp_path: Path) -> None:
    request = _request(tmp_path)
    experiment = create_experiment(
        ExperimentCreateRequest(
            name="Investigate alerts",
            attack_count=3,
            batch_size=2,
            scenarios=["normal_market", "spoofing"],
            seed=61,
        ),
        request,
    )
    alerts_path = tmp_path / "experiments" / experiment.id / "alerts.jsonl"
    alerts_path.parent.mkdir(parents=True, exist_ok=True)
    alerts = [
        {"alert_id": "low", "run_id": "r1", "tick": 1, "scenario": "normal_market", "detector": "none", "confidence": 0.1},
        {"alert_id": "high", "run_id": "r2", "tick": 2, "scenario": "spoofing", "detector": "spoofing_like", "confidence": 0.93, "evidence": ["wall"]},
        {"alert_id": "mid", "run_id": "r3", "tick": 3, "scenario": "spoofing", "detector": "layering_like", "confidence": 0.72},
    ]
    alerts_path.write_text("\n".join(json.dumps(row) for row in alerts) + "\n", encoding="utf-8")
    client = _MockInvestigationClient()

    response = ExperimentManager(ExperimentRepository(request.app.state.store)).run_investigations(
        experiment.id,
        client=client,
        top_k=2,
    )
    listed = list_experiment_investigations(experiment.id, request)
    refreshed = get_experiment(experiment.id, request)

    assert response is not None
    assert response.investigation_count == 2
    assert response.investigation_mode == "mock"
    assert len(client.requests) == 2
    assert [request.alerts[0]["alert_id"] for request in client.requests] == ["high", "mid"]
    assert (tmp_path / "experiments" / experiment.id / "investigations" / "high.json").exists()
    assert (tmp_path / "experiments" / experiment.id / "investigations" / "high.md").exists()
    assert listed[0].alert_id == "high"
    investigation_metric = next(metric for metric in refreshed.metrics if metric.get("kind") == "investigation_summary")
    assert investigation_metric["investigation_count"] == 2
    assert investigation_metric["investigation_mode"] == "mock"
    assert "endpoint_avg_latency_seconds" in investigation_metric
    assert refreshed.artifact_paths["investigations"] == str(tmp_path / "experiments" / experiment.id / "investigations")


def test_aggregate_experiment_uses_sample_detector_metrics_csv(tmp_path: Path) -> None:
    request = _request(tmp_path)
    experiment = create_experiment(
        ExperimentCreateRequest(
            name="Aggregate sample metrics",
            attack_count=4,
            batch_size=2,
            scenarios=["normal_market", "spoofing"],
            seed=71,
        ),
        request,
    )
    artifact_dir = tmp_path / "experiments" / experiment.id
    (artifact_dir / "detector_metrics.csv").write_text(
        "\n".join(
            [
                "scenario,runs,alerts,precision,recall,f1,avg_detection_latency_ms",
                "normal_market,2,0,1.0,0.0,0.0,",
                "spoofing,2,2,0.75,0.5,0.6,450",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "alerts.jsonl").write_text(
        '{"alert_id":"a1","scenario":"spoofing","confidence":0.9}\n{"alert_id":"a2","scenario":"spoofing","confidence":0.7}\n',
        encoding="utf-8",
    )
    (artifact_dir / "labels.jsonl").write_text(
        '{"run_id":"r1","scenario":"normal_market","has_attack":false}\n'
        '{"run_id":"r2","scenario":"spoofing","has_attack":true}\n'
        '{"run_id":"r3","scenario":"spoofing","has_attack":true}\n',
        encoding="utf-8",
    )
    investigations_dir = artifact_dir / "investigations"
    investigations_dir.mkdir()
    (investigations_dir / "a1.json").write_text('{"alert_id":"a1"}\n', encoding="utf-8")

    aggregate = aggregate_experiment_outputs(experiment.id, request)
    summary = get_experiment_summary(experiment.id, request)
    leaderboard = get_experiment_leaderboard(experiment.id, request)
    report = get_experiment_report(experiment.id, request)
    refreshed = get_experiment(experiment.id, request)

    assert aggregate.summary.experiment_id == experiment.id
    assert summary.total_attacks == 2
    assert summary.total_alerts == 2
    assert summary.investigation_count == 1
    assert summary.failed_runs == 0
    assert summary.precision_by_scenario["spoofing"] == 0.75
    assert summary.recall_by_scenario["spoofing"] == 0.5
    assert summary.f1_by_scenario["spoofing"] == 0.6
    assert summary.avg_detection_latency_ms == 450
    assert leaderboard[1].scenario == "spoofing"
    assert leaderboard[1].alert_count == 2
    assert "Experiment Benchmark Report" in report.body.decode("utf-8")
    assert (artifact_dir / "experiment_summary.json").exists()
    assert (artifact_dir / "leaderboard.json").exists()
    assert (artifact_dir / "benchmark_report.md").exists()
    assert refreshed.artifact_paths["experiment_summary"] == str(artifact_dir / "experiment_summary.json")
    assert refreshed.artifact_paths["leaderboard"] == str(artifact_dir / "leaderboard.json")


def test_submit_nebius_without_real_config_persists_pending_job(tmp_path: Path) -> None:
    request = _request(tmp_path)
    experiment = create_experiment(
        ExperimentCreateRequest(
            name="Pending Nebius",
            attack_count=3,
            batch_size=2,
            scenarios=["normal_market", "spoofing"],
            seed=31,
            nebius_mode="real_nebius_pending",
        ),
        request,
    )

    job = submit_experiment_nebius(experiment.id, request)
    jobs = list_experiment_jobs(experiment.id, request)
    refreshed_jobs = refresh_experiment_jobs(experiment.id, request)
    refreshed_experiment = get_experiment(experiment.id, request)
    observatory_response = observatory(request)

    assert job.backend == "nebius_serverless_job"
    assert job.status == "real_nebius_pending"
    assert job.attack_count == 3
    assert job.batch_start == 0
    assert job.batch_end == 3
    assert "not configured" in job.message
    assert (tmp_path / "experiments" / experiment.id / "attacks.jsonl").exists()
    assert jobs == [job]
    assert refreshed_jobs[0].status == "real_nebius_pending"
    assert refreshed_experiment.status == "submitted"
    assert refreshed_experiment.smart_batch_id == job.job_id
    assert observatory_response.experiment_jobs is not None
    assert observatory_response.experiment_jobs["status_counts"]["real_nebius_pending"] == 1


def test_managed_experiment_routes_are_registered_on_experiment_api() -> None:
    routes = {(method, route.path) for route in router.routes for method in route.methods}

    assert ("POST", "/api/experiments") in routes
    assert ("GET", "/api/experiments") in routes
    assert ("POST", "/api/experiments/{experiment_id}/generate-manifest") in routes
    assert ("POST", "/api/experiments/{experiment_id}/run-local-batch") in routes
    assert ("POST", "/api/experiments/{experiment_id}/normalize-artifacts") in routes
    assert ("POST", "/api/experiments/{experiment_id}/run-investigations") in routes
    assert ("GET", "/api/experiments/{experiment_id}/investigations") in routes
    assert ("POST", "/api/experiments/{experiment_id}/aggregate") in routes
    assert ("GET", "/api/experiments/{experiment_id}/summary") in routes
    assert ("GET", "/api/experiments/{experiment_id}/leaderboard") in routes
    assert ("GET", "/api/experiments/{experiment_id}/report") in routes
    assert ("POST", "/api/experiments/{experiment_id}/submit-nebius") in routes
    assert ("GET", "/api/experiments/{experiment_id}/jobs") in routes
    assert ("POST", "/api/experiments/{experiment_id}/refresh-jobs") in routes
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


class _MockInvestigationClient:
    def __init__(self) -> None:
        self.requests: list[InvestigationReportRequest] = []

    def investigation_report(self, request: InvestigationReportRequest) -> InvestigationReportResponse:
        self.requests.append(request)
        scenario = str(request.scenario_trace.get("scenario") or "unknown")
        return InvestigationReportResponse(
            mode="mock",
            endpoint="mock test client",
            title=f"Investigation {scenario}",
            summary="Mocked investigation report.",
            timeline=["alert selected"],
            detector_findings=["confidence reviewed"],
            limitations=["test only"],
            recommended_next_steps=["archive report"],
        )
