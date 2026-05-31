from fastapi import WebSocket, WebSocketDisconnect


class Broadcaster:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, initial_message: dict[str, object] | None = None) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        if initial_message is not None:
            await websocket.send_json(initial_message)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            self._clients.discard(websocket)

    async def broadcast(self, message: dict[str, object]) -> None:
        stale: list[WebSocket] = []
        for client in self._clients:
            try:
                await client.send_json(message)
            except RuntimeError:
                stale.append(client)
        for client in stale:
            self._clients.discard(client)

    @property
    def client_count(self) -> int:
        return len(self._clients)
