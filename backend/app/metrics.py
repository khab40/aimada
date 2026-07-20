from __future__ import annotations

import math
import threading
import time
from collections import defaultdict
from collections.abc import Iterable

LabelValues = tuple[str, ...]


class HistogramState:
    def __init__(self, buckets: tuple[float, ...]) -> None:
        self.bucket_counts = {bucket: 0 for bucket in buckets}
        self.count = 0
        self.total = 0.0

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        for bucket in self.bucket_counts:
            if value <= bucket:
                self.bucket_counts[bucket] += 1

    def copy(self) -> "HistogramSnapshot":
        return HistogramSnapshot(dict(self.bucket_counts), self.count, self.total)


class HistogramSnapshot:
    def __init__(self, bucket_counts: dict[float, int], count: int, total: float) -> None:
        self.bucket_counts = bucket_counts
        self.count = count
        self.total = total


class PrometheusTextRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, dict[LabelValues, float]] = defaultdict(dict)
        self._counter_meta: dict[str, tuple[str, tuple[str, ...]]] = {}
        self._gauges: dict[str, dict[LabelValues, float]] = defaultdict(dict)
        self._gauge_meta: dict[str, tuple[str, tuple[str, ...]]] = {}
        self._histograms: dict[str, dict[LabelValues, HistogramState]] = defaultdict(dict)
        self._histogram_meta: dict[str, tuple[str, tuple[str, ...], tuple[float, ...]]] = {}

    def counter(self, name: str, description: str, label_names: Iterable[str] = ()) -> None:
        self._counter_meta[name] = (description, tuple(label_names))

    def gauge(self, name: str, description: str, label_names: Iterable[str] = ()) -> None:
        self._gauge_meta[name] = (description, tuple(label_names))

    def histogram(
        self,
        name: str,
        description: str,
        label_names: Iterable[str] = (),
        buckets: Iterable[float] = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    ) -> None:
        self._histogram_meta[name] = (description, tuple(label_names), tuple(buckets))

    def inc(self, name: str, amount: float = 1.0, **labels: object) -> None:
        key = self._label_values(name, labels, self._counter_meta)
        with self._lock:
            self._counters[name][key] = self._counters[name].get(key, 0.0) + amount

    def set(self, name: str, value: float, **labels: object) -> None:
        key = self._label_values(name, labels, self._gauge_meta)
        with self._lock:
            self._gauges[name][key] = value

    def observe(self, name: str, value: float, **labels: object) -> None:
        key = self._label_values(name, labels, self._histogram_meta)
        buckets = self._histogram_meta[name][2]
        with self._lock:
            self._histograms[name].setdefault(key, HistogramState(buckets)).observe(value)

    def render(self) -> str:
        with self._lock:
            counters = {name: dict(values) for name, values in self._counters.items()}
            gauges = {name: dict(values) for name, values in self._gauges.items()}
            histograms = {
                name: {labels: values.copy() for labels, values in series.items()}
                for name, series in self._histograms.items()
            }

        lines: list[str] = []
        for name, (description, label_names) in sorted(self._counter_meta.items()):
            lines.extend(_metric_header(name, description, "counter"))
            for label_values, value in sorted(counters.get(name, {}).items()):
                lines.append(_sample(name, label_names, label_values, value))
        for name, (description, label_names) in sorted(self._gauge_meta.items()):
            lines.extend(_metric_header(name, description, "gauge"))
            for label_values, value in sorted(gauges.get(name, {}).items()):
                lines.append(_sample(name, label_names, label_values, value))
        for name, (description, label_names, buckets) in sorted(self._histogram_meta.items()):
            lines.extend(_metric_header(name, description, "histogram"))
            for label_values, state in sorted(histograms.get(name, {}).items()):
                for bucket in buckets:
                    count = state.bucket_counts.get(bucket, 0)
                    lines.append(_sample(f"{name}_bucket", (*label_names, "le"), (*label_values, _bucket(bucket)), count))
                lines.append(_sample(f"{name}_bucket", (*label_names, "le"), (*label_values, "+Inf"), state.count))
                lines.append(_sample(f"{name}_count", label_names, label_values, state.count))
                lines.append(_sample(f"{name}_sum", label_names, label_values, state.total))
        return "\n".join(lines)

    def _label_values(
        self,
        name: str,
        labels: dict[str, object],
        meta: dict[str, tuple[object, tuple[str, ...]]] | dict[str, tuple[object, tuple[str, ...], object]],
    ) -> LabelValues:
        label_names = meta[name][1]
        return tuple(str(labels.get(label_name, "")) for label_name in label_names)


class Timer:
    def __init__(self) -> None:
        self.started_at = time.perf_counter()

    def elapsed(self) -> float:
        return time.perf_counter() - self.started_at


def _metric_header(name: str, description: str, kind: str) -> list[str]:
    return [f"# HELP {name} {_escape_help(description)}", f"# TYPE {name} {kind}"]


def _sample(name: str, label_names: tuple[str, ...], label_values: LabelValues, value: float) -> str:
    label_text = ""
    if label_names:
        pairs = ",".join(
            f'{label_name}="{_escape_label(label_value)}"'
            for label_name, label_value in zip(label_names, label_values, strict=True)
        )
        label_text = f"{{{pairs}}}"
    return f"{name}{label_text} {_format_float(value)}"


def _bucket(value: float) -> str:
    return "+Inf" if math.isinf(value) else _format_float(value)


def _format_float(value: float) -> str:
    if isinstance(value, int) or value.is_integer():
        return str(int(value))
    return f"{value:.6g}"


def _escape_help(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n")


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
