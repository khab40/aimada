import asyncio
from contextlib import suppress

from app.arena.engine import ArenaEngine
from app.websocket.broadcaster import Broadcaster


class LiveArenaRuntime:
    def __init__(self, broadcaster: Broadcaster, tick_interval_seconds: float = 0.35) -> None:
        self.broadcaster = broadcaster
        self.tick_interval_seconds = tick_interval_seconds
        self.engine = ArenaEngine()
        self.running = False
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._last_state = self.engine.snapshot(running=False)

    async def start(self) -> dict[str, object]:
        async with self._lock:
            self.running = True
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._run())
            self._last_state = self.engine.snapshot(running=True)
        await self.broadcaster.broadcast({"type": "arena_state", "payload": self._last_state})
        return self._last_state

    async def pause(self) -> dict[str, object]:
        async with self._lock:
            self.running = False
            self._last_state = self.engine.snapshot(running=False)
        await self.broadcaster.broadcast({"type": "arena_state", "payload": self._last_state})
        return self._last_state

    async def reset(self) -> dict[str, object]:
        async with self._lock:
            self.running = False
            self.engine = ArenaEngine()
            self._last_state = self.engine.snapshot(running=False)
        await self.broadcaster.broadcast({"type": "arena_state", "payload": self._last_state})
        return self._last_state

    async def launch_scenario(self, scenario_name: str) -> dict[str, object]:
        async with self._lock:
            result = self.engine.launch_scenario(scenario_name)
            if result.get("accepted"):
                self.running = True
                if self._task is None or self._task.done():
                    self._task = asyncio.create_task(self._run())
            self._last_state = self.engine.snapshot(running=self.running)
        await self.broadcaster.broadcast({"type": "arena_state", "payload": self._last_state})
        return {"accepted": bool(result.get("accepted")), "result": result, "state": self._last_state}

    async def snapshot(self) -> dict[str, object]:
        async with self._lock:
            return dict(self._last_state)

    async def stop(self) -> None:
        self.running = False
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.tick_interval_seconds)
            if not self.running:
                continue
            async with self._lock:
                self._last_state = self.engine.step()
            await self.broadcaster.broadcast({"type": "arena_state", "payload": self._last_state})
