import argparse
import csv
import json
import sys
import struct
import zlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


def _add_backend_to_path() -> None:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "backend",
        Path.cwd() / "backend",
        Path.cwd(),
    ]
    for candidate in candidates:
        if (candidate / "app").exists():
            sys.path.insert(0, str(candidate))
            return


_add_backend_to_path()

from app.arena.engine import SimulationEngine  # noqa: E402


SCENARIO_ALIASES = {
    "spoofing": "spoofing-like",
    "spoofing_like": "spoofing-like",
    "spoofing_like_wall": "spoofing-like",
    "layering": "layering-like",
    "layering_like": "layering-like",
    "quote_stuffing": "quote-stuffing",
    "quote-stuffing": "quote-stuffing",
    "liquidity_evaporation": "liquidity-evaporation",
    "liquidity-evaporation": "liquidity-evaporation",
    "normal": "normal-market",
    "normal_market": "normal-market",
    "normal-market": "normal-market",
    "pump_and_cancel": "pump-and-cancel",
    "pump-and-cancel": "pump-and-cancel",
}

EXPECTED_DETECTORS = {
    "spoofing-like": "spoofing_like",
    "layering-like": "layering_like",
    "quote-stuffing": "quote_stuffing",
    "liquidity-evaporation": "liquidity_shock",
    "pump-and-cancel": "liquidity_shock",
}

DEFAULT_SCENARIOS = [
    "normal-market",
    "spoofing-like",
    "layering-like",
    "quote-stuffing",
    "pump-and-cancel",
]
DEFAULT_DETECTORS = ["spoofing_like", "layering_like", "quote_stuffing", "liquidity_shock"]


@dataclass
class RunResult:
    run_id: str
    scenario: str
    detector: str
    expected_detector: str
    predicted: bool
    truth: bool
    true_positive: int
    false_positive: int
    false_negative: int
    latency_ms: float | None
    max_confidence: float


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a synthetic detector tournament benchmark.")
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--scenarios", default=",".join(DEFAULT_SCENARIOS))
    parser.add_argument("--detectors", default=",".join(DEFAULT_DETECTORS))
    parser.add_argument("--output", type=Path, default=Path("outputs/benchmark"))
    args = parser.parse_args()

    scenarios = [_normalize_scenario(item) for item in _split_csv(args.scenarios)]
    detectors = [_normalize_detector(item) for item in _split_csv(args.detectors)]
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    run_results: list[RunResult] = []
    for run_index in range(args.runs):
        for scenario in scenarios:
            run_results.extend(_run_one_simulation(run_index, scenario, detectors))

    metrics = _compute_metrics(run_results, detectors)
    _write_metrics_csv(output_dir / "metrics.csv", metrics)
    _write_results_json(output_dir / "results.json", args.runs, scenarios, detectors, metrics, run_results)
    _write_report(output_dir / "benchmark_report.md", args.runs, scenarios, detectors, metrics)
    _write_charts(output_dir / "charts", metrics)

    print(json.dumps({"runs": args.runs, "scenarios": scenarios, "detectors": detectors, "output": str(output_dir)}, indent=2))


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_scenario(value: str) -> str:
    key = value.strip().lower().replace(" ", "_")
    return SCENARIO_ALIASES.get(key, key.replace("_", "-"))


def _normalize_detector(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _run_one_simulation(run_index: int, scenario: str, detectors: list[str]) -> list[RunResult]:
    engine = SimulationEngine(seed=run_index + 17)
    if scenario == "pump-and-cancel":
        engine.launch_scenario("liquidity-evaporation")
    elif scenario != "normal-market":
        engine.launch_scenario(scenario)
    expected_detector = EXPECTED_DETECTORS.get(scenario, "")
    first_alert_tick: dict[str, int] = {}
    max_confidence: dict[str, float] = defaultdict(float)
    incident_detectors: set[str] = set()

    for _ in range(14):
        state = engine.step()
        for score in state["detectors"]["scores"]:
            detector_name = score["name"]
            confidence = float(score["confidence"])
            max_confidence[detector_name] = max(max_confidence[detector_name], confidence)
            if confidence >= 0.75 and detector_name not in first_alert_tick:
                first_alert_tick[detector_name] = int(state["tick"])
        for incident in state.get("incidents", []):
            incident_detectors.add(str(incident["type"]))

    results: list[RunResult] = []
    for detector in detectors:
        truth = bool(expected_detector) and detector == expected_detector
        predicted = detector in incident_detectors or max_confidence[detector] >= 0.75
        true_positive = int(truth and predicted)
        false_positive = int(not truth and predicted)
        false_negative = int(truth and not predicted)
        latency_ms = None
        if detector in first_alert_tick:
            latency_ms = max(0, first_alert_tick[detector] - 1) * engine.tick_interval_seconds * 1000
        results.append(
            RunResult(
                run_id=f"run-{run_index:05d}",
                scenario=scenario,
                detector=detector,
                expected_detector=expected_detector,
                predicted=predicted,
                truth=truth,
                true_positive=true_positive,
                false_positive=false_positive,
                false_negative=false_negative,
                latency_ms=latency_ms,
                max_confidence=round(max_confidence[detector], 4),
            )
        )
    return results


def _compute_metrics(run_results: list[RunResult], detectors: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    groups: dict[tuple[str, str], list[RunResult]] = defaultdict(list)
    for result in run_results:
        groups[(result.scenario, result.detector)].append(result)

    for (scenario, detector), results in sorted(groups.items()):
        if detector not in detectors:
            continue
        tp = sum(item.true_positive for item in results)
        fp = sum(item.false_positive for item in results)
        fn = sum(item.false_negative for item in results)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        latencies = [item.latency_ms for item in results if item.latency_ms is not None and item.truth]
        rows.append(
            {
                "scenario": scenario,
                "detector": detector,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "avg_detection_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "runs": len(results),
            }
        )
    return rows


def _write_metrics_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "scenario",
        "detector",
        "precision",
        "recall",
        "f1",
        "avg_detection_latency_ms",
        "true_positive",
        "false_positive",
        "false_negative",
        "runs",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_results_json(
    path: Path,
    runs: int,
    scenarios: list[str],
    detectors: list[str],
    metrics: list[dict[str, object]],
    run_results: list[RunResult],
) -> None:
    path.write_text(
        json.dumps(
            {
                "runs": runs,
                "scenarios": scenarios,
                "detectors": detectors,
                "metrics": metrics,
                "run_results": [result.__dict__ for result in run_results],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_report(
    path: Path,
    runs: int,
    scenarios: list[str],
    detectors: list[str],
    metrics: list[dict[str, object]],
) -> None:
    lines = [
        "# Detector Tournament Benchmark",
        "",
        "Educational synthetic benchmark. These results do not represent real market surveillance performance.",
        "",
        f"- Runs per scenario: {runs}",
        f"- Scenarios: {', '.join(scenarios)}",
        f"- Detectors: {', '.join(detectors)}",
        "",
        "| Scenario | Detector | Precision | Recall | F1 | Avg Latency ms |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in metrics:
        latency = row["avg_detection_latency_ms"]
        lines.append(
            f"| {row['scenario']} | {row['detector']} | {row['precision']} | {row['recall']} | "
            f"{row['f1']} | {latency if latency is not None else 'n/a'} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_charts(output_dir: Path, metrics: list[dict[str, object]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    expected_rows = [
        row
        for row in metrics
        if EXPECTED_DETECTORS.get(str(row["scenario"])) == row["detector"]
        or str(row["scenario"]) == "normal-market"
    ]
    _write_bar_chart(
        output_dir / "f1_by_scenario.png",
        [(str(row["scenario"]), float(row["f1"])) for row in expected_rows],
        "F1 by Scenario",
        value_max=1.0,
    )
    _write_bar_chart(
        output_dir / "confidence_distribution.png",
        [(str(row["scenario"]), float(row["precision"])) for row in expected_rows],
        "Precision by Scenario",
        value_max=1.0,
    )
    _write_bar_chart(
        output_dir / "detection_latency.png",
        [
            (str(row["scenario"]), float(row["avg_detection_latency_ms"] or 0.0))
            for row in expected_rows
        ],
        "Detection Latency",
        value_max=None,
    )


def _write_bar_chart(
    path: Path,
    values: list[tuple[str, float]],
    title: str,
    *,
    value_max: float | None,
) -> None:
    width = 920
    height = 420
    image = bytearray([7, 13, 20] * width * height)

    def pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 3
            image[offset : offset + 3] = bytes(color)

    def rect(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        for y in range(max(0, y0), min(height, y1)):
            for x in range(max(0, x0), min(width, x1)):
                pixel(x, y, color)

    rect(0, 0, width, height, (7, 13, 20))
    for y in range(70, 340, 54):
        rect(80, y, width - 40, y + 1, (27, 52, 77))

    if not values:
        _write_png(path, width, height, bytes(image))
        return

    max_value = value_max or max(value for _, value in values) or 1.0
    bar_width = max(24, min(96, int((width - 140) / max(len(values), 1) * 0.62)))
    gap = int((width - 140 - bar_width * len(values)) / max(len(values), 1))
    x = 90
    for index, (_, value) in enumerate(values):
        bar_height = int(250 * (value / max_value)) if max_value else 0
        color = [(34, 211, 238), (34, 171, 148), (245, 184, 65), (242, 54, 69)][index % 4]
        rect(x, 340 - bar_height, x + bar_width, 340, color)
        rect(x, 340 - bar_height, x + bar_width, 340 - bar_height + 3, (216, 243, 255))
        x += bar_width + max(18, gap)

    # Tiny title stripe. Text labels stay in CSV/report; this PNG is a lightweight visual artifact.
    rect(80, 35, min(width - 40, 80 + len(title) * 9), 41, (34, 211, 238))
    _write_png(path, width, height, bytes(image))


def _write_png(path: Path, width: int, height: int, rgb: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw_rows = []
    stride = width * 3
    for y in range(height):
        raw_rows.append(b"\x00" + rgb[y * stride : (y + 1) * stride])
    payload = b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            chunk(b"IDAT", zlib.compress(b"".join(raw_rows), 9)),
            chunk(b"IEND", b""),
        ]
    )
    path.write_bytes(payload)


if __name__ == "__main__":
    main()
