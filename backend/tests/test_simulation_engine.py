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


def test_simulation_replay_is_deterministic_for_same_seed() -> None:
    first = SimulationEngine(seed=99)
    second = SimulationEngine(seed=99)

    first.launch_scenario("spoofing-like")
    second.launch_scenario("spoofing-like")
    first_states = [first.step() for _ in range(8)]
    second_states = [second.step() for _ in range(8)]

    assert [
        (
            state["tick"],
            state["book"]["best_bid"],
            state["book"]["best_ask"],
            state["features"]["wall_size_ratio"],
            [(event["type"], event.get("agent_id"), event.get("stage")) for event in state["events"][:5]],
        )
        for state in first_states
    ] == [
        (
            state["tick"],
            state["book"]["best_bid"],
            state["book"]["best_ask"],
            state["features"]["wall_size_ratio"],
            [(event["type"], event.get("agent_id"), event.get("stage")) for event in state["events"][:5]],
        )
        for state in second_states
    ]


def test_spoofing_scenario_creates_single_scenario_linked_incident() -> None:
    engine = SimulationEngine(seed=11)
    engine.launch_scenario("spoofing-like")

    state = {}
    for _ in range(8):
        state = engine.step()

    incidents = [
        incident
        for incident in state["incidents"]
        if incident["scenario_family"] == "spoofing_like"
    ]
    assert len(incidents) == 1
    assert incidents[0]["confidence"] >= 0.8
    assert incidents[0]["evidence"]
