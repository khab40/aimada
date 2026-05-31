const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws/arena";

export function connectArenaWebSocket(onMessage: (payload: unknown) => void): WebSocket {
  const socket = new WebSocket(WS_URL);
  socket.onmessage = (event) => onMessage(JSON.parse(event.data));
  return socket;
}
