import csv
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote
from uuid import uuid4

from pydantic import BaseModel, Field

from app.config import get_settings
from app.experiments.artifact_normalizer import ArtifactNormalizationResponse, normalize_batch_artifacts
from app.nebius.evidence_archive import NebiusEvidenceArchive
from app.storage.local_store import LocalStore


ManipulationType = Literal["spoofing_like_wall", "layering_like", "quote_stuffing", "liquidity_evaporation"]
DetectorName = Literal["spoofing_like", "layering_like", "quote_stuffing", "liquidity_shock"]
TournamentStatus = Literal["queued", "running", "completed", "failed", "real_nebius_pending"]
TournamentExecutionMode = Literal["local_mock", "local", "nebius_serverless_job"]
_LOCAL_TOURNAMENT_LOCK = threading.Lock()


class DetectorTournamentStartRequest(BaseModel):
    number_of_scenarios: int = Field(default=100, ge=1, le=1000)
    manipulation_types: list[ManipulationType] = Field(default_factory=lambda: ["spoofing_like_wall", "layering_like", "quote_stuffing", "liquidity_evaporation"])
    difficulty_mix: dict[str, float] = Field(default_factory=lambda: {"easy": 0.2, "medium": 0.5, "hard": 0.2, "adversarial": 0.1})
    detector_set: list[DetectorName] = Field(default_factory=lambda: ["spoofing_like", "layering_like", "quote_stuffing"])
    random_seed: int = 42
    execution_mode: Literal["local", "local_mock", "nebius"] = "local_mock"


class DetectorTournamentLeaderboardRow(BaseModel):
    detector: str
    scenario: str
    precision: float | None = Field(default=None, ge=0.0, le=1.0)
    recall: float | None = Field(default=None, ge=0.0, le=1.0)
    f1: float | None = Field(default=None, ge=0.0, le=1.0)
    specificity: float | None = Field(default=None, ge=0.0, le=1.0)
    false_positive_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    false_positives: int = Field(ge=0)
    false_negatives: int = Field(ge=0)
    avg_detection_latency_ms: float | None = None
    runs: int = Field(default=0, ge=0)
    temporal_overlap: float | None = Field(default=None, ge=0.0, le=1.0)
    event_precision: float | None = Field(default=None, ge=0.0, le=1.0)
    event_recall: float | None = Field(default=None, ge=0.0, le=1.0)
    participant_precision: float | None = Field(default=None, ge=0.0, le=1.0)
    participant_recall: float | None = Field(default=None, ge=0.0, le=1.0)
    order_precision: float | None = Field(default=None, ge=0.0, le=1.0)
    order_recall: float | None = Field(default=None, ge=0.0, le=1.0)


class DetectorTournamentResponse(BaseModel):
    tournament_id: str
    status: TournamentStatus
    execution_mode: TournamentExecutionMode
    started_at: str
    completed_at: str | None = None
    detectors: list[str]
    leaderboard: list[DetectorTournamentLeaderboardRow]
    metrics: dict[str, Any]
    artifacts: dict[str, str]
    summary: str
    fallback_reason: str | None = None


class DetectorTournamentArtifact(BaseModel):
    name: str
    path: str
    download_url: str


class DetectorTournamentArtifactsResponse(BaseModel):
    tournament_id: str
    artifacts: list[DetectorTournamentArtifact]


def start_tournament(
    request: DetectorTournamentStartRequest,
    *,
    store: LocalStore,
    repo_root: Path,
) -> DetectorTournamentResponse:
    started_at = _now()
    tournament_id = f"TRN-{uuid4().hex[:8].upper()}"
    if request.execution_mode == "nebius" and get_settings().nebius_job_submit_command_template:
        response = _submit_nebius_job(request, tournament_id=tournament_id, started_at=started_at, store=store)
    elif request.execution_mode in {"local_mock", "nebius"}:
        fallback_reason = (
            "NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE is not configured; returned deterministic local mock tournament."
            if request.execution_mode == "nebius"
            else "local_mock mode uses deterministic tournament output without backend batch execution."
        )
        response = _mock_tournament_response(
            request,
            tournament_id=tournament_id,
            started_at=started_at,
            completed_at=_now(),
            artifacts={},
            fallback_reason=fallback_reason,
        )
    else:
        response = _run_local_tournament(
            request,
            tournament_id=tournament_id,
            started_at=started_at,
            store=store,
            repo_root=repo_root,
            fallback_reason=None,
        )
    _persist_tournament(store, response)
    return response


def queue_tournament(
    request: DetectorTournamentStartRequest,
    *,
    store: LocalStore,
    repo_root: Path,
) -> DetectorTournamentResponse:
    started_at = _now()
    tournament_id = f"TRN-{uuid4().hex[:8].upper()}"
    if request.execution_mode == "nebius" and get_settings().nebius_job_submit_command_template:
        response = _submit_nebius_job(request, tournament_id=tournament_id, started_at=started_at, store=store)
    elif request.execution_mode in {"local_mock", "nebius"}:
        fallback_reason = (
            "NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE is not configured; returned deterministic local mock tournament."
            if request.execution_mode == "nebius"
            else "local_mock mode uses deterministic tournament output without backend batch execution."
        )
        response = _mock_tournament_response(
            request,
            tournament_id=tournament_id,
            started_at=started_at,
            completed_at=_now(),
            artifacts={},
            fallback_reason=fallback_reason,
        )
    else:
        response = _queued_local_response(request, tournament_id=tournament_id, started_at=started_at)
    _persist_tournament(store, response)
    return response


def complete_queued_tournament(
    request: DetectorTournamentStartRequest,
    *,
    tournament_id: str,
    started_at: str,
    store: LocalStore,
    repo_root: Path,
) -> None:
    queued = get_tournament(tournament_id, store=store)
    if queued is None or queued.status != "queued":
        return
    _persist_tournament(
        store,
        queued.model_copy(update={"status": "running", "summary": "Local detector tournament is running."}),
    )
    if not _LOCAL_TOURNAMENT_LOCK.acquire(blocking=False):
        response = _mock_tournament_response(
            request,
            tournament_id=tournament_id,
            started_at=started_at,
            completed_at=_now(),
            artifacts={},
            fallback_reason="local detector tournament runner is busy; returned deterministic mock output.",
        )
        _persist_tournament(store, response)
        return
    try:
        response = _run_local_tournament(
            request,
            tournament_id=tournament_id,
            started_at=started_at,
            store=store,
            repo_root=repo_root,
            fallback_reason=None,
        )
        _persist_tournament(store, response)
    finally:
        _LOCAL_TOURNAMENT_LOCK.release()


def get_tournament(tournament_id: str, *, store: LocalStore) -> DetectorTournamentResponse | None:
    decoded = store.read_json(f"nebius/tournaments/{tournament_id}/tournament.json")
    if not isinstance(decoded, dict):
        return None
    return DetectorTournamentResponse.model_validate(decoded)


def refresh_tournament(tournament_id: str, *, store: LocalStore) -> DetectorTournamentResponse | None:
    tournament = get_tournament(tournament_id, store=store)
    if tournament is None or tournament.execution_mode != "nebius_serverless_job":
        return tournament
    if tournament.status in {"failed", "real_nebius_pending"}:
        return tournament

    settings = get_settings()
    job_id = str(tournament.metrics.get("nebius_job_id") or "").strip()
    status_template = settings.nebius_job_status_command_template
    if not job_id or not status_template:
        return tournament

    artifact_dir = store.output_dir / "nebius" / "tournaments" / tournament_id
    try:
        status_result = _run_command_template(status_template, {"job_id": job_id})
        status = _parse_job_status(status_result.stdout) or tournament.status
    except RuntimeError as exc:
        response = tournament.model_copy(
            update={"summary": f"Nebius Job status refresh failed: {_redact(str(exc))}"}
        )
        _persist_tournament(store, response)
        return response

    artifacts = dict(tournament.artifacts)
    if status in {"completed", "failed"} and settings.nebius_job_logs_command_template:
        try:
            logs_result = _run_command_template(settings.nebius_job_logs_command_template, {"job_id": job_id})
            logs_path = artifact_dir / "nebius_job_logs.txt"
            logs_path.write_text(_redact(logs_result.stdout), encoding="utf-8")
            artifacts["nebius_job_logs"] = str(logs_path)
        except RuntimeError:
            pass

    if status == "completed":
        try:
            collected = _collect_cloud_artifacts(tournament, artifact_dir=artifact_dir, settings=settings)
        except RuntimeError as exc:
            response = tournament.model_copy(
                update={
                    "status": "failed",
                    "completed_at": _now(),
                    "artifacts": artifacts,
                    "summary": f"Nebius Job completed, but artifact collection failed: {_redact(str(exc))}",
                }
            )
            _persist_tournament(store, response)
            return response
        if collected.missing:
            response = tournament.model_copy(
                update={
                    "status": "running",
                    "artifacts": {**artifacts, **collected.artifact_paths},
                    "summary": "Nebius Job completed; waiting for the remaining S3 artifacts.",
                }
            )
            _persist_tournament(store, response)
            return response
        metrics_path = Path(collected.artifact_paths["detector_metrics"])
        leaderboard = _leaderboard_from_metrics(metrics_path)
        response = tournament.model_copy(
            update={
                "status": "completed",
                "completed_at": _now(),
                "leaderboard": leaderboard,
                "metrics": {
                    **tournament.metrics,
                    **_metrics_summary(
                        leaderboard,
                        total_scenarios=int(tournament.metrics.get("requested_scenarios") or 0),
                    ),
                    "artifact_count": collected.copied_count,
                },
                "artifacts": {**artifacts, **collected.artifact_paths},
                "summary": (
                    f"Nebius Serverless Job {job_id} completed; {collected.copied_count} S3 artifacts "
                    "were synced to the backend and exposed to the UI."
                ),
            }
        )
        _persist_tournament(store, response)
        return response

    response = tournament.model_copy(
        update={
            "status": status,
            "artifacts": artifacts,
            "summary": f"Nebius Serverless Job {job_id} status is {status}.",
        }
    )
    _persist_tournament(store, response)
    return response


def tournament_artifacts(tournament_id: str, *, store: LocalStore) -> DetectorTournamentArtifactsResponse | None:
    tournament = get_tournament(tournament_id, store=store)
    if tournament is None:
        return None
    return DetectorTournamentArtifactsResponse(
        tournament_id=tournament_id,
        artifacts=[
            DetectorTournamentArtifact(
                name=name,
                path=path,
                download_url=f"/api/experiments/artifacts/download?path={quote(path, safe='')}",
            )
            for name, path in tournament.artifacts.items()
        ],
    )


def _run_local_tournament(
    request: DetectorTournamentStartRequest,
    *,
    tournament_id: str,
    started_at: str,
    store: LocalStore,
    repo_root: Path,
    fallback_reason: str | None,
) -> DetectorTournamentResponse:
    output_dir = store.output_dir / "nebius" / "tournaments" / tournament_id / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)
    scenarios = _scenario_names(request.manipulation_types)
    detectors = _detectors(request.detector_set)
    scenario_limit = get_settings().nebius_local_tournament_scenario_limit
    effective_scenarios = min(request.number_of_scenarios, scenario_limit)
    if request.number_of_scenarios > effective_scenarios:
        cap_reason = (
            f"local tournament capped at {effective_scenarios} scenarios; use Nebius Serverless Jobs "
            f"for requested high-load run of {request.number_of_scenarios} scenarios."
        )
        fallback_reason = f"{fallback_reason} {cap_reason}".strip() if fallback_reason else cap_reason
    command = [
        sys.executable,
        str(repo_root / "serverless" / "jobs" / "detector_tournament.py"),
        "--runs",
        str(effective_scenarios),
        "--scenarios",
        ",".join(scenarios),
        "--detectors",
        ",".join(detectors),
        "--random-seed",
        str(request.random_seed),
        "--difficulty-mix",
        json.dumps(request.difficulty_mix, separators=(",", ":")),
        "--output",
        str(output_dir),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            cwd=repo_root,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        return _mock_tournament_response(
            request,
            tournament_id=tournament_id,
            started_at=started_at,
            completed_at=_now(),
            artifacts={},
            fallback_reason="local detector tournament timed out; returned deterministic mock output.",
        )
    if completed.returncode != 0:
        return _mock_tournament_response(
            request,
            tournament_id=tournament_id,
            started_at=started_at,
            completed_at=_now(),
            artifacts={},
            fallback_reason=f"local detector tournament failed: {completed.stderr[-1000:] or completed.stdout[-1000:]}",
        )

    leaderboard = _leaderboard_from_metrics(output_dir / "metrics.csv")
    artifacts = _artifact_paths(output_dir)
    return DetectorTournamentResponse(
        tournament_id=tournament_id,
        status="completed",
        execution_mode="local_mock" if request.execution_mode in {"local_mock", "nebius"} else "local",
        started_at=started_at,
        completed_at=_now(),
        detectors=detectors,
        leaderboard=leaderboard,
        metrics=_metrics_summary(leaderboard, total_scenarios=effective_scenarios),
        artifacts=artifacts,
        summary=(
            f"Detector tournament completed locally over exactly {effective_scenarios} "
            "synthetic scenario replays using the Nebius Serverless Job runner contract."
        ),
        fallback_reason=fallback_reason,
    )


def _pending_nebius_response(
    request: DetectorTournamentStartRequest,
    *,
    tournament_id: str,
    started_at: str,
    store: LocalStore,
) -> DetectorTournamentResponse:
    artifact_dir = store.output_dir / "nebius" / "tournaments" / tournament_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    request_path = artifact_dir / "request.json"
    request_path.write_text(request.model_dump_json(indent=2), encoding="utf-8")
    return DetectorTournamentResponse(
        tournament_id=tournament_id,
        status="real_nebius_pending",
        execution_mode="nebius_serverless_job",
        started_at=started_at,
        completed_at=None,
        detectors=_detectors(request.detector_set),
        leaderboard=[],
        metrics={
            "requested_scenarios": request.number_of_scenarios,
            "manipulation_types": request.manipulation_types,
            "difficulty_mix": request.difficulty_mix,
        },
        artifacts={"request": str(request_path)},
        summary=(
            "Nebius Serverless Job execution is configured. Submit/collect remains isolated in "
            "the existing managed experiment orchestration path."
        ),
    )


def _queued_local_response(
    request: DetectorTournamentStartRequest,
    *,
    tournament_id: str,
    started_at: str,
) -> DetectorTournamentResponse:
    fallback_reason = None
    if request.execution_mode == "nebius":
        fallback_reason = "NEBIUS_JOB_SUBMIT_COMMAND_TEMPLATE is not configured; queued deterministic local fallback."
    return DetectorTournamentResponse(
        tournament_id=tournament_id,
        status="queued",
        execution_mode="local_mock" if request.execution_mode in {"local_mock", "nebius"} else "local",
        started_at=started_at,
        completed_at=None,
        detectors=_detectors(request.detector_set),
        leaderboard=[],
        metrics={
            "requested_scenarios": request.number_of_scenarios,
            "manipulation_types": request.manipulation_types,
            "difficulty_mix": request.difficulty_mix,
        },
        artifacts={},
        summary="Detector tournament queued for local execution.",
        fallback_reason=fallback_reason,
    )


def _submit_nebius_job(
    request: DetectorTournamentStartRequest,
    *,
    tournament_id: str,
    started_at: str,
    store: LocalStore,
) -> DetectorTournamentResponse:
    settings = get_settings()
    artifact_dir = store.output_dir / "nebius" / "tournaments" / tournament_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    request_path = artifact_dir / "request.json"
    request_path.write_text(request.model_dump_json(indent=2), encoding="utf-8")
    submit_template = settings.nebius_job_submit_command_template
    if not submit_template:
        return _pending_nebius_response(request, tournament_id=tournament_id, started_at=started_at, store=store)

    cloud_output_uri = _tournament_cloud_output_uri(settings, tournament_id)
    batch_args = [
        "/job/serverless/jobs/run_batch_experiments.py",
        "--runs",
        str(request.number_of_scenarios),
        "--batch-size",
        str(min(request.number_of_scenarios, 100)),
        "--scenarios",
        ",".join(_scenario_names(request.manipulation_types)),
        "--random-seed",
        str(request.random_seed),
        "--difficulty-mix",
        json.dumps(request.difficulty_mix, separators=(",", ":")),
        "--output",
        f"/job/outputs/tournaments/{tournament_id}/local-batch",
    ]
    if cloud_output_uri:
        batch_args.extend(["--s3-output-uri", cloud_output_uri])
        if settings.nebius_object_storage_endpoint_url:
            batch_args.extend(["--s3-endpoint-url", settings.nebius_object_storage_endpoint_url])
    context = {
        "config_path": str(request_path),
        "experiment_id": tournament_id,
        "image": settings.nebius_job_image,
        "output_dir": str(artifact_dir / "job-output"),
        "job_args": shlex.quote(shlex.join(batch_args)),
        "tournament_id": tournament_id,
        "subnet_id": settings.nebius_subnet_id or "",
        "subnet_id_arg": _optional_flag("--subnet-id", settings.nebius_subnet_id),
        "parent_id": settings.nebius_parent_id or "",
        "parent_id_arg": _optional_flag("--parent-id", settings.nebius_parent_id),
        "volume": settings.nebius_job_output_volume or settings.nebius_volume or "",
        "volume_arg": _optional_flag("--volume", settings.nebius_job_output_volume or settings.nebius_volume),
        "object_storage_env_args": _object_storage_env_args(settings),
    }
    try:
        command = submit_template.format(**context)
        completed = subprocess.run(
            shlex.split(command),
            capture_output=True,
            check=False,
            text=True,
            timeout=120,
        )
    except (KeyError, OSError, subprocess.SubprocessError, TimeoutError) as exc:
        return _failed_nebius_submit_response(
            request,
            tournament_id=tournament_id,
            started_at=started_at,
            artifact_dir=artifact_dir,
            message=f"Nebius Serverless Job submit failed: {exc}",
        )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "").strip()
        return _failed_nebius_submit_response(
            request,
            tournament_id=tournament_id,
            started_at=started_at,
            artifact_dir=artifact_dir,
            message=f"Nebius Serverless Job submit exited {completed.returncode}: {details[:800]}",
        )

    submit_stdout_path = artifact_dir / "nebius_submit_stdout.txt"
    submit_stdout_path.write_text(_redact(completed.stdout), encoding="utf-8")
    job_id = _parse_job_id(completed.stdout) or f"NEB-SUBMITTED-{uuid4().hex[:8].upper()}"
    return DetectorTournamentResponse(
        tournament_id=tournament_id,
        status="queued",
        execution_mode="nebius_serverless_job",
        started_at=started_at,
        completed_at=None,
        detectors=_detectors(request.detector_set),
        leaderboard=[],
        metrics={
            "requested_scenarios": request.number_of_scenarios,
            "manipulation_types": request.manipulation_types,
            "difficulty_mix": request.difficulty_mix,
            "nebius_job_id": job_id,
            "cloud_output_uri": cloud_output_uri,
        },
        artifacts={"request": str(request_path), "submit_stdout": str(submit_stdout_path)},
        summary=f"Nebius Serverless Job queued as {job_id}. Poll job status and artifacts from the configured Nebius path.",
    )


def _failed_nebius_submit_response(
    request: DetectorTournamentStartRequest,
    *,
    tournament_id: str,
    started_at: str,
    artifact_dir: Path,
    message: str,
) -> DetectorTournamentResponse:
    error_path = artifact_dir / "nebius_submit_error.txt"
    error_path.write_text(message, encoding="utf-8")
    return DetectorTournamentResponse(
        tournament_id=tournament_id,
        status="failed",
        execution_mode="nebius_serverless_job",
        started_at=started_at,
        completed_at=_now(),
        detectors=_detectors(request.detector_set),
        leaderboard=[],
        metrics={"requested_scenarios": request.number_of_scenarios},
        artifacts={"submit_error": str(error_path)},
        summary=message,
        fallback_reason=message,
    )


def _optional_flag(flag: str, value: str | None) -> str:
    if not value or not value.strip():
        return ""
    return f"{flag} {shlex.quote(value.strip())}"


def _object_storage_env_args(settings: Any) -> str:
    values = {
        "AWS_ACCESS_KEY_ID": settings.nebius_object_storage_access_key_id,
        "AWS_SECRET_ACCESS_KEY": settings.nebius_object_storage_secret_access_key,
        "AWS_SESSION_TOKEN": settings.nebius_object_storage_session_token,
        "AWS_DEFAULT_REGION": settings.nebius_object_storage_region,
        "AWS_EC2_METADATA_DISABLED": "true",
    }
    return " ".join(
        f"--env {shlex.quote(f'{name}={value}')}"
        for name, value in values.items()
        if value
    )


def _tournament_cloud_output_uri(settings: Any, tournament_id: str) -> str | None:
    base_uri = str(getattr(settings, "nebius_job_output_uri", "") or "").rstrip("/")
    if not base_uri:
        return None
    return f"{base_uri}/tournaments/{tournament_id}/local-batch"


def _collect_cloud_artifacts(
    tournament: DetectorTournamentResponse,
    *,
    artifact_dir: Path,
    settings: Any,
) -> ArtifactNormalizationResponse:
    cloud_output_uri = str(tournament.metrics.get("cloud_output_uri") or "").strip()
    if not cloud_output_uri:
        raise RuntimeError("tournament cloud output URI is not configured")
    aws = shutil.which("aws")
    if aws is None:
        raise RuntimeError("aws CLI is required to sync tournament S3 artifacts")
    source_dir = artifact_dir / "cloud-batch"
    source_dir.mkdir(parents=True, exist_ok=True)
    command = [aws]
    if settings.nebius_object_storage_endpoint_url:
        command.extend(["--endpoint-url", settings.nebius_object_storage_endpoint_url])
    command.extend(["s3", "sync", cloud_output_uri, str(source_dir), "--only-show-errors"])
    env = os.environ.copy()
    if settings.nebius_object_storage_access_key_id:
        env["AWS_ACCESS_KEY_ID"] = settings.nebius_object_storage_access_key_id
    if settings.nebius_object_storage_secret_access_key:
        env["AWS_SECRET_ACCESS_KEY"] = settings.nebius_object_storage_secret_access_key
    if settings.nebius_object_storage_session_token:
        env["AWS_SESSION_TOKEN"] = settings.nebius_object_storage_session_token
    env["AWS_DEFAULT_REGION"] = settings.nebius_object_storage_region
    env["AWS_EC2_METADATA_DISABLED"] = "true"
    completed = subprocess.run(command, capture_output=True, check=False, text=True, timeout=300, env=env)
    sync_log = artifact_dir / "nebius_artifact_sync.txt"
    sync_log.write_text(_redact(completed.stdout or completed.stderr), encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"aws s3 sync exited {completed.returncode}: {completed.stderr or completed.stdout}")
    normalized = normalize_batch_artifacts(
        experiment_id=tournament.tournament_id,
        artifact_dir=artifact_dir,
        source_dir=source_dir,
    )
    normalized.artifact_paths["nebius_artifact_sync"] = str(sync_log)
    return normalized


def _run_command_template(template: str, context: dict[str, str]) -> subprocess.CompletedProcess[str]:
    try:
        command = template.format(**context)
        completed = subprocess.run(shlex.split(command), capture_output=True, check=False, text=True, timeout=120)
    except (KeyError, OSError, subprocess.SubprocessError, TimeoutError) as exc:
        raise RuntimeError(str(exc)) from exc
    if completed.returncode != 0:
        raise RuntimeError(f"command exited {completed.returncode}: {completed.stderr or completed.stdout}")
    return completed


def _parse_job_status(output: str) -> TournamentStatus | None:
    text = output.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    value: Any = parsed
    if isinstance(parsed, dict):
        value = parsed.get("status") or parsed.get("state")
        if isinstance(value, dict):
            value = value.get("state") or value.get("status")
    if not isinstance(value, str):
        match = re.search(r"\b(?:status|state)\b\s*[:=]\s*([A-Za-z_-]+)", text, flags=re.IGNORECASE)
        value = match.group(1) if match else text
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    if normalized in {"queued", "pending", "submitted", "provisioning", "starting"}:
        return "queued"
    if normalized in {"running", "in_progress", "started"}:
        return "running"
    if normalized in {"completed", "complete", "succeeded", "success", "done"}:
        return "completed"
    if normalized in {"failed", "failure", "error", "cancelled", "canceled"}:
        return "failed"
    return None


def _redact(value: str) -> str:
    redacted = re.sub(
        r"(?i)(AWS_(?:ACCESS_KEY_ID|SECRET_ACCESS_KEY|SESSION_TOKEN)\s*=\s*)([^\s,\"']+)",
        r"\1[REDACTED]",
        value,
    )
    return re.sub(
        r"(?i)(api[_-]?key|token|secret|authorization)(\s*[:=]\s*)([^\s\"']+)",
        r"\1\2[REDACTED]",
        redacted,
    )


def _scenario_names_from_metrics(leaderboard: list[DetectorTournamentLeaderboardRow]) -> list[str]:
    return sorted({row.scenario for row in leaderboard}) or ["unknown"]


def _mock_tournament_response(
    request: DetectorTournamentStartRequest,
    *,
    tournament_id: str,
    started_at: str,
    completed_at: str,
    artifacts: dict[str, str],
    fallback_reason: str,
) -> DetectorTournamentResponse:
    scenarios = _scenario_names(request.manipulation_types)
    detectors = _detectors(request.detector_set)
    rows: list[DetectorTournamentLeaderboardRow] = []
    for scenario in scenarios:
        for detector in detectors:
            rows.append(
                DetectorTournamentLeaderboardRow(
                    detector=detector,
                    scenario=scenario,
                    precision=0.82,
                    recall=0.82,
                    f1=0.82,
                    false_positives=0,
                    false_negatives=1,
                    avg_detection_latency_ms=1200.0,
                )
            )
    return DetectorTournamentResponse(
        tournament_id=tournament_id,
        status="completed",
        execution_mode="local_mock",
        started_at=started_at,
        completed_at=completed_at,
        detectors=detectors,
        leaderboard=rows,
        metrics=_metrics_summary(rows, total_scenarios=request.number_of_scenarios),
        artifacts=artifacts,
        summary="Deterministic mock detector tournament completed after local runner fallback.",
        fallback_reason=fallback_reason,
    )


def _persist_tournament(store: LocalStore, response: DetectorTournamentResponse) -> None:
    payload = response.model_dump(mode="json")
    store.write_json(f"nebius/tournaments/{response.tournament_id}/tournament.json", payload)
    store.append_jsonl("nebius/tournaments.jsonl", payload)
    settings = get_settings()
    if response.execution_mode == "nebius_serverless_job" and settings.nebius_evidence_archive_enabled:
        try:
            NebiusEvidenceArchive(store, settings).record_job(
                operation=f"detector_tournament_{response.status}",
                run_id=response.tournament_id,
                status=response.status,
                payload=payload,
                artifact_paths=response.artifacts,
            )
        except (OSError, RuntimeError, ValueError):
            pass


def _leaderboard_from_metrics(path: Path) -> list[DetectorTournamentLeaderboardRow]:
    if not path.exists():
        return []
    rows: list[DetectorTournamentLeaderboardRow] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                DetectorTournamentLeaderboardRow(
                    detector=str(row.get("detector") or "unknown"),
                    scenario=str(row.get("scenario") or "unknown"),
                    precision=_nullable_float(row.get("precision")),
                    recall=_nullable_float(row.get("recall")),
                    f1=_nullable_float(row.get("f1")),
                    specificity=_nullable_float(row.get("specificity")),
                    false_positive_rate=_nullable_float(row.get("false_positive_rate")),
                    false_positives=int(_float(row.get("false_positive"))),
                    false_negatives=int(_float(row.get("false_negative"))),
                    avg_detection_latency_ms=_optional_float(row.get("avg_detection_latency_ms")),
                    runs=int(_float(row.get("runs"))),
                    temporal_overlap=_nullable_float(row.get("temporal_overlap")),
                    event_precision=_nullable_float(row.get("event_precision")),
                    event_recall=_nullable_float(row.get("event_recall")),
                    participant_precision=_nullable_float(row.get("participant_precision")),
                    participant_recall=_nullable_float(row.get("participant_recall")),
                    order_precision=_nullable_float(row.get("order_precision")),
                    order_recall=_nullable_float(row.get("order_recall")),
                )
            )
    return rows


def _metrics_summary(
    leaderboard: list[DetectorTournamentLeaderboardRow],
    *,
    total_scenarios: int,
) -> dict[str, Any]:
    f1_values = [row.f1 for row in leaderboard if row.f1 is not None]
    latencies = [row.avg_detection_latency_ms for row in leaderboard if row.avg_detection_latency_ms is not None]
    return {
        "total_scenarios": total_scenarios,
        "scenario_families": _scenario_names_from_metrics(leaderboard),
        "macro_f1": round(sum(f1_values) / len(f1_values), 4) if f1_values else None,
        "false_positives": sum(row.false_positives for row in leaderboard),
        "false_negatives": sum(row.false_negatives for row in leaderboard),
        "avg_detection_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
    }


def _artifact_paths(output_dir: Path) -> dict[str, str]:
    candidates = {
        "metrics": output_dir / "metrics.csv",
        "results": output_dir / "results.json",
        "report": output_dir / "benchmark_report.md",
        "f1_chart": output_dir / "charts" / "f1_by_scenario.png",
        "confidence_chart": output_dir / "charts" / "confidence_distribution.png",
        "latency_chart": output_dir / "charts" / "detection_latency.png",
    }
    return {name: str(path) for name, path in candidates.items() if path.exists()}


def _scenario_names(values: list[ManipulationType]) -> list[str]:
    return [str(value) for value in values] or ["spoofing_like_wall", "layering_like", "quote_stuffing", "liquidity_evaporation"]


def _detectors(values: list[DetectorName]) -> list[str]:
    return [str(value) for value in values] or ["spoofing_like", "layering_like", "quote_stuffing"]


def _parse_job_id(output: str) -> str | None:
    try:
        decoded = json.loads(output)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, dict):
        for key in ("job_id", "id", "jobId", "jobID"):
            value = decoded.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    match = re.search(
        r"\b(?:job[_ -]?id)\b\s*[:=]\s*([A-Za-z0-9_.:/-]+)",
        output,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1)
    for token in output.replace("\n", " ").split():
        if token.startswith(("aijob-", "job-", "jobs/", "NEB-")):
            return token.strip().strip(",")
    return None


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _optional_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    return _float(value)


def _nullable_float(value: Any) -> float | None:
    if value is None or str(value).strip().lower() in {"", "none", "null", "n/a"}:
        return None
    return _float(value)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
