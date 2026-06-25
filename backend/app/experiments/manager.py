from pathlib import Path
from uuid import uuid4

from app.experiments.attack_manifest import AttackManifestResponse, generate_attack_manifest
from app.experiments.models import Experiment, ExperimentCreateRequest, ExperimentLocalBatchRunResponse, utc_now
from app.experiments.nebius_orchestrator import ExperimentJobRecord
from app.experiments.repository import ExperimentRepository
from app.nebius.smart_batch_runner import run_local_smart_batch
from app.storage.history import append_history_artifact


class ExperimentManager:
    def __init__(self, repository: ExperimentRepository) -> None:
        self.repository = repository

    def create(self, payload: ExperimentCreateRequest) -> Experiment:
        experiment_id = f"EXP-{uuid4().hex[:8].upper()}"
        created_at = utc_now()
        artifact_dir = self.repository.experiment_dir(experiment_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        experiment = Experiment(
            id=experiment_id,
            name=payload.name,
            status="manifest_generated",
            attack_count=payload.attack_count,
            batch_size=payload.batch_size,
            scenarios=payload.scenarios,
            seed=payload.seed,
            nebius_mode=payload.nebius_mode,
            artifact_dir=str(artifact_dir),
            artifact_paths=_artifact_paths(artifact_dir),
            metrics=[],
            created_at=created_at,
            updated_at=created_at,
        )
        saved = self.repository.save(experiment)
        append_history_artifact(
            self.repository.store,
            kind="run",
            payload=saved.model_dump(mode="json"),
            summary=f"Experiment manifest {saved.id} generated",
            created_at=saved.created_at,
            run_id=saved.id,
            source="experiment_manager",
            source_path=f"experiments/{saved.id}/experiment.json",
        )
        return saved

    def list(self) -> list[Experiment]:
        return self.repository.list()

    def get(self, experiment_id: str) -> Experiment | None:
        return self.repository.get(experiment_id)

    def generate_attack_manifest(self, experiment_id: str) -> AttackManifestResponse | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None
        artifact_dir = self.repository.experiment_dir(experiment.id)
        rows = generate_attack_manifest(experiment, artifact_dir)
        updated = experiment.model_copy(
            update={
                "status": "manifest_generated",
                "artifact_paths": {**experiment.artifact_paths, "attacks": str(artifact_dir / "attacks.jsonl")},
                "updated_at": utc_now(),
            }
        )
        self.repository.save(updated)
        append_history_artifact(
            self.repository.store,
            kind="artifact",
            payload={
                "experiment_id": updated.id,
                "attack_count": len(rows),
                "path": updated.artifact_paths["attacks"],
                "scenarios": updated.scenarios,
            },
            summary=f"Attack manifest generated for {updated.id}",
            created_at=updated.updated_at,
            run_id=updated.id,
            source="experiment_attack_manifest",
            source_path=f"experiments/{updated.id}/attacks.jsonl",
        )
        return AttackManifestResponse(
            experiment_id=updated.id,
            path=updated.artifact_paths["attacks"],
            attack_count=len(rows),
            scenarios=updated.scenarios,
            status=updated.status,
        )

    def run_local_batch(self, experiment_id: str) -> ExperimentLocalBatchRunResponse | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None

        artifact_dir = self.repository.experiment_dir(experiment.id)
        attacks_path = artifact_dir / "attacks.jsonl"
        if not attacks_path.exists():
            self.generate_attack_manifest(experiment.id)
            experiment = self.repository.get(experiment.id) or experiment

        output_dir = artifact_dir / "local-batch"
        local_batch_id = f"LOCAL-{uuid4().hex[:8].upper()}"
        created_at = utc_now()
        batch = run_local_smart_batch(
            repo_root=_repo_root(),
            output_dir=output_dir,
            runs=experiment.attack_count,
            batch_size=experiment.batch_size,
            scenarios=experiment.scenarios,
        )
        status = "completed" if batch.returncode == 0 else "failed"
        updated_at = utc_now()
        response = ExperimentLocalBatchRunResponse(
            id=local_batch_id,
            experiment_id=experiment.id,
            mode="local_parallel_batch",
            status=status,
            created_at=created_at,
            elapsed_seconds=batch.elapsed_seconds,
            runs=experiment.attack_count,
            batch_size=experiment.batch_size,
            scenarios=experiment.scenarios,
            artifact_paths=batch.artifact_paths,
            metrics=batch.metrics,
            error=None
            if status == "completed"
            else {
                "message": "local experiment batch failed",
                "returncode": batch.returncode,
                "stderr": batch.stderr[-2000:],
                "stdout": batch.stdout[-2000:],
            },
        )
        job = ExperimentJobRecord(
            job_id=local_batch_id,
            experiment_id=experiment.id,
            backend="local_parallel_batch",
            status=status,
            batch_start=0,
            batch_end=experiment.attack_count,
            attack_count=experiment.attack_count,
            created_at=created_at,
            updated_at=updated_at,
            message=f"Local parallel batch {status}",
            artifact_paths=batch.artifact_paths,
        )
        self.repository.store.append_jsonl(
            f"experiments/{experiment.id}/jobs.jsonl",
            job.model_dump(mode="json"),
        )
        updated = experiment.model_copy(
            update={
                "status": status,
                "smart_batch_id": local_batch_id,
                "artifact_paths": {
                    **experiment.artifact_paths,
                    "attacks": str(attacks_path),
                    "jobs": str(artifact_dir / "jobs.jsonl"),
                    **{f"local_batch_{key}": value for key, value in batch.artifact_paths.items()},
                },
                "metrics": batch.metrics,
                "updated_at": updated_at,
            }
        )
        self.repository.save(updated)
        append_history_artifact(
            self.repository.store,
            kind="run",
            payload=response.model_dump(mode="json"),
            summary=f"Experiment local batch {local_batch_id} {status}",
            created_at=response.created_at,
            run_id=local_batch_id,
            source="experiment_local_batch",
            source_path=f"experiments/{experiment.id}/jobs.jsonl",
        )
        return response

    def delete(self, experiment_id: str) -> bool:
        return self.repository.delete(experiment_id)


def _artifact_paths(artifact_dir: Path) -> dict[str, str]:
    return {
        "manifest": str(artifact_dir / "experiment.json"),
        "attacks": str(artifact_dir / "attacks.jsonl"),
        "order_book_event_logs": str(artifact_dir / "order_book_events.jsonl"),
        "trades": str(artifact_dir / "trades.jsonl"),
        "attack_labels": str(artifact_dir / "attack_labels.jsonl"),
        "blue_team_alerts": str(artifact_dir / "blue_team_alerts.jsonl"),
        "detector_metrics": str(artifact_dir / "detector_metrics.csv"),
        "generated_report": str(artifact_dir / "generated_report.md"),
    }


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [here.parents[3], here.parents[2], Path.cwd()]
    for candidate in candidates:
        if (candidate / "serverless" / "jobs" / "run_batch_experiments.py").exists():
            return candidate
    return here.parents[3]
