import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  AgentEvent,
  AttackStage,
  AttackStageSnapshot,
  ArenaState,
  AttackTrackerState,
  DetectorScore,
  EvidenceItem,
  ExchangeEvent,
  Incident,
  MarketFeatures,
  OrderBookSnapshot,
  PriceLevel
} from "@/types/arena";
import type { ArenaScenarioType } from "@/scenarios";

export type MockScenarioType = ArenaScenarioType;

type ScenarioSpec = {
  agentId: string;
  durationTicks: number;
  family: string;
  label: string;
};

const DEFAULT_SYMBOL = "BTCUSDT";
const TICK_MS = 500;
const BASE_MID = 68_000;
const BASE_SPREAD = 4;
const demoScenarioOrder: MockScenarioType[] = ["spoofing_like_wall", "layering_like", "quote_stuffing", "liquidity_evaporation"];

const scenarioSpecs: Record<MockScenarioType, ScenarioSpec> = {
  spoofing_like_wall: {
    agentId: "ABUSER_01",
    durationTicks: 10,
    family: "spoofing_like_wall",
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

export function useMockArena({
  demo = false,
  initialScenario = "spoofing_like_wall",
  symbol = DEFAULT_SYMBOL
}: {
  demo?: boolean;
  initialScenario?: MockScenarioType;
  symbol?: string;
} = {}) {
  const [state, setState] = useState<ArenaState>(() => createInitialState(demo, initialScenario, symbol));

  useEffect(() => {
    setState(createInitialState(demo, initialScenario, symbol));
  }, [demo, initialScenario, symbol]);

  useEffect(() => {
    if (!state.running) {
      return undefined;
    }

    const handle = window.setInterval(() => {
      setState((current) => advanceState(current, { demo, symbol }));
    }, TICK_MS);

    return () => window.clearInterval(handle);
  }, [demo, state.running, symbol]);

  const start = useCallback(() => {
    setState((current) => ({ ...current, running: true }));
  }, []);

  const pause = useCallback(() => {
    setState((current) => ({ ...current, running: false }));
  }, []);

  const reset = useCallback(() => {
    setState(createInitialState(demo, initialScenario, symbol));
  }, [demo, initialScenario, symbol]);

  const launchScenario = useCallback((type: MockScenarioType) => {
    setState((current) => {
      const spec = scenarioSpecs[type];
      const activeScenario = createActiveScenario(type, current.tick, 0.18);
      const event: AgentEvent = {
        agent_id: spec.agentId,
        kind: "red_team",
        scenario_family: spec.family,
        scenario_id: activeScenario.scenario_id,
        scenario_name: type,
        symbol,
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
  }, [symbol]);

  return useMemo(
    () => ({
      launchScenario,
      pause,
      reset,
      running: state.running,
      start,
      state,
      symbol,
      tick: state.tick
    }),
    [launchScenario, pause, reset, start, state, symbol]
  );
}

function createInitialState(demo = false, initialScenario: MockScenarioType = "spoofing_like_wall", symbol = DEFAULT_SYMBOL): ArenaState {
  const book = createBook(BASE_MID, BASE_SPREAD);
  const activeScenario = demo ? createActiveScenario(initialScenario, 0, 0.62) : null;
  const features = createFeatures(book, activeScenario?.scenario_name as MockScenarioType | undefined, 0, demo);
  const detectors = createDetectorScores(activeScenario?.scenario_name as MockScenarioType | undefined, 0, demo);
  return {
    active_agents: ["MarketMakerAgent", "NoiseTraderAgent", "LiquidityTakerAgent"],
    active_scenario: activeScenario,
    best_ask: book.best_ask,
    best_bid: book.best_bid,
    book,
    detectors,
    events: [
      {
        agent_id: "MarketMakerAgent",
        price: book.best_bid ?? BASE_MID,
        quantity: 2.4,
        side: "buy",
        symbol,
        timestamp: Date.now(),
        type: "limit_order"
      }
    ],
    exchange_events: createInitialExchangeEvents(book, symbol),
    features,
    mid: book.mid,
    running: demo,
    spread: book.spread,
    tick: 0
  };
}

function advanceState(current: ArenaState, { demo = false, symbol = DEFAULT_SYMBOL }: { demo?: boolean; symbol?: string } = {}): ArenaState {
  const nextTick = current.tick + 1;
  const currentScenario = current.active_scenario ?? (demo ? createActiveScenario(nextDemoScenario(undefined, nextTick), current.tick, 0.58) : null);
  const scenarioName = currentScenario?.scenario_name as MockScenarioType | undefined;
  const spec = scenarioName ? scenarioSpecs[scenarioName] : undefined;
  const elapsedTicks = currentScenario ? nextTick - currentScenario.start_tick : 0;
  const durationTicks = demo && currentScenario ? demoIncidentIntervalTicks(currentScenario.start_tick) : spec?.durationTicks;
  const scenarioStillActive = Boolean(spec && durationTicks !== undefined && elapsedTicks <= durationTicks);

  let book = perturbBook(current.book, nextTick);
  if (scenarioStillActive && scenarioName) {
    book = applyScenarioBookEffect(book, scenarioName);
  }

  const features = createFeatures(book, scenarioStillActive ? scenarioName : undefined, nextTick, demo);
  const detectors = createDetectorScores(scenarioStillActive ? scenarioName : undefined, nextTick, demo);
  const events = buildEvents({ ...current, active_scenario: currentScenario }, nextTick, scenarioStillActive, scenarioName, symbol);
  let activeScenario = scenarioStillActive && currentScenario
    ? updateAttackTracker(currentScenario, nextTick, detectors.scores)
    : null;
  let incidents = current.incidents ?? [];
  let nextEvents = events;

  if (demo && currentScenario && scenarioName && durationTicks !== undefined && elapsedTicks >= durationTicks) {
    const incident = createDemoIncident(currentScenario, nextTick, detectors.scores, features);
    const nextScenarioName = nextDemoScenario(scenarioName, nextTick);
    activeScenario = createActiveScenario(nextScenarioName, nextTick, 0.56);
    incidents = [...incidents, incident].slice(-6);
    nextEvents = [
      {
        agent_id: "DetectorEngine",
        kind: "detector",
        scenario_family: currentScenario.scenario_family,
        scenario_id: currentScenario.scenario_id,
        scenario_name: scenarioName,
        symbol,
        timestamp: Date.now(),
        type: "demo_incident_confirmed"
      },
      {
        agent_id: activeScenario.agent_id,
        kind: "red_team",
        scenario_family: activeScenario.scenario_family,
        scenario_id: activeScenario.scenario_id,
        scenario_name: nextScenarioName,
        symbol,
        timestamp: Date.now(),
        type: "demo_scenario_started"
      },
      ...events
    ].slice(0, 40);
  }

  return {
    ...current,
    active_scenario: activeScenario,
    best_ask: book.best_ask,
    best_bid: book.best_bid,
    book,
    detectors,
    events: nextEvents,
    exchange_events: appendMockExchangeEvents(current, book, nextTick, symbol),
    features,
    incidents,
    mid: book.mid,
    spread: book.spread,
    tick: nextTick
  };
}

function createInitialExchangeEvents(book: OrderBookSnapshot, symbol: string): ExchangeEvent[] {
  return [
    {
      schema_version: 1,
      event_type: "add",
      event_id: "MOCK:add:1",
      sequence: 1,
      source: "simulation",
      source_sequence: null,
      symbol,
      venue: "MOCK",
      tick: 0,
      exchange_timestamp_ns: null,
      received_timestamp_ns: null,
      scenario_id: null,
      scenario_name: null,
      scenario_family: null,
      order_id: "mock-market-maker-bid",
      agent_id: "MarketMakerAgent",
      side: "buy",
      price: book.best_bid ?? BASE_MID,
      quantity: book.bids[0]?.quantity ?? 0.1,
      owner: "normal"
    },
    createMockSnapshotEvent(book, symbol, 0, 2)
  ];
}

function appendMockExchangeEvents(current: ArenaState, book: OrderBookSnapshot, tick: number, symbol: string): ExchangeEvent[] {
  const nextSequence = (current.exchange_events.at(-1)?.sequence ?? 0) + 1;
  const previousPrice = current.book.best_bid ?? BASE_MID;
  const price = book.best_bid ?? previousPrice;
  const modify: ExchangeEvent = {
    schema_version: 1,
    event_type: "modify",
    event_id: `MOCK:modify:${nextSequence}`,
    sequence: nextSequence,
    source: "simulation",
    source_sequence: null,
    symbol,
    venue: "MOCK",
    tick,
    exchange_timestamp_ns: null,
    received_timestamp_ns: null,
    scenario_id: current.active_scenario?.scenario_id ?? null,
    scenario_name: current.active_scenario?.scenario_name ?? null,
    scenario_family: current.active_scenario?.scenario_family ?? null,
    order_id: "mock-market-maker-bid",
    agent_id: "MarketMakerAgent",
    side: "buy",
    previous_price: previousPrice,
    previous_quantity: current.book.bids[0]?.quantity ?? 0.1,
    price,
    quantity: book.bids[0]?.quantity ?? 0.1,
    priority_preserved: price === previousPrice,
    owner: "normal"
  };
  const snapshot = createMockSnapshotEvent(book, symbol, tick, nextSequence + 1);
  return [...current.exchange_events, modify, snapshot].slice(-100);
}

function createMockSnapshotEvent(
  book: OrderBookSnapshot,
  symbol: string,
  tick: number,
  sequence: number
): ExchangeEvent {
  return {
    schema_version: 1,
    event_type: "snapshot",
    event_id: `MOCK:snapshot:${sequence}`,
    sequence,
    source: "simulation",
    source_sequence: null,
    symbol,
    venue: "MOCK",
    tick,
    exchange_timestamp_ns: null,
    received_timestamp_ns: null,
    scenario_id: null,
    scenario_name: null,
    scenario_family: null,
    depth: Math.max(book.bids.length, book.asks.length),
    book
  };
}

function createActiveScenario(type: MockScenarioType, tick: number, confidence: number): AttackTrackerState {
  const spec = scenarioSpecs[type];
  return {
    agent_id: spec.agentId,
    current_stage: "armed",
    scenario_family: spec.family,
    scenario_id: `${type}-${tick}`,
    scenario_name: type,
    start_tick: tick,
    stages: createAttackStages(tick, Date.now(), "armed", confidence),
    status: "armed"
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

function createFeatures(book: OrderBookSnapshot, scenario?: MockScenarioType, tick = 0, demo = false): MarketFeatures {
  const topBidDepth = sumQuantity(book.bids.slice(0, 3));
  const topAskDepth = sumQuantity(book.asks.slice(0, 3));
  const totalTopDepth = topBidDepth + topAskDepth;
  const naturalWave = demo ? Math.sin(tick / 6) : 0;
  return {
    cancel_to_trade_ratio: scenario === "quote_stuffing" ? 34 + Math.round(Math.abs(naturalWave) * 16) : demo ? 8 + Math.round(Math.abs(naturalWave) * 8) : 3.5,
    depth_change_pct: scenario === "liquidity_evaporation" ? -58 - Math.round(Math.abs(naturalWave) * 16) : Math.round((Math.random() - 0.5) * (demo ? 18 : 8)),
    depth_top_n: roundQuantity(totalTopDepth),
    imbalance: totalTopDepth > 0 ? roundQuantity((topBidDepth - topAskDepth) / totalTopDepth) : 0,
    message_rate: scenario === "quote_stuffing" ? 220 + Math.round(Math.abs(naturalWave) * 95) : demo ? 34 + Math.round(Math.abs(naturalWave) * 22) : 18 + Math.round(Math.random() * 8),
    order_lifetime_ms: scenario === "spoofing_like_wall" ? 1_200 + Math.round(Math.abs(naturalWave) * 700) : 8_500,
    spread_bps: book.mid && book.spread ? roundQuantity((book.spread / book.mid) * 10_000) : 0,
    wall_size_ratio: scenario === "spoofing_like_wall" ? 7.8 + roundQuantity(Math.abs(naturalWave) * 2.4) : scenario === "layering_like" ? 5.1 + roundQuantity(Math.abs(naturalWave) * 1.8) : demo ? 1.6 + roundQuantity(Math.abs(naturalWave) * 0.9) : 1.1
  };
}

function createDetectorScores(scenario?: MockScenarioType, tick = 0, demo = false) {
  const primaryConfidence = scenario ? demoConfidenceFor(scenario, tick) : 0;
  const scores: DetectorScore[] = [
    score("Spoofing", scenario === "spoofing_like_wall" ? primaryConfidence : backgroundConfidence(tick, 0, demo), scenario === "spoofing_like_wall"),
    score("Layering", scenario === "layering_like" ? primaryConfidence : backgroundConfidence(tick, 1, demo), scenario === "layering_like"),
    score("Quote Stuffing", scenario === "quote_stuffing" ? primaryConfidence : backgroundConfidence(tick, 2, demo), scenario === "quote_stuffing"),
    score("Liquidity Shock", scenario === "liquidity_evaporation" ? primaryConfidence : backgroundConfidence(tick, 3, demo), scenario === "liquidity_evaporation")
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

function score(name: string, confidence: number, includeEvidence = false): DetectorScore {
  return {
    alert: confidence >= 0.75,
    confidence,
    evidence: includeEvidence ? detectorEvidence(name, confidence) : undefined,
    name,
    severity: confidence >= 0.9 ? "critical" : confidence >= 0.8 ? "high" : confidence >= 0.45 ? "medium" : "low"
  };
}

function detectorEvidence(name: string, confidence: number): EvidenceItem[] {
  return [
    { key: "confidence", label: "Detector confidence", value: confidence.toFixed(2) },
    { key: "pattern", label: "Pattern", value: name },
    { key: "window", label: "Replay window", value: "auto-collected" }
  ];
}

function demoConfidenceFor(scenario: MockScenarioType, tick: number) {
  const phase = scenario === "quote_stuffing" ? 0.7 : scenario === "layering_like" ? 1.4 : scenario === "liquidity_evaporation" ? 2.1 : 0;
  return clampConfidence(0.82 + Math.sin(tick / 5 + phase) * 0.08 + Math.sin(tick / 13) * 0.035);
}

function backgroundConfidence(tick: number, offset: number, demo: boolean) {
  if (!demo) {
    return [0.12, 0.1, 0.08, 0.14][offset] ?? 0.1;
  }
  return clampConfidence(0.24 + Math.sin(tick / 9 + offset) * 0.1 + Math.sin(tick / 17 + offset) * 0.06);
}

function clampConfidence(value: number) {
  return Number(Math.min(0.97, Math.max(0.04, value)).toFixed(2));
}

function demoIncidentIntervalTicks(startTick: number) {
  return 40 + Math.abs((startTick * 17 + 29) % 41);
}

function nextDemoScenario(current: MockScenarioType | undefined, tick: number) {
  if (!current) {
    return demoScenarioOrder[Math.abs(tick) % demoScenarioOrder.length];
  }
  const currentIndex = demoScenarioOrder.indexOf(current);
  return demoScenarioOrder[(currentIndex + 1) % demoScenarioOrder.length];
}

function createDemoIncident(
  scenario: AttackTrackerState,
  tick: number,
  scores: DetectorScore[],
  features: MarketFeatures
): Incident {
  const topScore = [...scores].sort((left, right) => right.confidence - left.confidence)[0] ?? score("Smart Detection", 0.82, true);
  const severity = topScore.confidence >= 0.9 ? "Critical" : topScore.confidence >= 0.8 ? "High" : "Medium";
  return {
    agent: scenario.agent_id,
    confidence: topScore.confidence,
    evidence: [
      { key: "message_rate", label: "Message rate", value: features.message_rate, unit: "updates/sec" },
      { key: "wall_size_ratio", label: "Wall size ratio", value: features.wall_size_ratio },
      { key: "cancel_to_trade_ratio", label: "Cancel/trade ratio", value: features.cancel_to_trade_ratio },
      { key: "depth_change_pct", label: "Depth change", value: features.depth_change_pct, unit: "%" }
    ],
    explanation: `${topScore.name} confidence rose during a continuously running demo scenario and the evidence window was collected automatically.`,
    id: `DEMO-${scenario.scenario_id}-${tick}`,
    scenario_family: scenario.scenario_family,
    scenario_id: scenario.scenario_id,
    severity,
    tick,
    title: `${topScore.name} demo incident`,
    type: scenario.scenario_name
  };
}

function buildEvents(
  current: ArenaState,
  tick: number,
  scenarioStillActive: boolean,
  scenarioName?: MockScenarioType,
  symbol = DEFAULT_SYMBOL
): AgentEvent[] {
  const baselineEvent: AgentEvent = {
    agent_id: tick % 3 === 0 ? "LiquidityTakerAgent" : tick % 2 === 0 ? "NoiseTraderAgent" : "MarketMakerAgent",
    kind: tick % 2 === 0 ? "normal" : "market_maker",
    price: current.mid ?? BASE_MID,
    quantity: roundQuantity(0.2 + Math.random() * 1.8),
    side: tick % 2 === 0 ? "buy" : "sell",
    symbol,
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
      symbol,
      timestamp: Date.now(),
      type: scenarioName === "quote_stuffing" ? "message_rate_spike" : "scenario_pressure"
    });
    events.unshift({
      agent_id: "DetectorEngine",
      kind: "detector",
      scenario_family: spec.family,
      scenario_id: current.active_scenario?.scenario_id,
      scenario_name: scenarioName,
      symbol,
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
      symbol,
      timestamp: Date.now(),
      type: "scenario_cancelled"
    });
    events.unshift({
      agent_id: "DetectorEngine",
      kind: "detector",
      scenario_family: current.active_scenario.scenario_family,
      scenario_id: current.active_scenario.scenario_id,
      scenario_name: current.active_scenario.scenario_name,
      symbol,
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
