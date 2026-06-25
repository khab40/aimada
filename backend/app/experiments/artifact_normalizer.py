import json
import shutil
from pathlib import Path

from pydantic import BaseModel, Field


ARTIFACT_MAPPINGS = {
    "events": ("order_book_events.jsonl", "events.jsonl"),
    "trades": ("trades.jsonl", "trades.jsonl"),
    "labels": ("attack_labels.jsonl", "labels.jsonl"),
    "alerts": ("blue_team_alerts.jsonl", "alerts.jsonl"),
    "detector_metrics": ("detector_metrics.csv", "detector_metrics.csv"),
    "benchmark_report": ("generated_report.md", "benchmark_report.md"),
    "batch_manifest": ("manifest.json", "batch_manifest.json"),
}


class ArtifactIndexEntry(BaseModel):
    key: str
    source_path: str
    normalized_path: str
    exists: bool


class ArtifactNormalizationResponse(BaseModel):
    experiment_id: str
    artifact_dir: str
    artifact_paths: dict[str, str]
    copied_count: int
    missing: list[str] = Field(default_factory=list)


def normalize_local_batch_artifacts(experiment_id: str, artifact_dir: Path) -> ArtifactNormalizationResponse:
    local_batch_dir = artifact_dir / "local-batch"
    if not local_batch_dir.exists() or not local_batch_dir.is_dir():
        raise ValueError(f"local batch artifacts not found for experiment: {experiment_id}")

    entries: list[ArtifactIndexEntry] = []
    normalized_paths: dict[str, str] = {}
    missing: list[str] = []
    copied_count = 0

    for key, (source_name, target_name) in ARTIFACT_MAPPINGS.items():
        source = local_batch_dir / source_name
        target = artifact_dir / target_name
        exists = source.exists() and source.is_file()
        if exists:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            copied_count += 1
            normalized_paths[key] = str(target)
        else:
            missing.append(source_name)
        entries.append(
            ArtifactIndexEntry(
                key=key,
                source_path=str(source),
                normalized_path=str(target),
                exists=exists,
            )
        )

    artifact_index = artifact_dir / "artifact_index.json"
    index_payload = {
        "experiment_id": experiment_id,
        "source_dir": str(local_batch_dir),
        "artifact_dir": str(artifact_dir),
        "artifacts": [entry.model_dump(mode="json") for entry in entries],
        "missing": missing,
    }
    artifact_index.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")
    normalized_paths["artifact_index"] = str(artifact_index)

    return ArtifactNormalizationResponse(
        experiment_id=experiment_id,
        artifact_dir=str(artifact_dir),
        artifact_paths=normalized_paths,
        copied_count=copied_count,
        missing=missing,
    )
