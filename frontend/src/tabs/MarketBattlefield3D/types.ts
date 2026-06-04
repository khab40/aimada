export type BattlefieldCell = {
  anomalyScore: number;
  price?: number;
  priceLevel: number;
  side: "bid" | "ask";
  tick: number;
  volume: number;
};

export type BattlefieldEvent = {
  agentId: string;
  description: string;
  severity: number;
  tick: number;
  type: "SPOOF_ORDER" | "CANCEL_BURST" | "PRICE_MOVE" | "DETECTION";
};

export type BattlefieldFrame = {
  cells: BattlefieldCell[];
  events: BattlefieldEvent[];
  midPrice: number;
  spoofingProbability: number;
  tick: number;
};

export type BattlefieldPlaybackState = "playing" | "paused";
