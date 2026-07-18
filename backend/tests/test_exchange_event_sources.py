from collections.abc import Iterable

import pytest

from app.exchange.event_log import EventLog
from app.exchange.schemas import AddOrderEvent, CanonicalExchangeEvent
from app.exchange.sources import (
    CanonicalJsonlEventSource,
    HistoricalRecordEventSource,
    SimulationEventSource,
)


def add_event(event_id: str, *, source: str = "simulation", source_sequence: int | None = None) -> AddOrderEvent:
    return AddOrderEvent(
        event_id=event_id,
        source=source,  # type: ignore[arg-type]
        source_sequence=source_sequence,
        symbol="MSFT",
        venue="SIM" if source == "simulation" else "XNAS",
        order_id=f"order-{event_id}",
        agent_id="feed",
        side="buy",
        price=400.0,
        quantity=10.0,
    )


def test_simulation_source_is_a_live_cursor_view_over_the_log() -> None:
    log = EventLog([add_event("event-1")])
    source = SimulationEventSource(log)

    first = source.read(limit=1)
    log.append(add_event("event-2"))
    second = source.read(after_sequence=first.next_after_sequence, limit=1)

    assert [event.event_id for event in first.events] == ["event-1"]
    assert [event.event_id for event in second.events] == ["event-2"]
    assert second.latest_sequence == 2


def test_canonical_jsonl_source_replays_validated_stream(tmp_path) -> None:
    path = EventLog([add_event("event-1"), add_event("event-2")]).write_jsonl(tmp_path / "events.jsonl")
    source = CanonicalJsonlEventSource(path)

    batch = source.read(after_sequence=1, limit=10)

    assert [event.event_id for event in batch.events] == ["event-2"]
    assert batch.has_more is False


class FakeHistoricalNormalizer:
    def normalize(self, record: object) -> Iterable[CanonicalExchangeEvent]:
        assert isinstance(record, dict)
        yield AddOrderEvent(
            event_id=f"XNAS-{record['sequence']}",
            source="historical",
            source_sequence=int(record["sequence"]),
            symbol="MSFT",
            venue="XNAS",
            exchange_timestamp_ns=int(record["timestamp_ns"]),
            order_id=str(record["order_id"]),
            agent_id="historical-feed",
            side="buy",
            price=float(record["price"]),
            quantity=float(record["quantity"]),
        )


def test_historical_source_preserves_source_fields_and_assigns_canonical_sequence() -> None:
    source = HistoricalRecordEventSource(
        [
            {"sequence": 91, "timestamp_ns": 1001, "order_id": "o1", "price": 400, "quantity": 10},
            {"sequence": 93, "timestamp_ns": 1003, "order_id": "o2", "price": 399, "quantity": 20},
        ],
        FakeHistoricalNormalizer(),
    )

    batch = source.read(limit=10)

    assert [event.sequence for event in batch.events] == [1, 2]
    assert [event.source_sequence for event in batch.events] == [91, 93]
    assert [event.exchange_timestamp_ns for event in batch.events] == [1001, 1003]


class InvalidHistoricalNormalizer:
    def normalize(self, record: object) -> Iterable[CanonicalExchangeEvent]:
        yield add_event("simulation-event")


def test_historical_source_rejects_wrong_origin() -> None:
    with pytest.raises(ValueError, match="source='historical'"):
        HistoricalRecordEventSource([{}], InvalidHistoricalNormalizer())
