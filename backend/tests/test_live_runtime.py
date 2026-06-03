import asyncio

from app.arena.live_runtime import LiveArenaRuntime


class RecordingBroadcaster:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def broadcast(self, message: dict[str, object]) -> None:
        self.messages.append(message)


def test_live_runtime_ticks_continuously_when_started() -> None:
    async def run() -> None:
        broadcaster = RecordingBroadcaster()
        runtime = LiveArenaRuntime(broadcaster, tick_interval_seconds=0.01)
        try:
            await runtime.start()
            await asyncio.sleep(0.04)
            snapshot = await runtime.snapshot()
            assert snapshot["running"] is True
            assert snapshot["tick"] >= 2
            assert snapshot["book"]["bids"]
            assert broadcaster.messages

            await runtime.pause()
            paused = await runtime.snapshot()
            assert paused["running"] is False

            await runtime.reset()
            reset = await runtime.snapshot()
            assert reset["tick"] == 0
        finally:
            await runtime.stop()

    asyncio.run(run())


def test_live_runtime_launches_scenario_and_broadcasts_state() -> None:
    async def run() -> None:
        broadcaster = RecordingBroadcaster()
        runtime = LiveArenaRuntime(broadcaster, tick_interval_seconds=0.01)
        try:
            result = await runtime.launch_scenario("layering-like")
            await asyncio.sleep(0.02)
            snapshot = await runtime.snapshot()

            assert result["accepted"] is True
            assert snapshot["running"] is True
            assert snapshot["active_scenario"]["scenario_name"] == "layering-like"
            assert "ABUSER_02" in snapshot["active_agents"]
            assert any(message["type"] == "arena_state" for message in broadcaster.messages)
        finally:
            await runtime.stop()

    asyncio.run(run())
