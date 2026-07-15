import csv
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class LeaderboardRow(BaseModel):
    scenario: str
    detector: str = "built-in detector suite"
    model: str = "none (deterministic)"
    precision: float | None
    recall: float | None
    f1: float | None
    specificity: float | None = None
    false_positive_rate: float | None = None
    avg_detection_latency_ms: float | None = None
    alert_count: int


class ExperimentSummary(BaseModel):
    experiment_id: str
    total_attacks: int
    total_alerts: int
    scenarios: list[str]
    precision_by_scenario: dict[str, float | None]
    recall_by_scenario: dict[str, float | None]
    f1_by_scenario: dict[str, float | None]
    avg_detection_latency_ms: float | None = None
    investigation_count: int
    failed_runs: int
    artifact_paths: dict[str, str] = Field(default_factory=dict)


class AggregationResult(BaseModel):
    summary: ExperimentSummary
    leaderboard: list[LeaderboardRow]
    report_path: str


def aggregate_experiment(experiment_id: str, artifact_dir: Path) -> AggregationResult:
    metrics_path = _first_existing(artifact_dir / "detector_metrics.csv", artifact_dir / "local-batch" / "detector_metrics.csv")
    alerts_path = _first_existing(artifact_dir / "alerts.jsonl", artifact_dir / "local-batch" / "blue_team_alerts.jsonl")
    labels_path = _first_existing(artifact_dir / "labels.jsonl", artifact_dir / "local-batch" / "attack_labels.jsonl")

    metric_rows = _read_metrics(metrics_path)
    alert_rows = _read_jsonl(alerts_path)
    label_rows = _read_jsonl(labels_path)
    investigation_count = len(list((artifact_dir / "investigations").glob("*.json"))) if (artifact_dir / "investigations").exists() else 0
    failed_runs = _failed_runs(artifact_dir)
    leaderboard = [_leaderboard_row(row) for row in metric_rows]
    scenarios = [row.scenario for row in leaderboard] or sorted({str(row.get("scenario")) for row in label_rows if row.get("scenario")})
    avg_latency = _average([row.avg_detection_latency_ms for row in leaderboard if row.avg_detection_latency_ms is not None])

    artifact_paths = {
        "experiment_summary": str(artifact_dir / "experiment_summary.json"),
        "leaderboard": str(artifact_dir / "leaderboard.json"),
        "benchmark_report": str(artifact_dir / "benchmark_report.md"),
    }
    if metrics_path is not None:
        artifact_paths["detector_metrics"] = str(metrics_path)
    if alerts_path is not None:
        artifact_paths["alerts"] = str(alerts_path)
    if labels_path is not None:
        artifact_paths["labels"] = str(labels_path)

    summary = ExperimentSummary(
        experiment_id=experiment_id,
        total_attacks=sum(1 for row in label_rows if bool(row.get("has_attack", True))),
        total_alerts=len(alert_rows),
        scenarios=scenarios,
        precision_by_scenario={row.scenario: row.precision for row in leaderboard},
        recall_by_scenario={row.scenario: row.recall for row in leaderboard},
        f1_by_scenario={row.scenario: row.f1 for row in leaderboard},
        avg_detection_latency_ms=avg_latency,
        investigation_count=investigation_count,
        failed_runs=failed_runs,
        artifact_paths=artifact_paths,
    )
    (artifact_dir / "experiment_summary.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    (artifact_dir / "leaderboard.json").write_text(
        json.dumps([row.model_dump(mode="json") for row in leaderboard], indent=2),
        encoding="utf-8",
    )
    report = _markdown_report(summary, leaderboard)
    (artifact_dir / "benchmark_report.md").write_text(report, encoding="utf-8")
    return AggregationResult(summary=summary, leaderboard=leaderboard, report_path=str(artifact_dir / "benchmark_report.md"))


def load_summary(artifact_dir: Path) -> ExperimentSummary | None:
    path = artifact_dir / "experiment_summary.json"
    if not path.exists():
        return None
    return ExperimentSummary.model_validate_json(path.read_text(encoding="utf-8"))


def load_leaderboard(artifact_dir: Path) -> list[LeaderboardRow] | None:
    path = artifact_dir / "leaderboard.json"
    if not path.exists():
        return None
    decoded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(decoded, list):
        return []
    return [LeaderboardRow.model_validate(row) for row in decoded if isinstance(row, dict)]


def report_path(artifact_dir: Path) -> Path:
    return artifact_dir / "benchmark_report.md"


def _leaderboard_row(row: dict[str, str]) -> LeaderboardRow:
    return LeaderboardRow(
        scenario=str(row.get("scenario") or "unknown"),
        detector=str(row.get("detector") or "built-in detector suite"),
        model=str(row.get("model") or "none (deterministic)"),
        precision=_optional_float(row.get("precision")),
        recall=_optional_float(row.get("recall")),
        f1=_optional_float(row.get("f1")),
        specificity=_optional_float(row.get("specificity")),
        false_positive_rate=_optional_float(row.get("false_positive_rate")),
        avg_detection_latency_ms=_optional_float(row.get("avg_detection_latency_ms")),
        alert_count=int(_float(row.get("alerts"))),
    )


def _read_metrics(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        decoded = json.loads(line)
        if isinstance(decoded, dict):
            rows.append(decoded)
    return rows


def _failed_runs(artifact_dir: Path) -> int:
    jobs_path = artifact_dir / "jobs.jsonl"
    if not jobs_path.exists():
        return 0
    latest_by_batch: dict[tuple[object, object, object], dict[str, Any]] = {}
    for row in _read_jsonl(jobs_path):
        batch = (row.get("backend"), row.get("batch_start"), row.get("batch_end"))
        latest_by_batch[batch] = row
    return sum(1 for row in latest_by_batch.values() if row.get("status") == "failed")


def _markdown_report(summary: ExperimentSummary, leaderboard: list[LeaderboardRow]) -> str:
    lines = [
        f"# Experiment Benchmark Report: {summary.experiment_id}",
        "",
        f"- Total attacks: {summary.total_attacks}",
        f"- Total alerts: {summary.total_alerts}",
        f"- Investigation reports: {summary.investigation_count}",
        f"- Failed runs: {summary.failed_runs}",
        f"- Average detection latency ms: {summary.avg_detection_latency_ms if summary.avg_detection_latency_ms is not None else 'n/a'}",
        "",
        "| Scenario | Detector | Model | Precision | Recall | F1 | Avg latency ms | Alerts |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in leaderboard:
        latency = row.avg_detection_latency_ms if row.avg_detection_latency_ms is not None else "n/a"
        lines.append(
            f"| {row.scenario} | {row.detector} | {row.model} | {_metric(row.precision)} | "
            f"{_metric(row.recall)} | {_metric(row.f1)} | {latency} | {row.alert_count} |"
        )
    lines.append("")
    return "\n".join(lines)


def _first_existing(*paths: Path) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _optional_float(value: object) -> float | None:
    if value in {None, ""}:
        return None
    return _float(value)


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _metric(value: float | None) -> float | str:
    return value if value is not None else "n/a"
