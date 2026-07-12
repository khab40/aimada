import argparse
import csv
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _add_backend_to_path() -> None:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "backend",
        Path.cwd() / "backend",
        Path("/job/backend"),
    ]
    for candidate in candidates:
        if (candidate / "app").exists():
            sys.path.insert(0, str(candidate))
            return


_add_backend_to_path()

from app.arena.engine import SimulationEngine  # noqa: E402


SCENARIOS = ["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"]
SCENARIO_TO_ENGINE = {
    "normal_market": None,
    "spoofing": "spoofing-like",
    "layering": "layering-like",
    "quote_stuffing": "quote-stuffing",
    "pump_and_cancel": "liquidity-evaporation",
}


@dataclass
class BatchResult:
    run_id: str
    scenario: str
    events: list[dict[str, Any]]
    trades: list[dict[str, Any]]
    labels: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    metrics: dict[str, Any]
    report: str


def main() -> None:
    parser = argparse.ArgumentParser(description="Run parallel synthetic attack/detect batches.")
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--scenarios", default=",".join(SCENARIOS))
    parser.add_argument("--output", type=Path, default=Path("outputs/serverless-batch"))
    parser.add_argument("--s3-output-uri", default="")
    parser.add_argument("--s3-endpoint-url", default="")
    args = parser.parse_args()

    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    scenarios = [item.strip() for item in args.scenarios.split(",") if item.strip()]
    runs = max(1, args.runs)
    batch_size = max(1, min(args.batch_size, 500))

    results: list[BatchResult] = []
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = [
            executor.submit(_run_one, index, scenarios[index % len(scenarios)])
            for index in range(runs)
        ]
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: item.run_id)
    _write_jsonl(output / "order_book_events.jsonl", (row for result in results for row in result.events))
    _write_jsonl(output / "trades.jsonl", (row for result in results for row in result.trades))
    _write_jsonl(output / "attack_labels.jsonl", (row for result in results for row in result.labels))
    _write_jsonl(output / "blue_team_alerts.jsonl", (row for result in results for row in result.alerts))
    metrics = _aggregate_metrics(results)
    _write_metrics(output / "detector_metrics.csv", metrics)
    report = _build_report(results, metrics, batch_size)
    (output / "generated_report.md").write_text(report, encoding="utf-8")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runs": runs,
        "batch_size": batch_size,
        "scenarios": scenarios,
        "artifacts": {
            "order_book_event_logs": str(output / "order_book_events.jsonl"),
            "trades": str(output / "trades.jsonl"),
            "attack_labels": str(output / "attack_labels.jsonl"),
            "blue_team_alerts": str(output / "blue_team_alerts.jsonl"),
            "detector_metrics": str(output / "detector_metrics.csv"),
            "generated_report": str(output / "generated_report.md"),
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if args.s3_output_uri:
        _sync_to_s3(output, args.s3_output_uri, args.s3_endpoint_url)
    print(json.dumps(manifest, indent=2))


def _run_one(index: int, scenario: str) -> BatchResult:
    run_id = f"batch-{index:06d}"
    engine = SimulationEngine(seed=10_000 + index)
    engine_scenario = SCENARIO_TO_ENGINE.get(scenario)
    if engine_scenario is not None:
        engine.launch_scenario(engine_scenario)

    events: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    labels: dict[str, dict[str, Any]] = {}
    alerts: dict[str, dict[str, Any]] = {}
    max_confidence = 0.0
    detected_pattern = "normal_market"
    first_alert_tick: int | None = None

    for _ in range(16):
        state = engine.step()
        for event in state["events"][:8]:
            row = dict(event)
            row["run_id"] = run_id
            row["tick"] = state["tick"]
            events.append(row)
            if row.get("type") == "trade" or "trade" in str(row.get("message", "")).lower():
                trades.append(row)
        active = state.get("active_scenario")
        if active and active.get("label"):
            labels[str(active["label"]["label_id"])] = {"run_id": run_id, **active["label"]}
        for score in state["detectors"]["scores"]:
            confidence = float(score["confidence"])
            if confidence > max_confidence:
                max_confidence = confidence
                detected_pattern = str(score["name"])
            if confidence >= 0.75:
                alert_id = f"{run_id}-{score['name']}"
                alerts[alert_id] = {
                    "alert_id": alert_id,
                    "run_id": run_id,
                    "tick": state["tick"],
                    "scenario": scenario,
                    "detector": score["name"],
                    "confidence": confidence,
                    "evidence": score.get("evidence") or [],
                }
                first_alert_tick = first_alert_tick or int(state["tick"])

    metrics = {
        "run_id": run_id,
        "scenario": scenario,
        "detected_pattern": detected_pattern,
        "max_confidence": round(max_confidence, 4),
        "alert_count": len(alerts),
        "first_alert_tick": first_alert_tick,
        "detected": bool(alerts),
    }
    return BatchResult(
        run_id=run_id,
        scenario=scenario,
        events=events,
        trades=trades,
        labels=list(labels.values())
        or [{"run_id": run_id, "scenario": scenario, "scenario_family": scenario, "has_attack": scenario != "normal_market"}],
        alerts=list(alerts.values()),
        metrics=metrics,
        report=f"{run_id}: {scenario} -> {detected_pattern} at confidence {max_confidence:.2f}",
    )


def _aggregate_metrics(results: list[BatchResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_scenario: dict[str, list[BatchResult]] = {}
    for result in results:
        by_scenario.setdefault(result.scenario, []).append(result)

    for scenario, scenario_results in sorted(by_scenario.items()):
        attack = scenario != "normal_market"
        detections = sum(1 for result in scenario_results if result.metrics["detected"])
        precision = 1.0 if attack and detections else 0.0 if detections else 1.0
        recall = detections / len(scenario_results) if attack else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        alert_ticks = [
            result.metrics["first_alert_tick"]
            for result in scenario_results
            if result.metrics["first_alert_tick"] is not None
        ]
        rows.append(
            {
                "scenario": scenario,
                "runs": len(scenario_results),
                "alerts": detections,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "avg_detection_latency_ms": round((sum(alert_ticks) / len(alert_ticks)) * 500, 2)
                if alert_ticks
                else "",
            }
        )
    return rows


def _write_jsonl(path: Path, rows: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(_drop_nulls(row)) + "\n")


def _drop_nulls(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value is not None}


def _write_metrics(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["scenario", "runs", "alerts", "precision", "recall", "f1", "avg_detection_latency_ms"],
        )
        writer.writeheader()
        writer.writerows(rows)


def _sync_to_s3(output: Path, s3_output_uri: str, endpoint_url: str) -> None:
    command = ["aws"]
    if endpoint_url:
        command.extend(["--endpoint-url", endpoint_url])
    command.extend(["s3", "sync", str(output), s3_output_uri.rstrip("/"), "--only-show-errors"])
    env = os.environ.copy()
    env.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    completed = subprocess.run(command, capture_output=True, check=False, text=True, timeout=300, env=env)
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"S3 artifact upload failed: {details}")


def _build_report(results: list[BatchResult], metrics: list[dict[str, Any]], batch_size: int) -> str:
    lines = [
        "# Smart Attack/Detect Batch Report",
        "",
        "Educational synthetic simulation only. Not for real market surveillance, trading, or compliance use.",
        "",
        f"- Simulations: {len(results)}",
        f"- Parallel batch size: {batch_size}",
        "- Output files: 6",
        "",
        "| Scenario | Runs | Alerts | Precision | Recall | F1 | Avg latency ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in metrics:
        lines.append(
            f"| {row['scenario']} | {row['runs']} | {row['alerts']} | {row['precision']} | "
            f"{row['recall']} | {row['f1']} | {row['avg_detection_latency_ms'] or 'n/a'} |"
        )
    lines.extend(["", "## Sample Reports", ""])
    for result in results[:12]:
        lines.append(f"- {result.report}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
