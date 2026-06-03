import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  AgentEvent,
  AttackStage,
  AttackStageSnapshot,
  ArenaState,
  AttackTrackerState,
  DetectorScore,
  MarketFeatures,
  OrderBookSnapshot,
  PriceLevel
} from "@/types/arena";

export type MockScenarioType =
  | "spoofing_like_wall"
  | "layering_like"
  | "quote_stuffing"
  | "liquidity_evaporation";

type ScenarioSpec = {
  agentId: string;
  durationTicks: number;
  family: string;
  label: string;
};

const SYMBOL = "BTCUSDT";
const TICK_MS = 500;
const BASE_MID = 68_000;
const BASE_SPREAD = 4;

const scenarioSpecs: Record<MockScenarioType, ScenarioSpec> = {
  spoofing_like_wall: {
    agentId: "ABUSER_01",
    durationTicks: 10,
    family: "spoofing_like",
    label: "Spoofing-like ask wall"
  },
  layering_like: {
    agentId: "ABUSER_02",
    durationTicks: 12,
    family: "layering_like",
    label: "Layering-like ask levels"
  },
  quote_stuffing: {
    agentId: "ABUSER_03",
    durationTicks: 8,
    family: "quote_stuffing",
    label: "Quote-stuffing message burst"
  },
  liquidity_evaporation: {
    agentId: "SCENARIO_LIQUIDITY",
    durationTicks: 10,
    family: "liquidity_evaporation",
    label: "Liquidity evaporation"
  }
};

export function useMockArena() {
  const [state, setState] = useState<ArenaState>(() => createInitialState());

  useEffect(() => {
    if (!state.running) {
      return undefined;
    }

    const handle = window.setInterval(() => {
      setState((current) => advanceState(current));
    }, TICK_MS);

    return () => window.clearInterval(handle);
  }, [state.running]);

  const start = useCallback(() => {
    setState((current) => ({ ...current, running: true }));
  }, []);

  const pause = useCallback(() => {
    setState((current) => ({ ...current, running: false }));
  }, []);

  const reset = useCallback(() => {
    setState(createInitialState());
  }, []);

  const launchScenario = useCallback((type: MockScenarioType) => {
    setState((current) => {
      const spec = scenarioSpecs[type];
      const activeScenario: AttackTrackerState = {
        agent_id: spec.agentId,
        current_stage: "armed",
        scenario_family: spec.family,
        scenario_id: `${type}-${current.tick}`,
        scenario_name: type,
        start_tick: current.tick,
        stages: createAttackStages(current.tick, Date.now(), "armed", 0.18),
        status: "armed"
      };
      const event: AgentEvent = {
        agent_id: spec.agentId,
        kind: "red_team",
        scenario_family: spec.family,
        scenario_id: activeScenario.scenario_id,
        scenario_name: type,
        symbol: SYMBOL,
        timestamp: Date.now(),
        type: "scenario_started"
      };

      return {
        ...current,
        active_scenario: activeScenario,
        events: [event, ...current.events].slice(0, 24),
        running: true
      };
    });
  }, []);

  return useMemo(
    () => ({
      launchScenario,
      pause,
      reset,
      running: state.running,
      start,
      state,
      symbol: SYMBOL,
      tick: state.tick
    }),
    [launchScenario, pause, reset, start, state]
  );
}

function createInitialState(): ArenaState {
  const book = createBook(BASE_MID, BASE_SPREAD);
  return {
    active_agents: ["MarketMakerAgent", "NoiseTraderAgent", "LiquidityTakerAgent"],
    active_scenario: null,
    best_ask: book.best_ask,
    best_bid: book.best_bid,
    book,
    detectors: createDetectorScores(),
    events: [
      {
        agent_id: "MarketMakerAgent",
        price: book.best_bid ?? BASE_MID,
        quantity: 2.4,
        side: "buy",
        symbol: SYMBOL,
        timestamp: Date.now(),
        type: "limit_order"
      }
    ],
    features: createFeatures(book),
    mid: book.mid,
    running: false,
    spread: book.spread,
    tick: 0
  };
}

function advanceState(current: ArenaState): ArenaState {
  const nextTick = current.tick + 1;
  const scenarioName = current.active_scenario?.scenario_name as MockScenarioType | undefined;
  const spec = scenarioName ? scenarioSpecs[scenarioName] : undefined;
  const elapsedTicks = current.active_scenario ? nextTick - current.active_scenario.start_tick : 0;
  const scenarioStillActive = Boolean(spec && elapsedTicks <= spec.durationTicks);

  let book = perturbBook(current.book, nextTick);
  if (scenarioStillActive && scenarioName) {
    book = applyScenarioBookEffect(book, scenarioName);
  }

  const features = createFeatures(book, scenarioStillActive ? scenarioName : undefined);
  const detectors = createDetectorScores(scenarioStillActive ? scenarioName : undefined);
  const events = buildEvents(current, nextTick, scenarioStillActive, scenarioName);
  const activeScenario = scenarioStillActive && current.active_scenario
    ? updateAttackTracker(current.active_scenario, nextTick, detectors.scores)
    : null;

  return {
    ...current,
    active_scenario: activeScenario,
    best_ask: book.best_ask,
    best_bid: book.best_bid,
    book,
    detectors,
    events,
    features,
    mid: book.mid,
    spread: book.spread,
    tick: nextTick
  };
}

function createBook(mid: number, spread: number): OrderBookSnapshot {
  const bids: PriceLevel[] = Array.from({ length: 10 }, (_, index) => ({
    price: roundPrice(mid - spread / 2 - index * 5),
    quantity: roundQuantity(1.8 + index * 0.45)
  }));
  const asks: PriceLevel[] = Array.from({ length: 10 }, (_, index) => ({
    price: roundPrice(mid + spread / 2 + index * 5),
    quantity: roundQuantity(1.7 + index * 0.42)
  }));

  return snapshotFromLevels(bids, asks);
}

function perturbBook(book: OrderBookSnapshot, tick: number): OrderBookSnapshot {
  const midShift = Math.sin(tick / 7) * 1.2 + (Math.random() - 0.5) * 1.8;
  const bids = perturbLevels(book.bids, -midShift);
  const asks = perturbLevels(book.asks, midShift);
  return snapshotFromLevels(bids, asks);
}

function perturbLevels(levels: PriceLevel[], priceShift: number): PriceLevel[] {
  return levels.map((level) => ({
    price: roundPrice(level.price + priceShift * 0.08),
    quantity: roundQuantity(Math.max(0.1, level.quantity + (Math.random() - 0.5) * 0.45))
  }));
}

function applyScenarioBookEffect(book: OrderBookSnapshot, scenario: MockScenarioType): OrderBookSnapshot {
  if (scenario === "spoofing_like_wall") {
    const asks = book.asks.map((level, index) => (
      index === 3
        ? { ...level, agent_id: "ABUSER_01", owner: "abuser", quantity: 48, scenario_name: scenario }
        : level
    ));
    return snapshotFromLevels(book.bids, asks);
  }

  if (scenario === "layering_like") {
    const asks = book.asks.map((level, index) => (
      index >= 1 && index <= 3
        ? { ...level, agent_id: "ABUSER_02", owner: "abuser", quantity: 24 + index * 6, scenario_name: scenario }
        : level
    ));
    return snapshotFromLevels(book.bids, asks);
  }

  if (scenario === "liquidity_evaporation") {
    const bids = book.bids.map((level, index) => ({
      price: index === 0 ? roundPrice(level.price - 8) : level.price,
      quantity: index < 3 ? roundQuantity(level.quantity * 0.25) : level.quantity
    }));
    const asks = book.asks.map((level, index) => ({
      price: index === 0 ? roundPrice(level.price + 8) : level.price,
      quantity: index < 3 ? roundQuantity(level.quantity * 0.25) : level.quantity
    }));
    return snapshotFromLevels(bids, asks);
  }

  return book;
}

function snapshotFromLevels(bids: PriceLevel[], asks: PriceLevel[]): OrderBookSnapshot {
  const bestBid = bids[0]?.price ?? null;
  const bestAsk = asks[0]?.price ?? null;
  return {
    asks,
    best_ask: bestAsk,
    best_bid: bestBid,
    bids,
    mid: bestBid !== null && bestAsk !== null ? roundPrice((bestBid + bestAsk) / 2) : null,
    spread: bestBid !== null && bestAsk !== null ? roundPrice(bestAsk - bestBid) : null
  };
}

function createFeatures(book: OrderBookSnapshot, scenario?: MockScenarioType): MarketFeatures {
  const topBidDepth = sumQuantity(book.bids.slice(0, 3));
  const topAskDepth = sumQuantity(book.asks.slice(0, 3));
  const totalTopDepth = topBidDepth + topAskDepth;
  return {
    cancel_to_trade_ratio: scenario === "quote_stuffing" ? 42 : 3.5,
    depth_change_pct: scenario === "liquidity_evaporation" ? -68 : Math.round((Math.random() - 0.5) * 8),
    depth_top_n: roundQuantity(totalTopDepth),
    imbalance: totalTopDepth > 0 ? roundQuantity((topBidDepth - topAskDepth) / totalTopDepth) : 0,
    message_rate: scenario === "quote_stuffing" ? 260 : 18 + Math.round(Math.random() * 8),
    order_lifetime_ms: scenario === "spoofing_like_wall" ? 1_400 : 8_500,
    spread_bps: book.mid && book.spread ? roundQuantity((book.spread / book.mid) * 10_000) : 0,
    wall_size_ratio: scenario === "spoofing_like_wall" ? 9.2 : scenario === "layering_like" ? 5.5 : 1.1
  };
}

function createDetectorScores(scenario?: MockScenarioType) {
  const scores: DetectorScore[] = [
    score("Spoofing", scenario === "spoofing_like_wall" ? 0.92 : 0.12),
    score("Layering", scenario === "layering_like" ? 0.86 : 0.1),
    score("Quote Stuffing", scenario === "quote_stuffing" ? 0.95 : 0.08),
    score("Liquidity Shock", scenario === "liquidity_evaporation" ? 0.88 : 0.14)
  ];
  return {
    alerts: scores.filter((item) => item.alert),
    scores
  };
}

function updateAttackTracker(
  current: AttackTrackerState,
  tick: number,
  scores: DetectorScore[]
): AttackTrackerState {
  const elapsedTicks = tick - current.start_tick;
  const currentStage = getStageForElapsedTicks(elapsedTicks);
  const confidence = scores.find((scoreItem) => scoreItem.alert)?.confidence ?? 0.18;
  const timestamp = Date.now();

  return {
    ...current,
    current_stage: currentStage,
    stages: createAttackStages(current.start_tick, timestamp, currentStage, confidence, tick),
    status: currentStage
  };
}

function getStageForElapsedTicks(elapsedTicks: number): AttackStage {
  if (elapsedTicks <= 1) {
    return "armed";
  }
  if (elapsedTicks <= 3) {
    return "wall_placed";
  }
  if (elapsedTicks <= 8) {
    return "pressure_phase";
  }
  if (elapsedTicks <= 9) {
    return "cancelled";
  }
  return "incident_confirmed";
}

function createAttackStages(
  startTick: number,
  timestamp: number,
  currentStage: AttackStage,
  confidence: number,
  tick = startTick
): AttackStageSnapshot[] {
  const stages: Array<{ label: string; offset: number; stage: AttackStage }> = [
    { label: "Armed", offset: 0, stage: "armed" },
    { label: "Wall Placed", offset: 2, stage: "wall_placed" },
    { label: "Pressure Phase", offset: 4, stage: "pressure_phase" },
    { label: "Cancelled", offset: 9, stage: "cancelled" },
    { label: "Incident Confirmed", offset: 10, stage: "incident_confirmed" }
  ];
  const currentIndex = stages.findIndex((stageItem) => stageItem.stage === currentStage);

  return stages.map((stageItem, index) => {
    const status = index < currentIndex ? "completed" : index === currentIndex ? "active" : "pending";
    const stageTick = startTick + stageItem.offset;
    return {
      detector_confidence: index <= currentIndex ? confidence : undefined,
      label: stageItem.label,
      stage: stageItem.stage,
      status,
      tick: index <= currentIndex ? stageTick : undefined,
      timestamp: index <= currentIndex ? timestamp - Math.max(0, tick - stageTick) * TICK_MS : undefined
    };
  });
}

function score(name: string, confidence: number): DetectorScore {
  return {
    alert: confidence >= 0.75,
    confidence,
    name,
    severity: confidence >= 0.9 ? "critical" : confidence >= 0.8 ? "high" : "low"
  };
}

function buildEvents(
  current: ArenaState,
  tick: number,
  scenarioStillActive: boolean,
  scenarioName?: MockScenarioType
): AgentEvent[] {
  const baselineEvent: AgentEvent = {
    agent_id: tick % 3 === 0 ? "LiquidityTakerAgent" : tick % 2 === 0 ? "NoiseTraderAgent" : "MarketMakerAgent",
    kind: tick % 2 === 0 ? "normal" : "market_maker",
    price: current.mid ?? BASE_MID,
    quantity: roundQuantity(0.2 + Math.random() * 1.8),
    side: tick % 2 === 0 ? "buy" : "sell",
    symbol: SYMBOL,
    timestamp: Date.now(),
    type: tick % 3 === 0 ? "trade" : "limit_order"
  };
  const events = [baselineEvent, ...current.events];

  if (scenarioName && scenarioStillActive) {
    const spec = scenarioSpecs[scenarioName];
    events.unshift({
      agent_id: spec.agentId,
      kind: "red_team",
      scenario_family: spec.family,
      scenario_id: current.active_scenario?.scenario_id,
      scenario_name: scenarioName,
      symbol: SYMBOL,
      timestamp: Date.now(),
      type: scenarioName === "quote_stuffing" ? "message_rate_spike" : "scenario_pressure"
    });
    events.unshift({
      agent_id: "DetectorEngine",
      kind: "detector",
      scenario_family: spec.family,
      scenario_id: current.active_scenario?.scenario_id,
      scenario_name: scenarioName,
      symbol: SYMBOL,
      timestamp: Date.now(),
      type: "detector_score_update"
    });
  }

  if (current.active_scenario && !scenarioStillActive) {
    events.unshift({
      agent_id: current.active_scenario.agent_id,
      kind: "red_team",
      scenario_family: current.active_scenario.scenario_family,
      scenario_id: current.active_scenario.scenario_id,
      scenario_name: current.active_scenario.scenario_name,
      symbol: SYMBOL,
      timestamp: Date.now(),
      type: "scenario_cancelled"
    });
    events.unshift({
      agent_id: "DetectorEngine",
      kind: "detector",
      scenario_family: current.active_scenario.scenario_family,
      scenario_id: current.active_scenario.scenario_id,
      scenario_name: current.active_scenario.scenario_name,
      symbol: SYMBOL,
      timestamp: Date.now(),
      type: "detector_incident_confirmed"
    });
  }

  return events.slice(0, 40);
}

function sumQuantity(levels: PriceLevel[]) {
  return levels.reduce((total, level) => total + level.quantity, 0);
}

function roundPrice(value: number) {
  return Number(value.toFixed(2));
}

function roundQuantity(value: number) {
  return Number(value.toFixed(3));
}
