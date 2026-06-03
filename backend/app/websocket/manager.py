from fastapi import WebSocket

from app.schemas.arena import ArenaState
from app.websocket.schemas import ArenaMessage


class WebSocketManager:
    def __init__(self, stream_interval_seconds: float = 0.5) -> None:
        self.stream_interval_seconds = stream_interval_seconds
        self._clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    async def send_state(self, websocket: WebSocket, state: ArenaState) -> None:
        message = ArenaMessage.from_payload(state.model_dump(mode="json"))
        await websocket.send_json(message.model_dump(mode="json"))

    async def broadcast_state(self, state: ArenaState) -> None:
        stale: list[WebSocket] = []
        for websocket in self._clients:
            try:
                await self.send_state(websocket, state)
            except RuntimeError:
                stale.append(websocket)

        for websocket in stale:
            self.disconnect(websocket)

    @property
    def client_count(self) -> int:
        return len(self._clients)
