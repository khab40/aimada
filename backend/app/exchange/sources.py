import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.exchange.event_log import EventLog
from app.exchange.schemas import CanonicalExchangeEvent, exchange_event_from_dict


@dataclass(frozen=True)
class ExchangeEventBatch:
    events: list[CanonicalExchangeEvent]
    after_sequence: int
    next_after_sequence: int
    latest_sequence: int
    has_more: bool


class ExchangeEventSource(Protocol):
    """Read canonical events without depending on simulation or storage details."""

    def read(self, *, after_sequence: int = 0, limit: int = 100) -> ExchangeEventBatch:
        ...


class SimulationEventSource:
    """Live view over the event log owned by a simulation run."""

    def __init__(self, event_log: EventLog) -> None:
        self.event_log = event_log

    def read(self, *, after_sequence: int = 0, limit: int = 100) -> ExchangeEventBatch:
        return _read_log(self.event_log, after_sequence=after_sequence, limit=limit)


class CanonicalJsonlEventSource:
    """Replay an already-normalized canonical JSONL event stream."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._event_log: EventLog | None = None

    def read(self, *, after_sequence: int = 0, limit: int = 100) -> ExchangeEventBatch:
        if self._event_log is None:
            self._event_log = EventLog.from_jsonl(self.path)
        return _read_log(self._event_log, after_sequence=after_sequence, limit=limit)


class PersistedExchangeEventSource:
    """Replay one stream from the append-only multi-stream history file."""

    def __init__(self, path: str | Path, *, stream_id: str) -> None:
        self.path = Path(path)
        self.stream_id = stream_id
        self._event_log: EventLog | None = None

    def read(self, *, after_sequence: int = 0, limit: int = 100) -> ExchangeEventBatch:
        if self._event_log is None:
            self._event_log = self._load_stream()
        return _read_log(self._event_log, after_sequence=after_sequence, limit=limit)

    def _load_stream(self) -> EventLog:
        event_log = EventLog()
        with self.path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                    if not isinstance(payload, dict):
                        raise ValueError("event must be a JSON object")
                    if payload.get("stream_id") != self.stream_id:
                        continue
                    event_log.append(exchange_event_from_dict(payload))
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise ValueError(f"invalid persisted exchange stream at line {line_number}: {exc}") from exc
        return event_log


class HistoricalRecordNormalizer(Protocol):
    """Venue/vendor adapter that maps one raw record into canonical events."""

    def normalize(self, record: object) -> Iterable[CanonicalExchangeEvent]:
        ...


class HistoricalRecordEventSource:
    """Normalize raw historical records while keeping vendor parsing outside the core."""

    def __init__(self, records: Iterable[object], normalizer: HistoricalRecordNormalizer) -> None:
        event_log = EventLog()
        for record in records:
            for event in normalizer.normalize(record):
                if event.source != "historical":
                    raise ValueError("historical normalizers must emit source='historical'")
                event_log.append(event)
        self.event_log = event_log

    def read(self, *, after_sequence: int = 0, limit: int = 100) -> ExchangeEventBatch:
        return _read_log(self.event_log, after_sequence=after_sequence, limit=limit)


def _read_log(event_log: EventLog, *, after_sequence: int, limit: int) -> ExchangeEventBatch:
    if after_sequence < 0:
        raise ValueError("after_sequence must be non-negative")
    if limit <= 0:
        raise ValueError("limit must be positive")
    requested = event_log.replay_events(after_sequence=after_sequence, limit=limit + 1)
    has_more = len(requested) > limit
    events = requested[:limit]
    next_after_sequence = events[-1].sequence if events else after_sequence
    return ExchangeEventBatch(
        events=events,
        after_sequence=after_sequence,
        next_after_sequence=next_after_sequence or after_sequence,
        latest_sequence=event_log.next_sequence - 1,
        has_more=has_more,
    )
