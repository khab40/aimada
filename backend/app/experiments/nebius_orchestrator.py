import importlib.util
import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.config import Settings
from app.experiments.artifact_normalizer import (
    ARTIFACT_MAPPINGS,
    ArtifactNormalizationResponse,
    normalize_batch_artifacts,
)
from app.experiments.attack_manifest import generate_attack_manifest
from app.experiments.models import Experiment, utc_now
from app.experiments.repository import ExperimentRepository


JobBackend = Literal["local_parallel_batch", "nebius_serverless_job"]
JobStatus = Literal["queued", "running", "completed", "failed", "real_nebius_pending"]
RenderJobConfig = Callable[..., Path]


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


class NebiusArtifactCollectionResponse(BaseModel):
    experiment_id: str
    status: Literal["collected", "cloud_artifacts_pending"]
    source_dir: str | None = None
    artifact_dir: str
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    copied_count: int = 0
    missing: list[str] = Field(default_factory=list)
    message: str


class NebiusJobConfigRenderResponse(BaseModel):
    experiment_id: str
    path: str
    image: str
    output_dir: str


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
        rendered_config_path = self._render_job_config(experiment, artifact_dir)
        base_artifact_paths = {
            "experiment": str(artifact_dir / "experiment.json"),
            "attacks": str(attacks_path),
            "jobs": str(artifact_dir / "jobs.jsonl"),
            "nebius_job_config": str(rendered_config_path),
        }

        now = utc_now()
        submit_template = self._setting("nebius_job_submit_command_template")
        if submit_template:
            job = self._submit_with_command(
                experiment=experiment,
                artifact_dir=artifact_dir,
                rendered_config_path=rendered_config_path,
                base_artifact_paths=base_artifact_paths,
                submit_template=submit_template,
                now=now,
            )
        else:
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
                artifact_paths=base_artifact_paths,
            )
        self._append_job(job)
        updated = experiment.model_copy(
            update={
                "status": "failed" if job.status == "failed" else "submitted",
                "smart_batch_id": job.job_id,
                "artifact_paths": {
                    **experiment.artifact_paths,
                    **base_artifact_paths,
                    **job.artifact_paths,
                },
                "updated_at": now,
            }
        )
        self.repository.save(updated)
        return job

    def _submit_with_command(
        self,
        *,
        experiment: Experiment,
        artifact_dir: Path,
        rendered_config_path: Path,
        base_artifact_paths: dict[str, str],
        submit_template: str,
        now: str,
    ) -> ExperimentJobRecord:
        context = self._command_context(experiment=experiment, rendered_config_path=rendered_config_path)
        try:
            result = self._run_template_command(submit_template, context)
            job_id = _parse_job_id(result.stdout) or f"NEB-SUBMITTED-{uuid4().hex[:8].upper()}"
            submit_stdout_path = artifact_dir / "nebius_submit_stdout.txt"
            submit_stdout_path.write_text(_redact(result.stdout), encoding="utf-8")
            return ExperimentJobRecord(
                job_id=job_id,
                experiment_id=experiment.id,
                backend="nebius_serverless_job",
                status="queued",
                batch_start=0,
                batch_end=experiment.attack_count,
                attack_count=experiment.attack_count,
                created_at=now,
                updated_at=now,
                message=f"Nebius submit command accepted job {job_id}. Waiting for status and artifacts confirmation.",
                artifact_paths={**base_artifact_paths, "submit_stdout": str(submit_stdout_path)},
            )
        except RuntimeError as exc:
            submit_error_path = artifact_dir / "nebius_submit_error.txt"
            submit_error_path.write_text(_redact(str(exc)), encoding="utf-8")
            return ExperimentJobRecord(
                job_id=f"NEB-FAILED-{uuid4().hex[:8].upper()}",
                experiment_id=experiment.id,
                backend="nebius_serverless_job",
                status="failed",
                batch_start=0,
                batch_end=experiment.attack_count,
                attack_count=experiment.attack_count,
                created_at=now,
                updated_at=now,
                message=f"Nebius submit command failed: {_redact(str(exc))}",
                artifact_paths={**base_artifact_paths, "submit_error": str(submit_error_path)},
            )

    def list_jobs(self, experiment_id: str) -> list[ExperimentJobRecord] | None:
        if self.repository.get(experiment_id) is None:
            return None
        return self._read_jobs(experiment_id)

    def render_job_config(self, experiment_id: str) -> NebiusJobConfigRenderResponse | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None
        artifact_dir = self.repository.experiment_dir(experiment.id)
        rendered_config_path = self._render_job_config(experiment, artifact_dir)
        context = self._command_context(experiment=experiment, rendered_config_path=rendered_config_path)
        updated = experiment.model_copy(
            update={
                "artifact_paths": {
                    **experiment.artifact_paths,
                    "nebius_job_config": str(rendered_config_path),
                },
                "updated_at": utc_now(),
            }
        )
        self.repository.save(updated)
        return NebiusJobConfigRenderResponse(
            experiment_id=experiment.id,
            path=str(rendered_config_path),
            image=context["image"],
            output_dir=context["output_dir"],
        )

    def refresh(self, experiment_id: str) -> list[ExperimentJobRecord] | None:
        if self.repository.get(experiment_id) is None:
            return None
        jobs = self._read_jobs(experiment_id)
        now = utc_now()
        refreshed: list[ExperimentJobRecord] = []
        for job in jobs:
            if job.backend == "nebius_serverless_job" and job.status == "real_nebius_pending":
                refreshed.append(job.model_copy(update={"updated_at": now, "message": self._pending_message()}))
            elif job.backend == "nebius_serverless_job" and job.status in {"queued", "running"}:
                refreshed.append(self._refresh_submitted_job(job, now=now))
            else:
                refreshed.append(job)
        self._write_jobs(experiment_id, refreshed)
        return refreshed

    def collect_artifacts(self, experiment_id: str) -> NebiusArtifactCollectionResponse | None:
        experiment = self.repository.get(experiment_id)
        if experiment is None:
            return None
        artifact_dir = self.repository.experiment_dir(experiment.id)
        rendered_config_path = Path(
            experiment.artifact_paths.get("nebius_job_config", artifact_dir / "nebius_job_config.rendered.yaml")
        )
        context = self._command_context(experiment=experiment, rendered_config_path=rendered_config_path)
        source_dir = self._find_mounted_output_dir(experiment, context)
        command_message = ""

        if source_dir is None:
            artifacts_template = self._setting("nebius_job_artifacts_command_template")
            if artifacts_template:
                try:
                    result = self._run_template_command(artifacts_template, context)
                    artifact_dir.mkdir(parents=True, exist_ok=True)
                    collection_stdout_path = artifact_dir / "nebius_artifact_collection_stdout.txt"
                    collection_stdout_path.write_text(_redact(result.stdout), encoding="utf-8")
                    source_dir = self._find_mounted_output_dir(experiment, context, command_output=result.stdout)
                    command_message = "Artifact collection command executed."
                except RuntimeError as exc:
                    command_message = f"Artifact collection command failed: {_redact(str(exc))}"

        if source_dir is None:
            return self._mark_artifacts_pending(
                experiment,
                artifact_dir=artifact_dir,
                message=command_message or "Nebius job artifacts are not available in the mounted output path yet.",
            )

        normalized = normalize_batch_artifacts(
            experiment_id=experiment.id,
            artifact_dir=artifact_dir,
            source_dir=source_dir,
        )
        collected = not normalized.missing
        updated = experiment.model_copy(
            update={
                "status": "completed" if collected else "cloud_artifacts_pending",
                "artifact_paths": {**experiment.artifact_paths, **normalized.artifact_paths},
                "updated_at": utc_now(),
            }
        )
        self.repository.save(updated)
        if collected:
            self._mark_latest_cloud_job_completed(experiment.id, normalized.artifact_paths)
        return NebiusArtifactCollectionResponse(
            experiment_id=experiment.id,
            status="collected" if collected else "cloud_artifacts_pending",
            source_dir=str(source_dir),
            artifact_dir=str(artifact_dir),
            artifact_paths=normalized.artifact_paths,
            copied_count=normalized.copied_count,
            missing=normalized.missing,
            message=(
                "Nebius job artifacts collected into the experiment artifact layout."
                if collected
                else "Nebius job artifact collection found partial output; missing expected files remain."
            ),
        )

    def _refresh_submitted_job(self, job: ExperimentJobRecord, *, now: str) -> ExperimentJobRecord:
        experiment = self.repository.get(job.experiment_id)
        if experiment is None:
            return job
        artifact_dir = self.repository.experiment_dir(job.experiment_id)
        config_path = Path(job.artifact_paths.get("nebius_job_config", artifact_dir / "nebius_job_config.rendered.yaml"))
        context = self._command_context(experiment=experiment, rendered_config_path=config_path)
        status_template = self._setting("nebius_job_status_command_template")
        if not status_template:
            return job.model_copy(
                update={
                    "updated_at": now,
                    "message": "Nebius job submitted; status command is not configured.",
                }
            )

        try:
            status_result = self._run_template_command(status_template, context)
            status = _parse_job_status(status_result.stdout) or job.status
        except RuntimeError as exc:
            return job.model_copy(
                update={
                    "updated_at": now,
                    "message": f"Nebius status command failed: {_redact(str(exc))}",
                }
            )

        artifact_paths = dict(job.artifact_paths)
        logs_path = self._collect_optional_command(
            "logs",
            self._setting("nebius_job_logs_command_template"),
            context,
            artifact_dir,
        )
        if logs_path is not None:
            artifact_paths["nebius_job_logs"] = str(logs_path)

        artifacts_path = self._collect_optional_command(
            "artifacts",
            self._setting("nebius_job_artifacts_command_template"),
            context,
            artifact_dir,
        )
        if artifacts_path is not None:
            artifact_paths["nebius_job_artifacts"] = str(artifacts_path)

        if status == "completed" and artifacts_path is not None:
            return job.model_copy(
                update={
                    "status": "completed",
                    "updated_at": now,
                    "message": "Nebius job completed and artifact collection command returned successfully.",
                    "artifact_paths": artifact_paths,
                }
            )
        if status == "completed":
            return job.model_copy(
                update={
                    "status": "running",
                    "updated_at": now,
                    "message": "Nebius job reported completed, but artifact collection is not confirmed.",
                    "artifact_paths": artifact_paths,
                }
            )
        return job.model_copy(
            update={
                "status": status,
                "updated_at": now,
                "message": f"Nebius job status is {status}.",
                "artifact_paths": artifact_paths,
            }
        )

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

    def _render_job_config(self, experiment: Experiment, artifact_dir: Path) -> Path:
        render_job_config = _load_render_job_config()
        image = self._job_image()
        return render_job_config(
            experiment_id=experiment.id,
            runs=experiment.attack_count,
            batch_size=experiment.batch_size,
            scenarios=experiment.scenarios,
            image=image,
            output_dir=f"/job/outputs/experiments/{experiment.id}/local-batch",
            rendered_path=artifact_dir / "nebius_job_config.rendered.yaml",
        )

    def _command_context(self, *, experiment: Experiment, rendered_config_path: Path) -> dict[str, str]:
        return {
            "config_path": str(rendered_config_path),
            "experiment_id": experiment.id,
            "image": self._job_image(),
            "output_dir": f"/job/outputs/experiments/{experiment.id}/local-batch",
        }

    def _job_image(self) -> str:
        return (
            self.settings.nebius_job_image
            if self.settings is not None
            else "ghcr.io/your-org/ai-market-abuse-detection-arena-jobs:latest"
        )

    def _setting(self, name: str) -> str | None:
        if self.settings is None:
            return None
        value = getattr(self.settings, name, None)
        if isinstance(value, str) and value.strip():
            return value
        return None

    def _run_template_command(self, template: str, context: dict[str, str]) -> subprocess.CompletedProcess[str]:
        try:
            command = template.format(**context)
        except KeyError as exc:
            raise RuntimeError(f"unknown command template variable: {exc}") from exc
        argv = shlex.split(command)
        if not argv:
            raise RuntimeError("empty command template")
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                check=False,
                text=True,
                timeout=120.0,
            )
        except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
            raise RuntimeError(_redact(str(exc))) from exc
        if completed.returncode != 0:
            details = _redact((completed.stderr or completed.stdout or "").strip())
            raise RuntimeError(f"command exited {completed.returncode}: {details}")
        return completed

    def _collect_optional_command(
        self,
        kind: str,
        template: str | None,
        context: dict[str, str],
        artifact_dir: Path,
    ) -> Path | None:
        if not template:
            return None
        result = self._run_template_command(template, context)
        suffix = "json" if _looks_like_json(result.stdout) else "txt"
        path = artifact_dir / f"nebius_job_{kind}.{suffix}"
        path.write_text(_redact(result.stdout), encoding="utf-8")
        return path

    def _find_mounted_output_dir(
        self,
        experiment: Experiment,
        context: dict[str, str],
        command_output: str | None = None,
    ) -> Path | None:
        artifact_dir = self.repository.experiment_dir(experiment.id)
        candidates: list[Path] = [
            artifact_dir / "local-batch",
            artifact_dir / "nebius-job-output",
            artifact_dir / "cloud-batch",
            self._local_path_for_job_output_dir(context["output_dir"]),
        ]
        if command_output:
            parsed = _parse_artifact_output_path(command_output)
            if parsed is not None:
                candidates.insert(0, parsed)
                candidates.insert(0, self._local_path_for_job_output_dir(str(parsed)))

        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.expanduser().resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if _has_expected_artifact_files(resolved):
                return resolved
        return None

    def _local_path_for_job_output_dir(self, output_dir: str) -> Path:
        prefix = "/job/outputs/"
        if output_dir.startswith(prefix):
            return self.repository.store.output_dir / output_dir[len(prefix):]
        return Path(output_dir)

    def _mark_artifacts_pending(
        self,
        experiment: Experiment,
        *,
        artifact_dir: Path,
        message: str,
    ) -> NebiusArtifactCollectionResponse:
        updated = experiment.model_copy(update={"status": "cloud_artifacts_pending", "updated_at": utc_now()})
        self.repository.save(updated)
        return NebiusArtifactCollectionResponse(
            experiment_id=experiment.id,
            status="cloud_artifacts_pending",
            artifact_dir=str(artifact_dir),
            message=message,
            missing=[source for source, _target in ARTIFACT_MAPPINGS.values()],
        )

    def _mark_latest_cloud_job_completed(self, experiment_id: str, artifact_paths: dict[str, str]) -> None:
        jobs = self._read_jobs(experiment_id)
        if not jobs:
            return
        updated_jobs: list[ExperimentJobRecord] = []
        marked = False
        for job in reversed(jobs):
            if not marked and job.backend == "nebius_serverless_job" and job.status in {"queued", "running"}:
                updated_jobs.append(
                    job.model_copy(
                        update={
                            "status": "completed",
                            "updated_at": utc_now(),
                            "message": "Nebius job artifacts collected from mounted output.",
                            "artifact_paths": {**job.artifact_paths, **artifact_paths},
                        }
                    )
                )
                marked = True
            else:
                updated_jobs.append(job)
        self._write_jobs(experiment_id, list(reversed(updated_jobs)))

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


def _load_render_job_config() -> RenderJobConfig:
    repo_root = _repo_root()
    module_path = repo_root / "serverless" / "jobs" / "render_job_config.py"
    spec = importlib.util.spec_from_file_location("aimada_render_job_config", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load Nebius job config renderer from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_job_config


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [here.parents[3], here.parents[2], Path.cwd()]
    for candidate in candidates:
        if (candidate / "serverless" / "jobs" / "nebius_job_config.yaml").exists():
            return candidate
    return here.parents[3]


def _parse_job_id(output: str) -> str | None:
    text = output.strip()
    if not text:
        return None
    parsed = _parse_json_object(text)
    if parsed is not None:
        for key in ("job_id", "id", "jobId", "jobID"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        metadata = parsed.get("metadata")
        if isinstance(metadata, dict):
            for key in ("job_id", "id", "jobId", "jobID"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    patterns = [
        r"\bjob[_ -]?id\b\s*[:=]\s*([A-Za-z0-9_.:/-]+)",
        r"\bid\b\s*[:=]\s*([A-Za-z0-9_.:/-]+)",
        r"\b(job-[A-Za-z0-9_.-]+)\b",
        r"\b(NEB-[A-Za-z0-9_.-]+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _parse_job_status(output: str) -> JobStatus | None:
    text = output.strip()
    if not text:
        return None
    parsed = _parse_json_object(text)
    if parsed is not None:
        value = parsed.get("status") or parsed.get("state")
        if isinstance(value, str):
            return _normalize_job_status(value)
    match = re.search(r"\b(?:status|state)\b\s*[:=]\s*([A-Za-z_-]+)", text, flags=re.IGNORECASE)
    if match:
        return _normalize_job_status(match.group(1))
    return _normalize_job_status(text)


def _parse_artifact_output_path(output: str) -> Path | None:
    text = output.strip()
    if not text:
        return None
    parsed = _parse_json_object(text)
    if parsed is not None:
        for key in ("output_dir", "artifact_dir", "artifacts_dir", "path"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return Path(value.strip())
    first_line = text.splitlines()[0].strip()
    if first_line:
        return Path(first_line)
    return None


def _has_expected_artifact_files(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    expected_names = [source for source, _target in ARTIFACT_MAPPINGS.values()]
    return any((path / name).is_file() for name in expected_names)


def _normalize_job_status(value: str) -> JobStatus | None:
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    if normalized in {"queued", "pending", "submitted"}:
        return "queued"
    if normalized in {"running", "in_progress", "started"}:
        return "running"
    if normalized in {"completed", "complete", "succeeded", "success", "done"}:
        return "completed"
    if normalized in {"failed", "failure", "error", "cancelled", "canceled"}:
        return "failed"
    if normalized == "real_nebius_pending":
        return "real_nebius_pending"
    return None


def _parse_json_object(text: str) -> dict[str, Any] | None:
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _looks_like_json(text: str) -> bool:
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return False
    return True


def _redact(value: str) -> str:
    redacted = value
    patterns = [
        r"Bearer\s+[A-Za-z0-9._~+/=-]+",
        r"(?i)(api[_-]?key|token|secret|authorization)(\s*[:=]\s*)([^\s\"']+)",
    ]
    for pattern in patterns:
        redacted = re.sub(pattern, _redaction_replacement, redacted)
    return redacted


def _redaction_replacement(match: re.Match[str]) -> str:
    if match.group(0).lower().startswith("bearer "):
        return "Bearer [REDACTED]"
    return f"{match.group(1)}{match.group(2)}[REDACTED]"


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
