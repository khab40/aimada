import asyncio

from fastapi import WebSocketDisconnect

from app.arena.engine import SimulationEngine
from app.websocket.broadcaster import Broadcaster
from app.websocket.manager import WebSocketManager


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.messages: list[dict[str, object]] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict[str, object]) -> None:
        self.messages.append(message)

    async def receive_text(self) -> str:
        raise WebSocketDisconnect()


def test_websocket_broadcaster_sends_initial_arena_state() -> None:
    async def run() -> None:
        websocket = FakeWebSocket()
        broadcaster = Broadcaster()
        initial = {"type": "arena_state", "payload": {"tick": 0, "book": {"bids": [], "asks": []}}}

        await broadcaster.connect(websocket, initial)

        assert websocket.accepted is True
        assert websocket.messages == [initial]
        assert broadcaster.client_count == 0

    asyncio.run(run())


def test_websocket_manager_tracks_clients_and_sends_arena_state() -> None:
    async def run() -> None:
        websocket = FakeWebSocket()
        manager = WebSocketManager()
        engine = SimulationEngine()

        await manager.connect(websocket)
        await manager.send_state(websocket, await engine.get_state())

        assert websocket.accepted is True
        assert manager.client_count == 1
        assert websocket.messages[0]["type"] == "arena_state"
        assert websocket.messages[0]["payload"]["tick"] == 0

        manager.disconnect(websocket)
        assert manager.client_count == 0

    asyncio.run(run())


def test_websocket_manager_sends_versioned_arena_message_envelope() -> None:
    async def run() -> None:
        websocket = FakeWebSocket()
        manager = WebSocketManager()
        engine = SimulationEngine()

        await manager.connect(websocket)
        await manager.send_state(websocket, await engine.get_state())

        message = websocket.messages[0]
        assert message["type"] == "arena_state"
        assert message["version"] == 1
        assert isinstance(message["timestamp"], str)
        assert message["payload"]["tick"] == 0
        assert message["payload"]["book"]["bids"]

    asyncio.run(run())
