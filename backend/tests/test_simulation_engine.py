import asyncio

from app.arena.engine import SimulationEngine


def test_simulation_engine_start_pause_reset_cycle() -> None:
    async def run() -> None:
        engine = SimulationEngine(tick_interval_seconds=0.01)
        try:
            started = await engine.start()
            assert started.running is True

            await asyncio.sleep(0.04)
            running = await engine.get_state()
            assert running.tick >= 2
            assert running.book.bids
            assert running.book.asks
            assert running.events

            paused = await engine.pause()
            assert paused.running is False

            reset = await engine.reset()
            assert reset.tick == 0
            assert reset.running is False
            assert reset.events == []
        finally:
            await engine.stop()

    asyncio.run(run())


def test_simulation_engine_step_updates_visible_depth() -> None:
    engine = SimulationEngine()
    initial = engine.snapshot()

    next_state = engine.step()

    assert next_state["tick"] == 1
    assert next_state["book"]["bids"] != initial["book"]["bids"]
    assert next_state["events"][0]["agent_id"] in {"MM_01", "NOISE_01"}
