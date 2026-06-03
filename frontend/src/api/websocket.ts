import type { ArenaState } from "@/types/arena";

const WS_URL = import.meta.env.VITE_ARENA_WS_URL ?? "ws://localhost:8000/ws/arena";

export type ArenaWebSocketMessage = {
  type: "arena_state";
  payload: ArenaState;
};

export function connectArenaWebSocket(onMessage: (payload: ArenaWebSocketMessage) => void): WebSocket {
  const socket = new WebSocket(WS_URL);
  socket.onmessage = (event) => onMessage(JSON.parse(event.data));
  return socket;
}
