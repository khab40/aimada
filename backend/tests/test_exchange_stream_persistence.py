import asyncio

from app.arena.engine import SimulationEngine
from app.exchange.schemas import LobSnapshotEvent
from app.exchange.sources import PersistedExchangeEventSource
from app.storage.history import EXCHANGE_EVENTS_FILE, LOB_SNAPSHOTS_FILE
from app.storage.local_store import LocalStore


def test_simulation_persists_complete_replayable_exchange_and_snapshot_streams(tmp_path) -> None:
    store = LocalStore(tmp_path)
    engine = SimulationEngine(seed=31, store=store)
    engine.launch_scenario("spoofing_like_wall")

    for _ in range(8):
        engine.step()

    event_rows = store.read_jsonl(EXCHANGE_EVENTS_FILE)
    snapshot_rows = store.read_jsonl(LOB_SNAPSHOTS_FILE)
    replay = PersistedExchangeEventSource(
        tmp_path / EXCHANGE_EVENTS_FILE,
        stream_id=engine.exchange_stream_id,
    ).read(limit=10_000)

    assert len(event_rows) == len(engine.exchange_event_log.events)
    assert [row["sequence"] for row in event_rows] == list(range(1, len(event_rows) + 1))
    assert {row["event_type"] for row in event_rows} == {"add", "modify", "cancel", "execute", "snapshot"}
    assert all(row["run_id"] == engine.run_id for row in event_rows)
    assert all(row["stream_id"] == engine.exchange_stream_id for row in event_rows)
    assert len(snapshot_rows) == 8
    assert [row["tick"] for row in snapshot_rows] == list(range(1, 9))
    assert [event.to_dict() for event in replay.events] == [
        event.to_dict() for event in engine.exchange_event_log.events
    ]
    final_event = replay.events[-1]
    assert isinstance(final_event, LobSnapshotEvent)
    assert final_event.book.to_dict() == engine.order_book.get_snapshot(depth=12).to_dict()


def test_reset_starts_a_new_persisted_stream_segment(tmp_path) -> None:
    store = LocalStore(tmp_path)
    engine = SimulationEngine(seed=32, store=store)
    engine.step()
    first_stream_id = engine.exchange_stream_id

    asyncio.run(engine.reset())
    engine.step()

    rows = store.read_jsonl(EXCHANGE_EVENTS_FILE)
    stream_ids = {str(row["stream_id"]) for row in rows}
    assert first_stream_id in stream_ids
    assert engine.exchange_stream_id in stream_ids
    assert first_stream_id != engine.exchange_stream_id
    second_replay = PersistedExchangeEventSource(
        tmp_path / EXCHANGE_EVENTS_FILE,
        stream_id=engine.exchange_stream_id,
    ).read(limit=100)
    assert second_replay.events[0].sequence == 1
