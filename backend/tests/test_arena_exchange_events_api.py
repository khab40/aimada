import asyncio
from types import SimpleNamespace

from app.api.routes_arena import get_exchange_events
from app.arena.engine import SimulationEngine


def test_arena_state_contains_bounded_recent_exchange_events() -> None:
    engine = SimulationEngine(exchange_event_window=3)

    state = engine.step()

    assert len(state["exchange_events"]) == 3
    assert state["exchange_events"][-1]["event_type"] == "snapshot"
    assert state["exchange_events"][-1]["tick"] == 1
    assert [event["sequence"] for event in state["exchange_events"]] == sorted(
        event["sequence"] for event in state["exchange_events"]
    )


def test_exchange_event_replay_endpoint_uses_sequence_cursor_and_limit() -> None:
    async def run() -> None:
        engine = SimulationEngine()
        engine.step()
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(simulation=engine)))

        first = await get_exchange_events(request, after_sequence=0, limit=2)
        second = await get_exchange_events(request, after_sequence=first.next_after_sequence, limit=100)

        assert len(first.events) == 2
        assert first.has_more is True
        assert first.next_after_sequence == 2
        assert second.events[0].sequence == 3
        assert second.latest_sequence == engine.exchange_event_log.next_sequence - 1
        assert second.has_more is False

    asyncio.run(run())
