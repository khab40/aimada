from typing import Any


def binary_classification_metrics(*, tp: int, fp: int, fn: int, tn: int) -> dict[str, float | int | None]:
    """Return the canonical deterministic binary detector metrics."""
    if min(tp, fp, fn, tn) < 0:
        raise ValueError("confusion-matrix counts must be non-negative")
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else 0.0 if recall == 0
        else None
    )
    specificity = tn / (tn + fp) if tn + fp else None
    false_positive_rate = fp / (fp + tn) if fp + tn else None
    return {
        "precision": _rounded(precision),
        "recall": _rounded(recall),
        "f1": _rounded(f1),
        "specificity": _rounded(specificity),
        "false_positive_rate": _rounded(false_positive_rate),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
    }


def evaluate_detection(
    *,
    alert_ticks: list[int],
    label: dict[str, Any] | None,
    predicted_participant_ids: set[str] | None = None,
    predicted_order_ids: set[str] | None = None,
    predicted_event_ids: set[str] | None = None,
) -> dict[str, Any]:
    unique_alerts = set(alert_ticks)
    if label is None:
        return {
            "temporal_overlap": None,
            "event_precision": None,
            "event_recall": None,
            "detection_timing": "false_positive" if unique_alerts else "not_applicable",
            "participant_precision": None,
            "participant_recall": None,
            "order_precision": None,
            "order_recall": None,
            "phase_detection": {},
        }

    window = _primary_window(label)
    positive_ticks = set(range(window[0], window[1] + 1)) if window else set()
    overlapping = unique_alerts & positive_ticks
    union = unique_alerts | positive_ticks
    first_alert = min(unique_alerts) if unique_alerts else None
    if first_alert is None:
        timing = "missed"
    elif window is None:
        timing = "not_applicable"
    elif first_alert < window[0]:
        timing = "early"
    elif first_alert <= window[1]:
        timing = "on_time"
    else:
        timing = "late"

    participant_metrics = _attribution(
        predicted_participant_ids or set(),
        {str(value) for value in label.get("agent_ids", [])},
    )
    order_metrics = _attribution(
        predicted_order_ids or set(),
        {str(value) for value in label.get("order_ids", [])},
    )
    event_metrics = _attribution(
        predicted_event_ids or set(),
        {str(value) for value in label.get("event_ids", [])},
    )
    phase_detection = {
        phase: bool(unique_alerts & set(range(start, end + 1)))
        for phase, values in label.get("phase_windows", {}).items()
        if (bounds := _bounds(values)) is not None
        for start, end in [bounds]
    }
    return {
        "temporal_overlap": round(len(overlapping) / len(union), 4) if union else None,
        "event_precision": event_metrics[0],
        "event_recall": event_metrics[1],
        "detection_timing": timing,
        "participant_precision": participant_metrics[0],
        "participant_recall": participant_metrics[1],
        "order_precision": order_metrics[0],
        "order_recall": order_metrics[1],
        "phase_detection": phase_detection,
    }


def evidence_attribution(evidence: list[dict[str, Any]]) -> tuple[set[str], set[str], set[str]]:
    participants: set[str] = set()
    orders: set[str] = set()
    events: set[str] = set()
    for item in evidence:
        values = {value for value in str(item.get("value", "")).split(",") if value and value != "unavailable"}
        if item.get("key") == "linked_participant_ids":
            participants.update(values)
        elif item.get("key") == "linked_order_ids":
            orders.update(values)
        elif item.get("key") == "linked_event_ids":
            events.update(values)
    return participants, orders, events


def _primary_window(label: dict[str, Any]) -> tuple[int, int] | None:
    windows = label.get("manipulation_windows") or []
    if windows and (bounds := _bounds(windows[0])) is not None:
        return bounds
    return _bounds({"start_tick": label.get("start_tick"), "end_tick": label.get("actual_end_tick") or label.get("expected_end_tick")})


def _bounds(values: dict[str, Any]) -> tuple[int, int] | None:
    start = values.get("start_tick")
    end = values.get("end_tick")
    if start is None or end is None:
        return None
    return int(start), max(int(start), int(end))


def _attribution(predicted: set[str], truth: set[str]) -> tuple[float | None, float | None]:
    if not truth:
        return None, None
    matches = predicted & truth
    precision = len(matches) / len(predicted) if predicted else None
    recall = len(matches) / len(truth)
    return (
        round(precision, 4) if precision is not None else None,
        round(recall, 4),
    )


def _rounded(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None
