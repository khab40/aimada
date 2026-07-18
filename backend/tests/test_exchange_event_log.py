import json

import pytest

from app.exchange.event_log import EventLog
from app.exchange.schemas import AddOrderEvent, LobSnapshotEvent, OrderBookSnapshot


def add_event(event_id: str, *, sequence: int | None = None) -> AddOrderEvent:
    return AddOrderEvent(
        event_id=event_id,
        sequence=sequence,
        source="simulation",
        symbol="LOB",
        venue="SIM",
        order_id=f"order-{event_id}",
        agent_id="maker",
        side="buy",
        price=99.0,
        quantity=5.0,
    )


def test_event_log_assigns_sequences_and_supports_tail_and_cursor_replay() -> None:
    log = EventLog()

    first = log.append(add_event("event-1"))
    second, third = log.extend([add_event("event-2"), add_event("event-3")])

    assert [first.sequence, second.sequence, third.sequence] == [1, 2, 3]
    assert [event.event_id for event in log.tail(2)] == ["event-2", "event-3"]
    assert [event.event_id for event in log.replay_events(after_sequence=1, limit=1)] == ["event-2"]
    assert log.next_sequence == 4


def test_event_log_rejects_duplicates_and_non_contiguous_sequence() -> None:
    log = EventLog([add_event("event-1", sequence=1)])

    with pytest.raises(ValueError, match="duplicate exchange event id"):
        log.append(add_event("event-1"))
    with pytest.raises(ValueError, match="expected exchange event sequence 2"):
        log.append(add_event("event-3", sequence=3))


def test_event_log_jsonl_round_trip_preserves_typed_events(tmp_path) -> None:
    snapshot = LobSnapshotEvent(
        event_id="event-2",
        source="simulation",
        symbol="LOB",
        venue="SIM",
        depth=5,
        book=OrderBookSnapshot(bids=[], asks=[], best_bid=None, best_ask=None, mid=None, spread=None),
    )
    log = EventLog([add_event("event-1"), snapshot])

    path = log.write_jsonl(tmp_path / "exchange-events.jsonl")
    restored = EventLog.from_jsonl(path)

    assert restored.events == log.events
    assert [event.event_type for event in restored.events] == ["add", "snapshot"]


def test_event_log_reports_invalid_jsonl_line(tmp_path) -> None:
    path = tmp_path / "broken.jsonl"
    path.write_text(json.dumps(add_event("event-1", sequence=1).to_dict()) + "\nnot-json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        EventLog.from_jsonl(path)
