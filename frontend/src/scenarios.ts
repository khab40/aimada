export const arenaScenarioTypes = [
  "spoofing_like_wall",
  "layering_like",
  "quote_stuffing",
  "liquidity_evaporation"
] as const;

export type ArenaScenarioType = (typeof arenaScenarioTypes)[number];

export const arenaScenarioLabels = {
  layering_like: "Layering-like Pattern",
  liquidity_evaporation: "Liquidity Evaporation",
  quote_stuffing: "Quote Stuffing Burst",
  spoofing_like_wall: "Spoofing-like Wall"
} as const satisfies Record<ArenaScenarioType, string>;

export type ArenaScenarioLabel = (typeof arenaScenarioLabels)[ArenaScenarioType];
