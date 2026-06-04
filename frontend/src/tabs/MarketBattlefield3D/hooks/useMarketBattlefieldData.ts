import { useEffect, useMemo, useState } from "react";
import { useArenaSource } from "@/hooks/useArenaSource";
import type { AgentEvent, ArenaState, PriceLevel } from "@/types/arena";
import type { BattlefieldEvent, BattlefieldFrame, BattlefieldPlaybackState } from "../types";

const MAX_HISTORY = 64;
const VISIBLE_LEVELS_PER_SIDE = 12;

export function useMarketBattlefieldData() {
  const arena = useArenaSource();
  const [frames, setFrames] = useState<BattlefieldFrame[]>(() => [arenaStateToFrame(arena.state)]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [followLive, setFollowLive] = useState(true);

  useEffect(() => {
    const nextFrame = arenaStateToFrame(arena.state);
    setFrames((current) => {
      const last = current.at(-1);
      if (last?.tick === nextFrame.tick) {
        return [...current.slice(0, -1), nextFrame];
      }
      return [...current, nextFrame].slice(-MAX_HISTORY);
    });
  }, [arena.state]);

  useEffect(() => {
    if (!followLive) {
      return;
    }
    setSelectedIndex(Math.max(0, frames.length - 1));
  }, [followLive, frames.length]);

  const boundedIndex = Math.min(selectedIndex, Math.max(0, frames.length - 1));
  const frame = frames[boundedIndex] ?? arenaStateToFrame(arena.state);
  const events = useMemo(() => dedupeEvents(frames.flatMap((item) => item.events)), [frames]);

  return {
    events,
    frame,
    frames,
    mode: arena.mode,
    pause: arena.pause,
    play: () => {
      setFollowLive(true);
      arena.start();
    },
    playbackState: (arena.running ? "playing" : "paused") as BattlefieldPlaybackState,
    reset: () => {
      arena.reset();
      const resetFrame = arenaStateToFrame({ ...arena.state, tick: 0 });
      setFrames([resetFrame]);
      setSelectedIndex(0);
      setFollowLive(true);
    },
    selectedIndex: boundedIndex,
    setSelectedIndex: (index: number) => {
      setFollowLive(index >= frames.length - 1);
      setSelectedIndex(index);
    },
    sourceStatus: arena.sourceStatus,
    symbol: arena.symbol,
    visibleFrames: frames.slice(Math.max(0, boundedIndex - 47), boundedIndex + 1)
  };
}

function arenaStateToFrame(state: ArenaState): BattlefieldFrame {
  const detectorConfidence = Math.max(0, ...state.detectors.scores.map((score) => score.confidence));
  const scenarioConfidence = state.active_scenario?.stages
    ?.map((stage) => stage.detector_confidence ?? 0)
    .reduce((max, value) => Math.max(max, value), 0) ?? 0;

  return {
    cells: [
      ...levelsToCells(state.book.bids, "bid", state.tick, detectorConfidence),
      ...levelsToCells(state.book.asks, "ask", state.tick, detectorConfidence)
    ],
    events: [
      ...eventsToBattlefieldEvents(state.events, state.tick),
      ...incidentEvents(state)
    ],
    midPrice: state.mid ?? 0,
    spoofingProbability: Math.max(detectorConfidence, scenarioConfidence),
    tick: state.tick
  };
}

function levelsToCells(
  levels: PriceLevel[],
  side: "ask" | "bid",
  tick: number,
  detectorConfidence: number
) {
  const visible = levels.slice(0, VISIBLE_LEVELS_PER_SIDE);
  return visible.map((level, index) => {
    const ownedByAbuser = level.owner === "abuser" || level.agent_id?.toLowerCase().includes("abuser");
    return {
      anomalyScore: ownedByAbuser ? Math.max(0.86, detectorConfidence) : Math.max(0, detectorConfidence - 0.55) * 0.45,
      price: level.price,
      priceLevel: side === "ask" ? index + 1 : -(index + 1),
      side,
      tick,
      volume: level.quantity
    };
  });
}

function eventsToBattlefieldEvents(events: AgentEvent[], fallbackTick: number): BattlefieldEvent[] {
  return events.slice(0, 28).map((event, index) => {
    const type = classifyEvent(event);
    const severity = type === "DETECTION" ? numberValue(event.confidence, 0.78) : event.scenario_name ? 0.72 : 0.35;
    return {
      agentId: event.agent_id ?? event.aggressor_agent_id ?? "EXCHANGE",
      description: describeEvent(event),
      severity,
      tick: numberValue(event.tick, fallbackTick - index),
      type
    };
  });
}

function incidentEvents(state: ArenaState): BattlefieldEvent[] {
  return (state.incidents ?? []).slice(-4).map((incident) => ({
    agentId: incident.agent,
    description: `${incident.title} confirmed with confidence ${incident.confidence.toFixed(2)}.`,
    severity: incident.confidence,
    tick: state.tick,
    type: "DETECTION" as const
  }));
}

function classifyEvent(event: AgentEvent): BattlefieldEvent["type"] {
  const text = `${event.type} ${String(event.kind ?? "")} ${event.scenario_name ?? ""}`.toLowerCase();
  if (text.includes("cancel")) {
    return "CANCEL_BURST";
  }
  if (text.includes("detector") || text.includes("incident") || text.includes("alert")) {
    return "DETECTION";
  }
  if (text.includes("trade") || text.includes("price")) {
    return "PRICE_MOVE";
  }
  if (event.scenario_name || event.scenario_family || event.owner === "abuser") {
    return "SPOOF_ORDER";
  }
  return "PRICE_MOVE";
}

function describeEvent(event: AgentEvent) {
  const scenario = event.scenario_name ? ` [${event.scenario_name.replaceAll("_", " ")}]` : "";
  const side = event.side ? ` ${event.side}` : "";
  const quantity = typeof event.quantity === "number" ? ` size ${event.quantity.toFixed(3)}` : "";
  const price = typeof event.price === "number" ? ` @ ${event.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "";
  return `${event.type}${scenario}${side}${quantity}${price}`;
}

function dedupeEvents(events: BattlefieldEvent[]) {
  const seen = new Set<string>();
  return events.filter((event) => {
    const key = `${event.tick}-${event.type}-${event.agentId}-${event.description}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function numberValue(value: unknown, fallback: number) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}
