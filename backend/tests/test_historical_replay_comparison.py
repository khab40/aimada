import hashlib
from pathlib import Path

from scripts.run_historical_replay_comparison import build_comparison, write_bundle


def _raw_comparison() -> dict[str, object]:
    control = {
        "source_row_count": 12,
        "source_rows_replayed": 12,
        "events_sha256": "fixture-sha",
        "canonical_event_count": 15,
        "detector_alert_ticks": {},
        "ground_truth": None,
    }
    hybrid = {
        "source_row_count": 12,
        "source_rows_replayed": 12,
        "events_sha256": "fixture-sha",
        "canonical_event_count": 20,
        "detector_alert_ticks": {"spoofing_like_detector": [1]},
        "ground_truth": {"has_attack": True},
    }
    return {
        "dataset_id": "sample-btcusdt-0945",
        "events_sha256": "fixture-sha",
        "control": control,
        "hybrid": hybrid,
        "realism_impact": {
            "canonical_event_count_delta": 5,
            "final_depth_delta": 1.0,
            "final_spread_delta": 0.0,
        },
    }


def test_builds_metrics_without_treating_control_history_as_ground_truth() -> None:
    comparison = build_comparison(_raw_comparison())
    spoofing = next(
        row for row in comparison["detector_metrics"] if row["detector"] == "spoofing_like_detector"
    )

    assert comparison["same_historical_window"] is True
    assert spoofing["true_positive"] == 1
    assert spoofing["false_positive"] == 0
    assert spoofing["false_negative"] == 0
    assert spoofing["true_negative"] == 1
    assert spoofing["precision"] == 1.0
    assert spoofing["recall"] == 1.0
    assert spoofing["f1"] == 1.0
    assert spoofing["hybrid_evaluation"]["detection_timing"] == "not_applicable"

    missed = next(
        row for row in comparison["detector_metrics"] if row["detector"] == "layering_like_detector"
    )
    assert missed["true_positive"] == 0
    assert missed["false_positive"] == 0
    assert missed["false_negative"] == 1
    assert missed["true_negative"] == 1
    assert missed["precision"] is None
    assert missed["recall"] == 0.0
    assert missed["f1"] == 0.0


def test_writes_deterministic_manifest_and_checksums(tmp_path: Path) -> None:
    write_bundle(_raw_comparison(), tmp_path)

    assert {path.name for path in tmp_path.iterdir()} == {
        "control.json",
        "hybrid.json",
        "comparison.json",
        "manifest.json",
        "checksums.sha256",
    }
    for line in (tmp_path / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == expected
