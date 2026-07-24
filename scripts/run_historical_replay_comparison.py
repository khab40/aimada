import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.ground_truth import binary_classification_metrics, evaluate_detection  # noqa: E402


def build_comparison(raw: dict[str, Any]) -> dict[str, Any]:
    control = raw["control"]
    hybrid = raw["hybrid"]
    detector_names = sorted(
        set(control.get("detector_alert_ticks", {}))
        | set(hybrid.get("detector_alert_ticks", {}))
        | {
            "spoofing_like_detector",
            "layering_like_detector",
            "quote_stuffing_detector",
            "liquidity_shock_detector",
        }
    )
    metrics: list[dict[str, Any]] = []
    for detector in detector_names:
        control_predicted = bool(control.get("detector_alert_ticks", {}).get(detector))
        hybrid_predicted = bool(hybrid.get("detector_alert_ticks", {}).get(detector))
        control_ticks = control.get("detector_alert_ticks", {}).get(detector, [])
        hybrid_ticks = hybrid.get("detector_alert_ticks", {}).get(detector, [])
        classification = binary_classification_metrics(
            tp=int(hybrid_predicted),
            fp=int(control_predicted),
            fn=int(not hybrid_predicted),
            tn=int(not control_predicted),
        )
        metrics.append(
            {
                "detector": detector,
                **classification,
                "control_alert_ticks": control_ticks,
                "hybrid_alert_ticks": hybrid_ticks,
                "control_evaluation": evaluate_detection(alert_ticks=control_ticks, label=None),
                "hybrid_evaluation": evaluate_detection(
                    alert_ticks=hybrid_ticks,
                    label=hybrid.get("ground_truth"),
                ),
            }
        )
    return {
        "schema_version": "historical_replay_metrics_v1",
        "dataset_id": raw["dataset_id"],
        "master_seed": raw.get("master_seed", 42),
        "events_sha256": raw["events_sha256"],
        "same_historical_window": (
            control["source_rows_replayed"] == hybrid["source_rows_replayed"]
            and control["events_sha256"] == raw["events_sha256"]
            and hybrid["events_sha256"] == raw["events_sha256"]
        ),
        "event_counts": {
            "control": control["canonical_event_count"],
            "hybrid": hybrid["canonical_event_count"],
            "delta": raw["realism_impact"]["canonical_event_count_delta"],
        },
        "detector_metrics": metrics,
        "realism_impact": raw["realism_impact"],
    }


def write_bundle(raw: dict[str, Any], output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    comparison = build_comparison(raw)
    artifacts = {
        "control.json": raw["control"],
        "hybrid.json": raw["hybrid"],
        "comparison.json": comparison,
    }
    for name, payload in artifacts.items():
        _write_json(output / name, payload)
    manifest = {
        "schema_version": "historical_replay_bundle_v1",
        "dataset_id": raw["dataset_id"],
        "master_seed": raw.get("master_seed", 42),
        "events_sha256": raw["events_sha256"],
        "artifacts": sorted(artifacts),
    }
    _write_json(output / "manifest.json", manifest)
    checksum_files = [*sorted(artifacts), "manifest.json"]
    (output / "checksums.sha256").write_text(
        "".join(f"{_sha256(output / name)}  {name}\n" for name in checksum_files),
        encoding="utf-8",
    )
    return comparison


def run(args: argparse.Namespace) -> dict[str, Any]:
    payload = json.dumps(
        {
            "dataset_id": args.dataset,
            "scenario_family": args.scenario,
            "max_ticks": args.max_ticks,
            "master_seed": args.master_seed,
        }
    ).encode()
    request = urllib.request.Request(
        f"{args.base_url.rstrip('/')}/api/arena/replay-comparison",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            raw = json.load(response)
    except urllib.error.URLError as exception:
        raise SystemExit(f"historical replay request failed: {exception}") from exception
    return write_bundle(raw, args.output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Java historical control and hybrid replay and write checksummed comparison artifacts."
    )
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--dataset", default="sample-btcusdt-0945")
    parser.add_argument("--scenario", default="spoofing_like_wall")
    parser.add_argument("--max-ticks", type=int, default=10_000)
    parser.add_argument("--master-seed", type=int, default=42)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "historical-replay")
    return parser.parse_args()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))
