import json
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path
from typing import Self

from app.exchange.schemas import CanonicalExchangeEvent, exchange_event_from_dict


class EventLog:
    """Append-only canonical event log with deterministic stream sequencing."""

    def __init__(self, events: Iterable[CanonicalExchangeEvent] = ()) -> None:
        self._events: list[CanonicalExchangeEvent] = []
        self._event_ids: set[str] = set()
        for event in events:
            self.append(event)

    @property
    def events(self) -> tuple[CanonicalExchangeEvent, ...]:
        return tuple(self._events)

    @property
    def next_sequence(self) -> int:
        return len(self._events) + 1

    def append(self, event: CanonicalExchangeEvent) -> CanonicalExchangeEvent:
        if event.event_id in self._event_ids:
            raise ValueError(f"duplicate exchange event id: {event.event_id}")
        sequence = self.next_sequence
        if event.sequence is not None and event.sequence != sequence:
            raise ValueError(f"expected exchange event sequence {sequence}, got {event.sequence}")
        sequenced_event = event if event.sequence == sequence else replace(event, sequence=sequence)
        self._events.append(sequenced_event)
        self._event_ids.add(sequenced_event.event_id)
        return sequenced_event

    def extend(self, events: Iterable[CanonicalExchangeEvent]) -> list[CanonicalExchangeEvent]:
        return [self.append(event) for event in events]

    def tail(self, limit: int = 100) -> list[CanonicalExchangeEvent]:
        if limit < 0:
            raise ValueError("tail limit must be non-negative")
        if limit == 0:
            return []
        return list(self._events[-limit:])

    def replay_events(
        self,
        *,
        after_sequence: int = 0,
        limit: int | None = None,
    ) -> list[CanonicalExchangeEvent]:
        if after_sequence < 0:
            raise ValueError("after_sequence must be non-negative")
        if limit is not None and limit < 0:
            raise ValueError("replay limit must be non-negative")
        replay = [event for event in self._events if event.sequence and event.sequence > after_sequence]
        return replay if limit is None else replay[:limit]

    def write_jsonl(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            for event in self._events:
                handle.write(json.dumps(event.to_dict(), separators=(",", ":"), sort_keys=True))
                handle.write("\n")
        return output_path

    @classmethod
    def from_jsonl(cls, path: str | Path) -> Self:
        log = cls()
        with Path(path).open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                    if not isinstance(payload, dict):
                        raise ValueError("event must be a JSON object")
                    log.append(exchange_event_from_dict(payload))
                except (json.JSONDecodeError, ValueError, TypeError) as exc:
                    raise ValueError(f"invalid exchange event JSONL at line {line_number}: {exc}") from exc
        return log
