import asyncio

from app.arena.engine import SimulationEngine
from app.schemas.arena import AttackStage
from app.scenarios.controller import ScenarioController


def test_spoofing_like_scenario_progresses_and_marks_abuser_wall() -> None:
    engine = SimulationEngine()

    result = engine.launch_scenario("spoofing_like_wall")
    first = engine.step()

    assert result["accepted"] is True
    assert first["active_scenario"]["current_stage"] == AttackStage.ARMED

    second = engine.step()
    abuser_asks = [level for level in second["book"]["asks"] if level.get("owner") == "abuser"]

    assert second["active_scenario"]["current_stage"] == AttackStage.WALL_PLACED
    assert abuser_asks


def test_scenario_launch_creates_reproducible_label_record() -> None:
    engine = SimulationEngine(seed=123)

    result = engine.launch_scenario("spoofing_like_wall")
    state = engine.step()

    label = state["active_scenario"]["label"]
    assert result["accepted"] is True
    assert label["scenario_id"] == state["active_scenario"]["scenario_id"]
    assert label["scenario_family"] == "spoofing_like_wall"
    assert label["seed"] == 123
    assert label["start_tick"] == state["active_scenario"]["start_tick"]
    assert label["start_tick"] == 1
    assert label["expected_end_tick"] >= label["start_tick"]
    assert label["agent_ids"] == ["ABUSER_01"]
    assert label["parameters"]["scenario_name"] == "Spoofing-like Wall"


def test_quote_stuffing_scenario_generates_burst_events() -> None:
    engine = SimulationEngine()
    engine.launch_scenario("quote_stuffing")

    for _ in range(5):
        state = engine.step()

    stuffing_events = [
        event for event in state["events"]
        if event.get("scenario_family") == "quote_stuffing"
    ]

    assert state["active_scenario"]["current_stage"] == AttackStage.PRESSURE_PHASE
    assert len(stuffing_events) >= 8


def test_liquidity_evaporation_route_method_starts_running_scenario() -> None:
    async def run() -> None:
        engine = SimulationEngine(tick_interval_seconds=0.01)
        try:
            tracker = await engine.start_scenario("liquidity_evaporation")
            await asyncio.sleep(0.03)
            state = await engine.get_state()

            assert tracker.scenario_family == "liquidity_evaporation"
            assert state.running is True
            assert state.active_scenario is not None
            assert state.active_scenario.scenario_family == "liquidity_evaporation"
        finally:
            await engine.stop()

    asyncio.run(run())


def test_unknown_scenario_is_rejected() -> None:
    controller = ScenarioController()

    try:
        controller.start("unknown", tick=0)
    except ValueError as exc:
        assert "unknown scenario" in str(exc)
    else:
        raise AssertionError("expected unknown scenario to raise ValueError")
