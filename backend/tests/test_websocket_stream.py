import asyncio

from fastapi import WebSocketDisconnect

from app.websocket.broadcaster import Broadcaster


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
