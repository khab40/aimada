import type { ArenaState } from "@/types/arena";
import { ARENA_WS_URL } from "@/config/runtime";

export type ArenaWebSocketMessage = {
  type: "arena_state";
  payload: ArenaState;
};

export function connectArenaWebSocket(onMessage: (payload: ArenaWebSocketMessage) => void): WebSocket {
  const socket = new WebSocket(ARENA_WS_URL);
  socket.onmessage = (event) => onMessage(JSON.parse(event.data));
  return socket;
}
