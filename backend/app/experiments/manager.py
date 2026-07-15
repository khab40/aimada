from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.config import get_settings
from app.experiments.aggregator import AggregationResult, ExperimentSummary, LeaderboardRow, aggregate_experiment, load_leaderboard, load_summary, report_path
from app.experiments.artifact_normalizer import ArtifactNormalizationResponse, normalize_local_batch_artifacts
from app.experiments.attack_manifest import AttackManifestResponse, generate_attack_manifest
from app.experiments.investigation_pipeline import (
    InvestigationRecord,
    InvestigationRunResponse,
    list_investigations,
    run_batch_investigations,
)
from app.experiments.models import Experiment, ExperimentCreateRequest, ExperimentLocalBatchRunResponse, utc_now
from app.experiments.nebius_orchestrator import ExperimentJobRecord
from app.experiments.repository import ExperimentRepository
from app.nebius.client import NebiusClient
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
            max_workers=get_settings().arena_local_batch_max_workers,
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
        normalized = None
        if status == "completed":
            normalized = normalize_local_batch_artifacts(experiment.id, artifact_dir)
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
                    **(normalized.artifact_paths if normalized is not None else {}),
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

    def normalize_artifacts(self, experiment_id: str) -> ArtifactNormalizationResponse | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None
        artifact_dir = self.repository.experiment_dir(experiment.id)
        normalized = normalize_local_batch_artifacts(experiment.id, artifact_dir)
        updated = experiment.model_copy(
            update={
                "artifact_paths": {**experiment.artifact_paths, **normalized.artifact_paths},
                "updated_at": utc_now(),
            }
        )
        self.repository.save(updated)
        append_history_artifact(
            self.repository.store,
            kind="artifact",
            payload=normalized.model_dump(mode="json"),
            summary=f"Experiment artifacts normalized for {experiment.id}",
            created_at=updated.updated_at,
            run_id=experiment.id,
            source="experiment_artifact_normalizer",
            source_path=f"experiments/{experiment.id}/artifact_index.json",
        )
        return normalized

    def run_investigations(
        self,
        experiment_id: str,
        *,
        client: NebiusClient,
        top_k: int = 7,
    ) -> InvestigationRunResponse | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None
        artifact_dir = self.repository.experiment_dir(experiment.id)
        response = run_batch_investigations(
            experiment_id=experiment.id,
            artifact_dir=artifact_dir,
            client=client,
            top_k=top_k,
        )
        summary_metric = {
            "investigation_count": response.investigation_count,
            "investigation_mode": response.investigation_mode,
            "endpoint_avg_latency_seconds": response.endpoint_avg_latency_seconds,
        }
        updated_metrics = [
            metric for metric in experiment.metrics if metric.get("kind") != "investigation_summary"
        ]
        updated_metrics.append({"kind": "investigation_summary", **summary_metric})
        updated = experiment.model_copy(
            update={
                "metrics": updated_metrics,
                "artifact_paths": {
                    **experiment.artifact_paths,
                    "investigations": str(artifact_dir / "investigations"),
                },
                "updated_at": utc_now(),
            }
        )
        self.repository.save(updated)
        append_history_artifact(
            self.repository.store,
            kind="ai_explanation",
            payload=response.model_dump(mode="json"),
            summary=f"{response.investigation_count} experiment investigation reports generated",
            created_at=updated.updated_at,
            run_id=experiment.id,
            source="experiment_investigation_pipeline",
            source_path=f"experiments/{experiment.id}/investigations",
        )
        return response

    def list_investigations(self, experiment_id: str) -> list[InvestigationRecord] | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None
        return list_investigations(self.repository.experiment_dir(experiment.id))

    def aggregate(self, experiment_id: str) -> AggregationResult | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None
        artifact_dir = self.repository.experiment_dir(experiment.id)
        result = aggregate_experiment(experiment.id, artifact_dir)
        updated = experiment.model_copy(
            update={
                "artifact_paths": {**experiment.artifact_paths, **result.summary.artifact_paths},
                "updated_at": utc_now(),
            }
        )
        self.repository.save(updated)
        append_history_artifact(
            self.repository.store,
            kind="artifact",
            payload=result.model_dump(mode="json"),
            summary=f"Experiment aggregate report generated for {experiment.id}",
            created_at=updated.updated_at,
            run_id=experiment.id,
            source="experiment_aggregator",
            source_path=f"experiments/{experiment.id}/experiment_summary.json",
        )
        return result

    def summary(self, experiment_id: str) -> ExperimentSummary | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None
        return load_summary(self.repository.experiment_dir(experiment.id))

    def leaderboard(self, experiment_id: str) -> list[LeaderboardRow] | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None
        return load_leaderboard(self.repository.experiment_dir(experiment.id))

    def report_path(self, experiment_id: str) -> Path | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None
        return report_path(self.repository.experiment_dir(experiment.id))

    def delete(self, experiment_id: str) -> bool:
        return self.repository.delete(experiment_id)


def _artifact_paths(artifact_dir: Path) -> dict[str, str]:
    return {
        "manifest": str(artifact_dir / "experiment.json"),
        "attacks": str(artifact_dir / "attacks.jsonl"),
        "order_book_event_logs": str(artifact_dir / "order_book_events.jsonl"),
        "attack_labels": str(artifact_dir / "attack_labels.jsonl"),
        "blue_team_alerts": str(artifact_dir / "blue_team_alerts.jsonl"),
        "generated_report": str(artifact_dir / "generated_report.md"),
    }


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [here.parents[3], here.parents[2], Path.cwd()]
    for candidate in candidates:
        if (candidate / "serverless" / "jobs" / "run_batch_experiments.py").exists():
            return candidate
    return here.parents[3]
