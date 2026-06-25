from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.config import Settings
from app.experiments.attack_manifest import generate_attack_manifest
from app.experiments.models import Experiment, utc_now
from app.experiments.repository import ExperimentRepository


JobBackend = Literal["local_parallel_batch", "nebius_serverless_job"]
JobStatus = Literal["queued", "running", "completed", "failed", "real_nebius_pending"]


class ExperimentJobRecord(BaseModel):
    job_id: str
    experiment_id: str
    backend: JobBackend
    status: JobStatus
    batch_start: int
    batch_end: int
    attack_count: int
    created_at: str
    updated_at: str
    message: str
    artifact_paths: dict[str, str] = Field(default_factory=dict)


class NebiusExperimentOrchestrator:
    def __init__(self, repository: ExperimentRepository, settings: Settings | None = None) -> None:
        self.repository = repository
        self.settings = settings

    def submit(self, experiment_id: str) -> ExperimentJobRecord | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None

        artifact_dir = self.repository.experiment_dir(experiment.id)
        attacks_path = artifact_dir / "attacks.jsonl"
        if not attacks_path.exists():
            generate_attack_manifest(experiment, artifact_dir)

        now = utc_now()
        job = ExperimentJobRecord(
            job_id=f"NEB-PENDING-{uuid4().hex[:8].upper()}",
            experiment_id=experiment.id,
            backend="nebius_serverless_job",
            status="real_nebius_pending",
            batch_start=0,
            batch_end=experiment.attack_count,
            attack_count=experiment.attack_count,
            created_at=now,
            updated_at=now,
            message=self._pending_message(),
            artifact_paths={
                "experiment": str(artifact_dir / "experiment.json"),
                "attacks": str(attacks_path),
                "jobs": str(artifact_dir / "jobs.jsonl"),
            },
        )
        self._append_job(job)
        updated = experiment.model_copy(
            update={
                "status": "submitted",
                "smart_batch_id": job.job_id,
                "artifact_paths": {
                    **experiment.artifact_paths,
                    "attacks": str(attacks_path),
                    "jobs": str(artifact_dir / "jobs.jsonl"),
                },
                "updated_at": now,
            }
        )
        self.repository.save(updated)
        return job

    def list_jobs(self, experiment_id: str) -> list[ExperimentJobRecord] | None:
        if self.repository.get(experiment_id) is None:
            return None
        return self._read_jobs(experiment_id)

    def refresh(self, experiment_id: str) -> list[ExperimentJobRecord] | None:
        if self.repository.get(experiment_id) is None:
            return None
        jobs = self._read_jobs(experiment_id)
        now = utc_now()
        refreshed: list[ExperimentJobRecord] = []
        for job in jobs:
            if job.backend == "nebius_serverless_job" and job.status == "real_nebius_pending":
                refreshed.append(job.model_copy(update={"updated_at": now, "message": self._pending_message()}))
            else:
                refreshed.append(job)
        self._write_jobs(experiment_id, refreshed)
        return refreshed

    def _pending_message(self) -> str:
        if self._has_nebius_credentials():
            return (
                "Real Nebius credentials are present, but Nebius Serverless Job submission is not implemented. "
                "Add the real SDK/CLI call only in backend/app/experiments/nebius_orchestrator.py."
            )
        return (
            "Real Nebius Serverless Job submission is not configured. Configure Nebius credentials and add the "
            "real SDK/CLI call only in backend/app/experiments/nebius_orchestrator.py; this job was not submitted "
            "to cloud."
        )

    def _has_nebius_credentials(self) -> bool:
        return bool(self.settings and self.settings.nebius_api_key and self.settings.nebius_tenant_id)

    def _append_job(self, job: ExperimentJobRecord) -> None:
        self.repository.store.append_jsonl(
            self._relative_jobs_path(job.experiment_id),
            job.model_dump(mode="json"),
        )

    def _read_jobs(self, experiment_id: str) -> list[ExperimentJobRecord]:
        rows = self.repository.store.read_jsonl(self._relative_jobs_path(experiment_id), limit=None)
        jobs: list[ExperimentJobRecord] = []
        for row in rows:
            try:
                jobs.append(ExperimentJobRecord.model_validate(row))
            except ValueError:
                continue
        return jobs

    def _write_jobs(self, experiment_id: str, jobs: list[ExperimentJobRecord]) -> Path:
        path = self.repository.store.output_dir / self._relative_jobs_path(experiment_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(job.model_dump_json() for job in jobs)
        path.write_text(f"{content}\n" if content else "", encoding="utf-8")
        return path

    def _relative_jobs_path(self, experiment_id: str) -> str:
        return f"experiments/{experiment_id}/jobs.jsonl"


def summarize_experiment_jobs(output_dir: Path) -> dict[str, Any] | None:
    jobs: list[dict[str, Any]] = []
    for jobs_path in sorted((output_dir / "experiments").glob("*/jobs.jsonl")):
        for line in jobs_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                job = ExperimentJobRecord.model_validate_json(line)
            except ValueError:
                continue
            jobs.append(job.model_dump(mode="json"))
    if not jobs:
        return None
    status_counts: dict[str, int] = {}
    backend_counts: dict[str, int] = {}
    for job in jobs:
        status_counts[str(job["status"])] = status_counts.get(str(job["status"]), 0) + 1
        backend_counts[str(job["backend"])] = backend_counts.get(str(job["backend"]), 0) + 1
    return {
        "total_jobs": len(jobs),
        "status_counts": status_counts,
        "backend_counts": backend_counts,
        "latest_jobs": jobs[-5:],
    }
