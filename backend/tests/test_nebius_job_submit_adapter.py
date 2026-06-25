import subprocess
from pathlib import Path
from typing import Any

from app.config import Settings
from app.experiments.models import Experiment, utc_now
from app.experiments.nebius_orchestrator import (
    NebiusExperimentOrchestrator,
    _parse_job_id,
)
from app.experiments.repository import ExperimentRepository
from app.storage.local_store import LocalStore


def test_submit_without_template_stays_pending(tmp_path: Path) -> None:
    repository = _repository_with_experiment(tmp_path)
    orchestrator = NebiusExperimentOrchestrator(repository, Settings(_env_file=None))

    job = orchestrator.submit("EXP-SUBMIT")

    assert job is not None
    assert job.status == "real_nebius_pending"
    assert job.artifact_paths["nebius_job_config"].endswith("nebius_job_config.rendered.yaml")


def test_submit_with_template_persists_queued_job(monkeypatch: Any, tmp_path: Path) -> None:
    repository = _repository_with_experiment(tmp_path)
    captured: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout='{"job_id":"job-abc123","status":"queued"}',
            stderr="",
        )

    monkeypatch.setattr("app.experiments.nebius_orchestrator.subprocess.run", fake_run)
    settings = Settings(
        _env_file=None,
        NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE=(
            "nebius ai job create --config {config_path} --image {image} "
            "--output {output_dir} --label experiment={experiment_id}"
        ),
        NEBIUS_JOB_IMAGE="ghcr.io/acme/aimada-jobs:test",
    )
    orchestrator = NebiusExperimentOrchestrator(repository, settings)

    job = orchestrator.submit("EXP-SUBMIT")

    assert job is not None
    assert job.status == "queued"
    assert job.job_id == "job-abc123"
    assert "--config" in captured["argv"]
    assert str(tmp_path / "experiments" / "EXP-SUBMIT" / "nebius_job_config.rendered.yaml") in captured["argv"]
    assert "--image" in captured["argv"]
    assert "ghcr.io/acme/aimada-jobs:test" in captured["argv"]
    assert job.artifact_paths["submit_stdout"].endswith("nebius_submit_stdout.txt")
    assert "job-abc123" in Path(job.artifact_paths["submit_stdout"]).read_text(encoding="utf-8")
    assert repository.get("EXP-SUBMIT").smart_batch_id == "job-abc123"  # type: ignore[union-attr]


def test_submit_with_template_persists_failed_job_and_redacts(monkeypatch: Any, tmp_path: Path) -> None:
    repository = _repository_with_experiment(tmp_path)

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv,
            2,
            stdout="",
            stderr="Authorization=secret-token token=another-secret",
        )

    monkeypatch.setattr("app.experiments.nebius_orchestrator.subprocess.run", fake_run)
    settings = Settings(
        _env_file=None,
        NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE="nebius ai job create --config {config_path}",
    )
    orchestrator = NebiusExperimentOrchestrator(repository, settings)

    job = orchestrator.submit("EXP-SUBMIT")

    assert job is not None
    assert job.status == "failed"
    assert "secret-token" not in job.message
    assert "another-secret" not in job.message
    error_text = Path(job.artifact_paths["submit_error"]).read_text(encoding="utf-8")
    assert "secret-token" not in error_text
    assert "another-secret" not in error_text
    assert "[REDACTED]" in error_text
    assert repository.get("EXP-SUBMIT").status == "failed"  # type: ignore[union-attr]


def test_refresh_does_not_complete_without_artifact_confirmation(monkeypatch: Any, tmp_path: Path) -> None:
    repository = _repository_with_experiment(tmp_path)

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if argv[0] == "submit-job":
            return subprocess.CompletedProcess(argv, 0, stdout="job_id: job-refresh", stderr="")
        return subprocess.CompletedProcess(argv, 0, stdout='{"status":"completed"}', stderr="")

    monkeypatch.setattr("app.experiments.nebius_orchestrator.subprocess.run", fake_run)
    settings = Settings(
        _env_file=None,
        NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE="submit-job {config_path}",
        NEBIUS_JOB_STATUS_COMMAND_TEMPLATE="status-job {experiment_id}",
    )
    orchestrator = NebiusExperimentOrchestrator(repository, settings)

    submitted = orchestrator.submit("EXP-SUBMIT")
    refreshed = orchestrator.refresh("EXP-SUBMIT")

    assert submitted is not None
    assert submitted.status == "queued"
    assert refreshed is not None
    assert refreshed[0].status == "running"
    assert "artifact collection is not confirmed" in refreshed[0].message


def test_parse_job_id_from_json_and_text() -> None:
    assert _parse_job_id('{"id":"job-json"}') == "job-json"
    assert _parse_job_id('{"metadata":{"jobId":"job-nested"}}') == "job-nested"
    assert _parse_job_id("created job id: job-text-123") == "job-text-123"
    assert _parse_job_id("submitted NEB-ABC123") == "NEB-ABC123"


def _repository_with_experiment(tmp_path: Path) -> ExperimentRepository:
    repository = ExperimentRepository(LocalStore(tmp_path))
    now = utc_now()
    repository.save(
        Experiment(
            id="EXP-SUBMIT",
            name="Submit adapter test",
            status="manifest_generated",
            attack_count=4,
            batch_size=2,
            scenarios=["normal_market", "spoofing"],
            seed=42,
            nebius_mode="real_nebius_pending",
            artifact_dir=str(tmp_path / "experiments" / "EXP-SUBMIT"),
            created_at=now,
            updated_at=now,
        )
    )
    return repository
