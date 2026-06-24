from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


ExperimentStatus = Literal["draft", "manifest_generated", "submitted", "running", "completed", "failed"]
NebiusMode = Literal["mock", "local_parallel_batch", "real_nebius_pending"]


class ExperimentCreateRequest(BaseModel):
    name: str = Field(default="Detector batch experiment", min_length=1, max_length=160)
    attack_count: int = Field(default=100, ge=1, le=1000)
    batch_size: int = Field(default=100, ge=1, le=500)
    scenarios: list[str] = Field(
        default_factory=lambda: ["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"]
    )
    seed: int = Field(default=42, ge=0)
    nebius_mode: NebiusMode = "local_parallel_batch"


class Experiment(BaseModel):
    id: str
    name: str
    status: ExperimentStatus
    attack_count: int
    batch_size: int
    scenarios: list[str]
    seed: int
    nebius_mode: NebiusMode
    smart_batch_id: str | None = None
    artifact_dir: str
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str


class ExperimentDeleteResponse(BaseModel):
    id: str
    deleted: bool


class ExperimentLocalBatchRunResponse(BaseModel):
    id: str
    experiment_id: str
    mode: Literal["local_parallel_batch"]
    status: Literal["completed", "failed"]
    created_at: str
    elapsed_seconds: float
    runs: int
    batch_size: int
    scenarios: list[str]
    artifact_paths: dict[str, str]
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    error: dict[str, Any] | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
