import csv
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LocalSmartBatchResult:
    elapsed_seconds: float
    artifact_paths: dict[str, str]
    metrics: list[dict[str, Any]]
    command: list[str]
    stdout: str
    stderr: str
    returncode: int


def run_local_smart_batch(
    *,
    repo_root: Path,
    output_dir: Path,
    runs: int,
    batch_size: int,
    scenarios: list[str],
    timeout_seconds: int = 120,
) -> LocalSmartBatchResult:
    command = [
        sys.executable,
        str(repo_root / "serverless" / "jobs" / "run_batch_experiments.py"),
        "--runs",
        str(runs),
        "--batch-size",
        str(batch_size),
        "--scenarios",
        ",".join(scenarios),
        "--output",
        str(output_dir),
    ]
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
        cwd=repo_root,
        text=True,
        timeout=timeout_seconds,
    )
    elapsed = round(time.perf_counter() - started, 3)
    return LocalSmartBatchResult(
        elapsed_seconds=elapsed,
        artifact_paths=smart_batch_artifact_paths(output_dir),
        metrics=read_metrics(output_dir / "detector_metrics.csv"),
        command=command,
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )


def smart_batch_artifact_paths(output_dir: Path) -> dict[str, str]:
    return {
        "order_book_event_logs": str(output_dir / "order_book_events.jsonl"),
        "trades": str(output_dir / "trades.jsonl"),
        "attack_labels": str(output_dir / "attack_labels.jsonl"),
        "blue_team_alerts": str(output_dir / "blue_team_alerts.jsonl"),
        "detector_metrics": str(output_dir / "detector_metrics.csv"),
        "generated_report": str(output_dir / "generated_report.md"),
        "manifest": str(output_dir / "manifest.json"),
    }


def read_metrics(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
