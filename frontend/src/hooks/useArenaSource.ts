import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMockArena, type MockScenarioType } from "@/hooks/useMockArena";
import type { ArenaState, ArenaWebSocketMessage } from "@/types/arena";

export type ArenaMode = "mock" | "websocket";
export type ArenaScenarioType = MockScenarioType;
export type ArenaSourceStatus = "mock" | "connecting" | "connected" | "disconnected" | "error";

const DEFAULT_WS_URL = "ws://localhost:8000/ws/arena";
const DEFAULT_API_BASE_URL = "http://localhost:8000";

export function useArenaSource() {
  const mockArena = useMockArena();
  const mode = getArenaMode();
  const wsUrl = import.meta.env.VITE_ARENA_WS_URL ?? DEFAULT_WS_URL;
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;
  const socketRef = useRef<WebSocket | null>(null);
  const [sourceStatus, setSourceStatus] = useState<ArenaSourceStatus>(mode === "mock" ? "mock" : "connecting");
  const [websocketState, setWebsocketState] = useState<ArenaState>(() => mockArena.state);

  useEffect(() => {
    if (mode !== "websocket") {
      setSourceStatus("mock");
      return undefined;
    }

    setSourceStatus("connecting");
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => setSourceStatus("connected");
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as ArenaWebSocketMessage | ArenaState;
        const nextState = "payload" in message ? message.payload : message;
        if (isArenaState(nextState)) {
          setWebsocketState(nextState);
        }
      } catch {
        setSourceStatus("error");
      }
    };
    socket.onerror = () => setSourceStatus("error");
    socket.onclose = () => {
      if (socketRef.current === socket) {
        setSourceStatus("disconnected");
        socketRef.current = null;
      }
    };

    return () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
      socket.close();
    };
  }, [mode, wsUrl]);

  const sendWebSocketCommand = useCallback((message: Record<string, unknown>) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setSourceStatus("error");
      return false;
    }
    socket.send(JSON.stringify(message));
    return true;
  }, []);

  const start = useCallback(() => {
    if (mode === "mock") {
      mockArena.start();
      return;
    }
    sendWebSocketCommand({ action: "start", type: "arena_control" });
  }, [mockArena, mode, sendWebSocketCommand]);

  const pause = useCallback(() => {
    if (mode === "mock") {
      mockArena.pause();
      return;
    }
    sendWebSocketCommand({ action: "pause", type: "arena_control" });
  }, [mockArena, mode, sendWebSocketCommand]);

  const reset = useCallback(() => {
    if (mode === "mock") {
      mockArena.reset();
      return;
    }
    sendWebSocketCommand({ action: "reset", type: "arena_control" });
  }, [mockArena, mode, sendWebSocketCommand]);

  const launchScenario = useCallback((scenario: ArenaScenarioType) => {
    if (mode === "mock") {
      mockArena.launchScenario(scenario);
      return;
    }
    sendWebSocketCommand({ scenario: scenarioToBackendName(scenario), type: "launch_scenario" });
  }, [mockArena, mode, sendWebSocketCommand]);

  const state = mode === "mock" ? mockArena.state : websocketState;

  return useMemo(
    () => ({
      launchScenario,
      mode,
      pause,
      reset,
      running: state.running,
      sourceStatus,
      start,
      state,
      symbol: getSymbol(state),
      tick: state.tick,
      apiBaseUrl,
      wsUrl
    }),
    [apiBaseUrl, launchScenario, mode, pause, reset, sourceStatus, start, state, wsUrl]
  );
}

function getArenaMode(): ArenaMode {
  return import.meta.env.VITE_ARENA_MODE === "mock" ? "mock" : "websocket";
}

function scenarioToBackendName(scenario: ArenaScenarioType) {
  const mapping: Record<ArenaScenarioType, string> = {
    layering_like: "layering-like",
    liquidity_evaporation: "liquidity-evaporation",
    quote_stuffing: "quote-stuffing",
    spoofing_like_wall: "spoofing-like"
  };
  return mapping[scenario];
}

function isArenaState(value: unknown): value is ArenaState {
  return Boolean(
    value &&
    typeof value === "object" &&
    "book" in value &&
    "tick" in value &&
    "running" in value
  );
}

function getSymbol(state: ArenaState) {
  const eventSymbol = state.events.find((event) => typeof event.symbol === "string")?.symbol;
  return typeof eventSymbol === "string" ? eventSymbol : "BTCUSDT";
}
