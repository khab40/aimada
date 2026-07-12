from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _non_empty(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"missing or empty artifact: {path}")
    return path


def _json_object(path: Path) -> dict[str, Any]:
    value = json.loads(_non_empty(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    status = value.get("status")
    if isinstance(status, str) and status.lower() in {"failed", "error"}:
        raise ValueError(f"artifact reports failed status: {path}")
    return value


def _jsonl(path: Path) -> None:
    rows = 0
    with _non_empty(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
            rows += 1
    if rows == 0:
        raise ValueError(f"JSONL artifact has no rows: {path}")


def _csv(path: Path) -> None:
    with _non_empty(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"CSV artifact has no data rows: {path}")


def validate(root: Path) -> None:
    dataset = root / "synthetic-dataset"
    benchmark = root / "benchmark"
    batch = root / "serverless-batch"

    dataset_manifest = _json_object(dataset / "manifest.json")
    batch_manifest = _json_object(batch / "manifest.json")
    benchmark_results = _json_object(benchmark / "results.json")

    if int(dataset_manifest.get("samples", 0)) < 1:
        raise ValueError("dataset manifest has no samples")
    if int(batch_manifest.get("runs", 0)) < 1:
        raise ValueError("batch manifest has no runs")
    if int(benchmark_results.get("runs", 0)) < 1:
        raise ValueError("benchmark results have no runs")

    for path in (
        dataset / "events.jsonl",
        dataset / "labels.jsonl",
        batch / "order_book_events.jsonl",
        batch / "attack_labels.jsonl",
        batch / "blue_team_alerts.jsonl",
    ):
        _jsonl(path)

    _csv(benchmark / "metrics.csv")
    _csv(batch / "detector_metrics.csv")
    _non_empty(benchmark / "benchmark_report.md")
    _non_empty(batch / "generated_report.md")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate deterministic AIMADA CI evaluation artifacts.")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    validate(args.root)
    print(f"Validated deterministic artifacts under {args.root}")


if __name__ == "__main__":
    main()
