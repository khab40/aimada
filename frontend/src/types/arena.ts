export type PriceLevel = {
  agent_id?: string;
  owner?: "normal" | "abuser" | string;
  price: number;
  quantity: number;
  scenario_id?: string;
  scenario_name?: string;
};

export type OrderBookSnapshot = {
  bids: PriceLevel[];
  asks: PriceLevel[];
  best_bid: number | null;
  best_ask: number | null;
  mid: number | null;
  spread: number | null;
};

export type MarketFeatures = {
  spread_bps: number;
  depth_top_n: number;
  imbalance: number;
  order_book_imbalance?: number;
  top_n_bid_depth?: number;
  top_n_ask_depth?: number;
  message_rate: number;
  message_rate_per_sec?: number;
  cancel_to_trade_ratio: number;
  order_lifetime_ms: number;
  wall_size_ratio: number;
  depth_change_pct: number;
};

export type DetectorScore = {
  name: string;
  confidence: number;
  alert: boolean;
  severity?: "low" | "medium" | "high" | "critical";
  evidence?: EvidenceItem[];
};

export type DetectorScores = {
  scores: DetectorScore[];
  alerts: DetectorScore[];
};

export type AgentEvent = {
  type: string;
  timestamp?: number;
  order_id?: string;
  aggressor_order_id?: string;
  resting_order_id?: string;
  agent_id?: string;
  aggressor_agent_id?: string;
  resting_agent_id?: string;
  side?: "buy" | "sell";
  price?: number;
  quantity?: number;
  scenario_id?: string | null;
  scenario_name?: string | null;
  scenario_family?: string | null;
  [key: string]: unknown;
};

export type EvidenceItem = {
  key: string;
  label: string;
  value: string | number | boolean;
  unit?: string;
  interpretation?: string;
};

export type Incident = {
  id: string;
  title: string;
  type: string;
  agent: string;
  confidence: number;
  severity: "Low" | "Medium" | "High" | "Critical";
  evidence: EvidenceItem[];
  explanation: string;
  scenario_id?: string;
  scenario_family?: string;
};

export type AttackStage =
  | "armed"
  | "wall_placed"
  | "pressure_phase"
  | "wall_cancelled"
  | "cancelled"
  | "incident_confirmed"
  | "done";

export type AttackStageStatus = "pending" | "active" | "completed";

export type AttackStageSnapshot = {
  detector_confidence?: number;
  label: string;
  stage: AttackStage;
  status: AttackStageStatus;
  tick?: number;
  timestamp?: number;
};

export type AttackTrackerState = {
  scenario_id: string;
  scenario_name: string;
  scenario_family: string;
  agent_id: string;
  current_stage?: AttackStage;
  start_tick: number;
  stages?: AttackStageSnapshot[];
  status: AttackStage | string;
  evidence?: EvidenceItem[];
};

export type ArenaState = {
  tick: number;
  running: boolean;
  events: AgentEvent[];
  book: OrderBookSnapshot;
  best_bid: number | null;
  best_ask: number | null;
  mid: number | null;
  spread: number | null;
  active_agents: string[];
  active_scenario: AttackTrackerState | null;
  detectors: DetectorScores;
  incidents?: Incident[];
  features?: Partial<MarketFeatures>;
};

export type ArenaWebSocketMessage = {
  type: "arena_state";
  version: number;
  timestamp: string;
  payload: ArenaState;
};

export type ScenarioConfig = {
  label: string;
  slug: string;
  scenario_family: string;
  agent_id: string;
  description: string;
  launch_endpoint?: string;
  parameters?: Record<string, unknown>;
  market_regime?: "calm" | "volatile" | "thin_liquidity";
  goal?: "obvious" | "stealth" | "hard_to_detect";
  source?: "nebius" | "mock";
  expected_detector_risk?: number;
  safety_note?: string;
};

export type BenchmarkResult = {
  avg_detection_latency_ms?: number;
  scenario: string;
  precision: number;
  recall: number;
  f1: number;
};
