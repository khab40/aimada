import type {
  AiExplanation,
  AlertExplanationInput,
  AttackScenario,
  AttackScenarioGeneratorClient,
  AttackScenarioInput,
  ExperimentArtifact,
  ExperimentBatchConfig,
  GeneratedScenario,
  IncidentReport,
  IncidentReportInput,
  MarketStateInput,
  MarketSummary,
  NebiusAiClient,
  NebiusDeploymentHealthClient,
  NebiusScenarioClient,
  NebiusServerlessClient,
  NebiusStorageClient,
  ScenarioGridConfig,
  ServerlessExperimentJob,
  ServiceHealth,
  StrategyInput,
  StrategySuggestion
} from "@/features/nebius/types";

const now = () => new Date().toISOString();

export class MockNebiusAiClient implements NebiusAiClient {
  async explainCurrentAlert(input: AlertExplanationInput): Promise<AiExplanation> {
    return {
      title: "AI Investigator",
      suspicion: "High",
      findings: [
        `Agent ${input.agentId} placed a large sell wall near the best ask.`,
        "The order represented 42% of visible ask liquidity.",
        "The order was cancelled after 1.8 seconds.",
        "The mid-price moved downward before cancellation.",
        `Agent ${input.agentId} bought aggressively after the induced move.`
      ],
      recommendedAction: `Freeze Agent ${input.agentId} and inspect all cancelled orders in the last 60 seconds.`,
      latencySec: 1.4,
      tokensUsed: 1842,
      createdAt: now()
    };
  }

  async generateIncidentReport(input: IncidentReportInput): Promise<IncidentReport> {
    return {
      title: `Incident report for ${input.incidentId}`,
      severity: "High",
      sections: [
        `${input.scenario} produced a high-confidence surveillance alert.`,
        "Evidence bundle includes replay, detector metrics, alert log, and generated narrative.",
        "Recommended review scope is the alert window plus 60 seconds of preceding cancellations."
      ],
      latencySec: 1.8,
      tokensUsed: 2310
    };
  }

  async suggestRedTeamStrategy(input: StrategyInput): Promise<StrategySuggestion> {
    return {
      title: "Bounded red-team strategy",
      bullets: [
        `Stress the ${input.detectorFamily} detector with varied order lifetime and wall distance.`,
        `Use ${input.marketRegime} liquidity conditions and keep all activity inside the simulator.`,
        "Generate normal-market controls alongside attack variants for false-positive measurement."
      ],
      safetyNote: "Synthetic simulator-only guidance. Do not use against real markets.",
      latencySec: 1.1,
      tokensUsed: 1460
    };
  }

  async summarizeMarketRegime(input: MarketStateInput): Promise<MarketSummary> {
    return {
      regime: `${input.volatility} volatility / ${input.liquidity} liquidity`,
      summary: "The current book is suitable for spoofing and layering robustness tests because visible depth is uneven and cancellation pressure is elevated.",
      watchItems: ["Spread widening", "Cancel-to-trade ratio", "Top-of-book wall ratio", "Mid-price drift after cancellations"],
      latencySec: 0.9,
      tokensUsed: 980
    };
  }
}

export class MockAttackScenarioGeneratorClient implements AttackScenarioGeneratorClient {
  private sequence = 42;

  async generateAttackScenario(input: AttackScenarioInput): Promise<AttackScenario> {
    return this.buildScenario(input, this.sequence++);
  }

  async generateAttackVariants(input: AttackScenarioInput, count: number): Promise<AttackScenario[]> {
    return Array.from({ length: count }, (_, index) => this.buildScenario(input, this.sequence + index));
  }

  private buildScenario(input: AttackScenarioInput, numericId: number): AttackScenario {
    const attackType = normalizeAttackType(input.attackType);
    const marketRegime = input.marketCondition.toLowerCase().replaceAll(" ", "_");
    const stealthLevel = input.stealthLevel.toLowerCase() as AttackScenario["stealthLevel"];
    const difficulty = input.detectorDifficulty.toLowerCase() as AttackScenario["expectedDetectorDifficulty"];
    const redTeamAgents = Array.from({ length: input.redTeamAgentCount }, (_, index) => `R-${17 + index}`);
    const durationTicks = input.attackDuration === "Short" ? 120 : input.attackDuration === "Medium" ? 300 : 720;
    const targetSide = input.objective === "Sell higher" ? "buy" : input.objective === "Trigger stop-loss cascade" ? "both" : "sell";
    const realTradeSide = input.objective === "Sell higher" ? "sell" : "buy";
    const id = `ATTACK-${String(numericId).padStart(3, "0")}`;
    const name = `${input.marketCondition.replace(" liquidity", " Liquidity")} ${targetSide === "sell" ? "Sell-Side" : targetSide === "buy" ? "Buy-Side" : "Two-Sided"} ${input.attackType}`;

    return {
      id,
      attackType,
      cancelDelayTicks: input.stealthLevel === "Subtle" ? 12 : input.stealthLevel === "Medium" ? 25 : 40,
      durationTicks,
      expectedDetectorDifficulty: difficulty,
      expectedSignals: expectedSignalsFor(attackType, targetSide),
      fakeOrderLevels: attackType === "quote_stuffing" ? 8 : 3,
      fakeOrderSizeMultiplier: input.stealthLevel === "Subtle" ? 4 : input.stealthLevel === "Medium" ? 8 : 12,
      marketRegime,
      name,
      objective: objectiveText(input.objective),
      planSteps: planStepsFor({ attackType: input.attackType, durationTicks, id, realTradeSide, redTeamAgents, targetSide }),
      realTradeSide,
      realTradeSize: input.redTeamAgentCount * 120,
      redTeamAgents,
      startTick: 1200,
      stealthLevel,
      targetSide
    };
  }
}

export class MockNebiusServerlessClient implements NebiusServerlessClient {
  private jobs: ServerlessExperimentJob[] = [
    { id: "JOB-1042", scenario: "Spoofing", runs: 100, status: "running", alerts: 68, precision: 0.82, estimatedCostUsd: 0.41 },
    { id: "JOB-1043", scenario: "Normal", runs: 100, status: "done", alerts: 4, estimatedCostUsd: 0.37 },
    { id: "JOB-1044", scenario: "Layering", runs: 50, status: "queued" }
  ];

  async submitExperimentBatch(config: ExperimentBatchConfig): Promise<ServerlessExperimentJob> {
    const job: ServerlessExperimentJob = {
      id: `JOB-${Math.floor(1100 + Math.random() * 8000)}`,
      scenario: config.attackType,
      runs: config.numberOfRuns,
      status: "queued",
      alerts: Math.max(1, Math.round(config.numberOfRuns * 0.58)),
      precision: config.detector === "Rule-based" ? 0.82 : 0.76,
      estimatedCostUsd: Number((0.21 + config.numberOfRuns * config.agentsPerRun * 0.00004).toFixed(2))
    };
    this.jobs = [job, ...this.jobs];
    return job;
  }

  async listJobs(): Promise<ServerlessExperimentJob[]> {
    return this.jobs;
  }
}

export class MockNebiusScenarioClient implements NebiusScenarioClient {
  async generateScenarioGrid(config: ScenarioGridConfig): Promise<GeneratedScenario[]> {
    return [
      `${config.liquidity} liquidity + ${config.attackIntensity.toLowerCase()} spoofing`,
      "Normal liquidity + subtle layering",
      `${config.marketVolatility} volatility + quote stuffing`,
      "Deep book + institutional TWAP + spoofing",
      `${config.numberOfAgents} agents + ${config.latencyModel.toLowerCase()} latency + threshold ${config.detectionThreshold.toFixed(2)}`
    ].map((label, index) => ({
      id: `SCN-${index + 1}`,
      label,
      selected: index < 3
    }));
  }
}

export class MockNebiusStorageClient implements NebiusStorageClient {
  private artifacts: ExperimentArtifact[] = [
    { path: "/replays/spoofing_042.json", type: "replay", sizeLabel: "2.4 MB", createdAt: "2026-06-09 10:42", status: "stored" },
    { path: "/metrics/spoofing_042_metrics.json", type: "metrics", sizeLabel: "180 KB", createdAt: "2026-06-09 10:43", status: "stored" },
    { path: "/alerts/spoofing_042_alerts.json", type: "alerts", sizeLabel: "44 KB", createdAt: "2026-06-09 10:44", status: "stored" },
    { path: "/reports/incident_R17_042.md", type: "report", sizeLabel: "12 KB", createdAt: "2026-06-09 10:45", status: "stored" },
    { path: "/datasets/generated_lob_events_2026_06_09.parquet", type: "dataset", sizeLabel: "86 MB", createdAt: "2026-06-09 10:48", status: "stored" }
  ];

  async listArtifacts(): Promise<ExperimentArtifact[]> {
    return this.artifacts;
  }

  async saveCurrentReplay(): Promise<ExperimentArtifact> {
    const artifact = { path: `/replays/spoofing_${Math.floor(Math.random() * 900 + 100)}.json`, type: "replay" as const, sizeLabel: "2.7 MB", createdAt: "just now", status: "stored" as const };
    this.artifacts = [artifact, ...this.artifacts];
    return artifact;
  }

  async saveScenarioTemplate(scenario: AttackScenario): Promise<ExperimentArtifact> {
    const artifact = { path: `/scenarios/${scenario.id.toLowerCase()}_template.json`, type: "scenario_template" as const, sizeLabel: "18 KB", createdAt: "just now", status: "stored" as const };
    this.artifacts = [artifact, ...this.artifacts];
    return artifact;
  }

  async exportDataset(): Promise<ExperimentArtifact> {
    const artifact = { path: `/datasets/generated_lob_events_${Date.now()}.parquet`, type: "dataset" as const, sizeLabel: "91 MB", createdAt: "just now", status: "stored" as const };
    this.artifacts = [artifact, ...this.artifacts];
    return artifact;
  }

  async generateTrainingData(): Promise<ExperimentArtifact> {
    const artifact = { path: `/datasets/training_labels_${Date.now()}.jsonl`, type: "dataset" as const, sizeLabel: "34 MB", createdAt: "just now", status: "pending" as const };
    this.artifacts = [artifact, ...this.artifacts];
    return artifact;
  }
}

function normalizeAttackType(value: AttackScenarioInput["attackType"]): AttackScenario["attackType"] {
  const mapping: Record<AttackScenarioInput["attackType"], AttackScenario["attackType"]> = {
    "Layering": "layering",
    "Mixed Attack": "mixed",
    "Momentum Ignition": "momentum_ignition",
    "Quote Stuffing": "quote_stuffing",
    "Spoofing": "spoofing"
  };
  return mapping[value];
}

function objectiveText(value: AttackScenarioInput["objective"]) {
  const mapping: Record<AttackScenarioInput["objective"], string> = {
    "Buy cheaper": "Induce downward mid-price move, then buy cheaper",
    "Distort visible liquidity": "Distort visible liquidity and measure detector response",
    "Sell higher": "Induce upward mid-price move, then sell higher",
    "Test detector weakness": "Stress detector thresholds with bounded synthetic behavior",
    "Trigger stop-loss cascade": "Create synthetic pressure to trigger a simulated stop-loss cascade"
  };
  return mapping[value];
}

function expectedSignalsFor(attackType: AttackScenario["attackType"], targetSide: AttackScenario["targetSide"]) {
  if (attackType === "spoofing") {
    return [
      `large visible ${targetSide === "buy" ? "buy-side" : "sell-side"} wall`,
      "fast cancellation before execution",
      "order book imbalance flip",
      "mid-price movement before cancellation",
      "opposite-side real trade after cancellation"
    ];
  }
  if (attackType === "quote_stuffing") {
    return ["message-rate burst", "high cancel-to-trade ratio", "short order lifetime", "temporary spread widening"];
  }
  if (attackType === "layering") {
    return ["multi-level fake depth", "staggered cancellations", "persistent side imbalance", "price pressure without durable execution"];
  }
  if (attackType === "momentum_ignition") {
    return ["aggressive sweep", "short-lived price acceleration", "follow-on cancellations", "reversal after ignition"];
  }
  return ["combined spoofing and layering signatures", "mixed-side pressure", "high message rate", "timed real trades"];
}

function planStepsFor({
  attackType,
  durationTicks,
  id,
  realTradeSide,
  redTeamAgents,
  targetSide
}: {
  attackType: AttackScenarioInput["attackType"];
  durationTicks: number;
  id: string;
  realTradeSide: "buy" | "sell";
  redTeamAgents: string[];
  targetSide: "buy" | "sell" | "both";
}) {
  const agent = redTeamAgents[0] ?? "R-17";
  return [
    `At tick 1200, Agent ${agent} starts ${id} with a ${attackType.toLowerCase()} pattern.`,
    `Place synthetic ${targetSide === "both" ? "two-sided" : targetSide} pressure near the best quote.`,
    "Scale fake order size above average visible depth while keeping the plan inside the simulator.",
    `Hold the pattern for a bounded ${durationTicks} ticks with randomized timing.`,
    "Cancel fake orders before they execute.",
    `Submit a real ${realTradeSide} order after the induced price move.`,
    "Repeat the pattern twice with randomized delay and archive detector evidence."
  ];
}

export class MockDeploymentHealthClient implements NebiusDeploymentHealthClient {
  private services: ServiceHealth[] = [
    { name: "Frontend", status: "mock", lastCheckedAt: now() },
    { name: "Backend API", status: "mock", lastCheckedAt: now() },
    { name: "Simulation Engine", status: "mock", lastCheckedAt: now() },
    { name: "WebSocket Stream", status: "mock", lastCheckedAt: now() },
    { name: "Nebius AI Proxy", status: "mock", lastCheckedAt: now() },
    { name: "Managed Experiment Runner", status: "mock", lastCheckedAt: now() },
    { name: "Object Storage", status: "mock", lastCheckedAt: now() }
  ];

  async listServices(): Promise<ServiceHealth[]> {
    return this.services;
  }

  async pingAi(): Promise<ServiceHealth> {
    return this.update("Nebius AI Proxy", "mock");
  }

  async testServerlessJob(): Promise<ServiceHealth> {
    return this.update("Managed Experiment Runner", "mock");
  }

  async testStorageWrite(): Promise<ServiceHealth> {
    return this.update("Object Storage", "mock");
  }

  async restartSimulationEngine(): Promise<ServiceHealth> {
    return this.update("Simulation Engine", "mock");
  }

  private update(name: string, status: ServiceHealth["status"]) {
    const updated = { name, status, lastCheckedAt: now() };
    this.services = this.services.map((service) => service.name === name ? updated : service);
    return updated;
  }
}
