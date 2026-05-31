def build_benchmark_report(
    run_count: int,
    detections: list[dict[str, object]],
    labels: list[dict[str, object]],
) -> dict[str, object]:
    true_positive = min(len(detections), len(labels))
    false_positive = max(len(detections) - len(labels), 0)
    false_negative = max(len(labels) - len(detections), 0)
    precision = true_positive / len(detections) if detections else 0.0
    recall = true_positive / len(labels) if labels else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "run_count": run_count,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive": false_positive,
        "false_negative": false_negative,
    }
