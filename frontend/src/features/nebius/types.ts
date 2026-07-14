export type NebiusRuntimeStatus = {
  cloudStatus: "checking" | "online" | "offline" | "degraded";
  aiEndpointStatus: "checking" | "ready" | "busy" | "offline" | "not-configured";
  serverlessStatus: "checking" | "idle" | "running" | "error" | "not-configured";
  storageStatus: "checking" | "synced" | "pending" | "error" | "not-configured";
  region: string;
  mode: "local" | "nebius-cloud";
  activeSimulation: string;
  runningAgents: number;
  ticksProcessed: number;
  eventsPerSecond: number;
  websocketStatus: "live" | "disconnected";
};

export type AlertExplanationInput = {
  alertId: string;
  agentId: string;
  pattern: string;
  confidence: number;
};

export type AiExplanation = {
  title: string;
  suspicion: "Low" | "Medium" | "High";
  findings: string[];
  recommendedAction: string;
  latencySec: number;
  tokensUsed: number;
  createdAt: string;
};

export type IncidentReportInput = {
  incidentId: string;
  scenario: string;
};

export type IncidentReport = {
  title: string;
  sections: string[];
  severity: "Low" | "Medium" | "High" | "Critical";
  latencySec: number;
  tokensUsed: number;
};

export type StrategyInput = {
  detectorFamily: string;
  marketRegime: string;
};

export type StrategySuggestion = {
  title: string;
  bullets: string[];
  safetyNote: string;
  latencySec: number;
  tokensUsed: number;
};

export type MarketStateInput = {
  volatility: string;
  liquidity: string;
};

export type MarketSummary = {
  regime: string;
  summary: string;
  watchItems: string[];
  latencySec: number;
  tokensUsed: number;
};

export interface NebiusAiClient {
  explainCurrentAlert(input: AlertExplanationInput): Promise<AiExplanation>;
  generateIncidentReport(input: IncidentReportInput): Promise<IncidentReport>;
  suggestRedTeamStrategy(input: StrategyInput): Promise<StrategySuggestion>;
  summarizeMarketRegime(input: MarketStateInput): Promise<MarketSummary>;
}

export type AttackScenarioInput = {
  attackType: "Spoofing" | "Layering" | "Quote Stuffing" | "Momentum Ignition" | "Mixed Attack";
  marketCondition: "Thin liquidity" | "Normal liquidity" | "High volatility" | "News shock" | "Low activity period";
  objective: "Buy cheaper" | "Sell higher" | "Trigger stop-loss cascade" | "Distort visible liquidity" | "Test detector weakness";
  stealthLevel: "Obvious" | "Medium" | "Subtle";
  attackDuration: "Short" | "Medium" | "Long";
  redTeamAgentCount: 1 | 2 | 5 | 10;
  detectorDifficulty: "Easy" | "Medium" | "Hard";
};

export type AttackScenario = {
  id: string;
  name: string;
  attackType: "spoofing" | "layering" | "quote_stuffing" | "momentum_ignition" | "mixed";
  targetSide: "buy" | "sell" | "both";
  objective: string;
  marketRegime: string;
  redTeamAgents: string[];
  startTick: number;
  durationTicks: number;
  fakeOrderLevels?: number;
  fakeOrderSizeMultiplier?: number;
  cancelDelayTicks?: number;
  realTradeSide?: "buy" | "sell";
  realTradeSize?: number;
  stealthLevel: "obvious" | "medium" | "subtle";
  expectedDetectorDifficulty: "easy" | "medium" | "hard";
  expectedSignals: string[];
  planSteps: string[];
};

export interface AttackScenarioGeneratorClient {
  generateAttackScenario(input: AttackScenarioInput): Promise<AttackScenario>;
  generateAttackVariants(input: AttackScenarioInput, count: number): Promise<AttackScenario[]>;
}

export type ExperimentBatchConfig = {
  scenarioFamily: string;
  numberOfRuns: number;
  agentsPerRun: number;
  attackType: string;
  detector: string;
  sourceAttackScenarioId?: string;
  outputs: {
    storeReplay: boolean;
    storeMetrics: boolean;
    storeAlerts: boolean;
    generateIncidentReport: boolean;
  };
};

export type ServerlessExperimentJob = {
  id: string;
  scenario: string;
  runs: number;
  status: "queued" | "running" | "done" | "failed";
  alerts?: number;
  precision?: number;
  estimatedCostUsd?: number;
};

export interface NebiusServerlessClient {
  submitExperimentBatch(config: ExperimentBatchConfig): Promise<ServerlessExperimentJob>;
  listJobs(): Promise<ServerlessExperimentJob[]>;
}

export type ScenarioGridConfig = {
  marketVolatility: "Low" | "Medium" | "High";
  liquidity: "Thin" | "Normal" | "Deep";
  numberOfAgents: 10 | 50 | 100 | 500;
  attackIntensity: "Subtle" | "Medium" | "Aggressive";
  detectionThreshold: number;
  latencyModel: "None" | "Random" | "Agent-specific";
};

export type GeneratedScenario = {
  id: string;
  label: string;
  selected: boolean;
};

export interface NebiusScenarioClient {
  generateScenarioGrid(config: ScenarioGridConfig): Promise<GeneratedScenario[]>;
}

export type ExperimentArtifact = {
  path: string;
  type: "replay" | "metrics" | "alerts" | "report" | "dataset" | "scenario_template";
  sizeLabel: string;
  createdAt: string;
  status: "stored" | "pending" | "failed";
};

export interface NebiusStorageClient {
  listArtifacts(): Promise<ExperimentArtifact[]>;
  saveCurrentReplay(): Promise<ExperimentArtifact>;
  saveScenarioTemplate(scenario: AttackScenario): Promise<ExperimentArtifact>;
  exportDataset(): Promise<ExperimentArtifact>;
  generateTrainingData(): Promise<ExperimentArtifact>;
}

export type NebiusUsageMetrics = {
  aiEndpointCallsToday: number;
  averageLlmLatencySec: number;
  serverlessJobsRun: number;
  simulationEventsGenerated: number;
  replayStorageMb: number;
  estimatedCostUsd: number;
  tokensUsed: number;
};

export type ServiceHealth = {
  name: string;
  status: "healthy" | "running" | "connected" | "ready" | "degraded" | "error" | "mock";
  lastCheckedAt: string;
};

export interface NebiusDeploymentHealthClient {
  listServices(): Promise<ServiceHealth[]>;
  pingAi(): Promise<ServiceHealth>;
  testServerlessJob(): Promise<ServiceHealth>;
  testStorageWrite(): Promise<ServiceHealth>;
  restartSimulationEngine(): Promise<ServiceHealth>;
}
