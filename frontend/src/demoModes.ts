import type { MockScenarioType } from "@/hooks/useMockArena";

export type ProductDemoMode = "real" | "two-model" | "streaming";

export type ProductDemoConfig = {
  aiInvestigationMode: string;
  attackPattern: string;
  detectorProfile: string;
  id: ProductDemoMode;
  label: string;
  marketSymbol: string;
  models: string;
  scenarioType: MockScenarioType;
  title: string;
};

export const productDemoConfigs: ProductDemoConfig[] = [
  {
    aiInvestigationMode: "Structured incident explanation",
    attackPattern: "Spoofing-like ask wall",
    detectorProfile: "Wall-size + cancel timing detector",
    id: "real",
    label: "Best for live connected demo",
    marketSymbol: "BTCUSDT",
    models: "Nebius AI incident explainer",
    scenarioType: "spoofing_like_wall",
    title: "Real Nebius AI Run"
  },
  {
    aiInvestigationMode: "Classifier then reasoning investigation",
    attackPattern: "Layering-like price pressure",
    detectorProfile: "Fast classifier + reasoning model",
    id: "two-model",
    label: "Best for showing AI architecture",
    marketSymbol: "ETHUSDT",
    models: "Fast classifier, reasoning model",
    scenarioType: "layering_like",
    title: "Two-Model Pipeline"
  },
  {
    aiInvestigationMode: "Stepwise streamed explanation",
    attackPattern: "Quote-stuffing burst",
    detectorProfile: "Streaming evidence retriever",
    id: "streaming",
    label: "Best for visual impact",
    marketSymbol: "SOLUSDT",
    models: "Streaming investigator",
    scenarioType: "quote_stuffing",
    title: "Streaming Explanation"
  }
];

export function getProductDemoConfig(value: string | null | undefined) {
  return productDemoConfigs.find((config) => config.id === value) ?? null;
}
