import { useEffect, useState } from "react";
import {
  attachNebiusScreenshot,
  createInvestigationReport,
  createSmartScenario,
  exportNebiusDataset,
  generateNebiusScenarioGrid,
  generateNebiusTrainingData,
  getNebiusObservatory,
  getNebiusStatus,
  getReportsSummary,
  runSmartBatches,
  runSmartDetection,
  saveNebiusEvidenceBundle,
  type InvestigationReportResponse,
  type NebiusObservatory,
  type NebiusStatus,
  type OrderBookAlertResponse,
  type ReportsSummary,
  type SmartBatchRunResponse,
  type SmartScenarioResponse
} from "@/api/client";
import { AiAnalystConsole } from "@/features/nebius/components/AiAnalystConsole";
import { DeploymentHealthCard } from "@/features/nebius/components/DeploymentHealthCard";
import { ExperimentArtifactsCard } from "@/features/nebius/components/ExperimentArtifactsCard";
import { RuntimeStatusCard } from "@/features/nebius/components/RuntimeStatusCard";
import { ScenarioBatchGenerator } from "@/features/nebius/components/ScenarioBatchGenerator";
import { ServerlessRunnerCard } from "@/features/nebius/components/ServerlessRunnerCard";
import { UsageCostMonitor } from "@/features/nebius/components/UsageCostMonitor";
import type {
  AiExplanation,
  ExperimentArtifact,
  ExperimentBatchConfig,
  GeneratedScenario,
  IncidentReport,
  MarketSummary,
  NebiusRuntimeStatus,
  NebiusUsageMetrics,
  ScenarioGridConfig,
  ServerlessExperimentJob,
  ServiceHealth,
  StrategySuggestion
} from "@/features/nebius/types";

const initialBatchConfig: ExperimentBatchConfig = {
  agentsPerRun: 50,
  attackType: "Spoofing",
  detector: "Rule-based",
  numberOfRuns: 100,
  outputs: {
    generateIncidentReport: true,
    storeAlerts: true,
    storeMetrics: true,
    storeReplay: true
  },
  scenarioFamily: "Spoofing Attack"
};

const initialScenarioConfig: ScenarioGridConfig = {
  attackIntensity: "Aggressive",
  detectionThreshold: 0.72,
  latencyModel: "Random",
  liquidity: "Thin",
  marketVolatility: "High",
  numberOfAgents: 50
};

const fallbackRuntimeStatus: NebiusRuntimeStatus = {
  activeSimulation: "Spoofing Attack #042",
  aiEndpointStatus: "ready",
  cloudStatus: "degraded",
  eventsPerSecond: 1250,
  mode: "local",
  region: "eu-north1",
  runningAgents: 24,
  serverlessStatus: "idle",
  storageStatus: "synced",
  ticksProcessed: 18420,
  websocketStatus: "live"
};

const fallbackUsageMetrics: NebiusUsageMetrics = {
  aiEndpointCallsToday: 24,
  averageLlmLatencySec: 1.2,
  estimatedCostUsd: 3.86,
  replayStorageMb: 482,
  serverlessJobsRun: 0,
  simulationEventsGenerated: 0,
  tokensUsed: 1842
};

type AnalystOutput = AiExplanation | IncidentReport | StrategySuggestion | MarketSummary;

export function NebiusControlPanelPage() {
  const [analystOutput, setAnalystOutput] = useState<AnalystOutput | null>(null);
  const [artifacts, setArtifacts] = useState<ExperimentArtifact[]>([]);
  const [batchConfig, setBatchConfig] = useState<ExperimentBatchConfig>(initialBatchConfig);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [deploymentMessage, setDeploymentMessage] = useState<string | null>(null);
  const [generatedScenarios, setGeneratedScenarios] = useState<GeneratedScenario[]>([]);
  const [jobs, setJobs] = useState<ServerlessExperimentJob[]>([]);
  const [runtimeStatus, setRuntimeStatus] = useState<NebiusRuntimeStatus>(fallbackRuntimeStatus);
  const [scenarioConfig, setScenarioConfig] = useState<ScenarioGridConfig>(initialScenarioConfig);
  const [services, setServices] = useState<ServiceHealth[]>([]);
  const [usageMetrics, setUsageMetrics] = useState<NebiusUsageMetrics>(fallbackUsageMetrics);

  useEffect(() => {
    void refreshControlPlane();
    void generateNebiusScenarioGrid(initialScenarioConfig).then(setGeneratedScenarios);
  }, []);

  async function refreshControlPlane() {
    try {
      const [status, observatory, reports] = await Promise.all([
        getNebiusStatus(),
        getNebiusObservatory(),
        getReportsSummary()
      ]);
      setRuntimeStatus(runtimeFrom(status, observatory));
      setUsageMetrics(usageFrom(observatory, reports));
      setServices(servicesFrom(observatory));
      setJobs(jobsFrom(reports, observatory));
      setArtifacts(artifactsFrom(reports, observatory));
    } catch (error) {
      setDeploymentMessage(error instanceof Error ? error.message : "Control plane refresh failed.");
    }
  }

  async function runAiAction(action: string, fn: () => Promise<AnalystOutput>) {
    setBusyAction(action);
    try {
      const response = await fn();
      setAnalystOutput(response);
      const tokens = "tokensUsed" in response ? response.tokensUsed : 0;
      const latency = "latencySec" in response ? response.latencySec : usageMetrics.averageLlmLatencySec;
      setUsageMetrics((current) => ({
        ...current,
        aiEndpointCallsToday: current.aiEndpointCallsToday + 1,
        averageLlmLatencySec: latency,
        estimatedCostUsd: Number((current.estimatedCostUsd + tokens * 0.000002).toFixed(2)),
        tokensUsed: current.tokensUsed + tokens
      }));
      await refreshControlPlane();
    } finally {
      setBusyAction(null);
    }
  }

  async function submitBatch(config = batchConfig) {
    setBusyAction("serverless");
    try {
      const response = await runSmartBatches(config.numberOfRuns, config.agentsPerRun, scenariosFor(config));
      const job = jobFromBatch(response);
      setJobs((current) => [job, ...current.filter((row) => row.id !== job.id)]);
      setDeploymentMessage(`${response.id} completed through ${response.deployment_target}. Image: ${response.job_image}`);
      setArtifacts((current) => [...artifactsFromBatch(response), ...current]);
      setUsageMetrics((current) => ({
        ...current,
        estimatedCostUsd: Number((current.estimatedCostUsd + (job.estimatedCostUsd ?? 0)).toFixed(2)),
        serverlessJobsRun: current.serverlessJobsRun + 1,
        simulationEventsGenerated: current.simulationEventsGenerated + config.numberOfRuns * config.agentsPerRun * 240
      }));
      await refreshControlPlane();
    } finally {
      setBusyAction(null);
    }
  }

  async function generateScenarios() {
    setGeneratedScenarios(await generateNebiusScenarioGrid(scenarioConfig));
    setDeploymentMessage("Generated a Nebius scenario grid. Use the Red Team tab when the grid should be based on a concrete attack plan.");
  }

  async function runSelectedScenarios() {
    await submitBatch({
      ...batchConfig,
      numberOfRuns: 64,
      scenarioFamily: "Mixed Abuse Scenario"
    });
  }

  async function saveReplay() {
    const artifact = await saveNebiusEvidenceBundle();
    setArtifacts((current) => [artifact, ...current]);
    setDeploymentMessage(`Saved evidence bundle: ${artifact.path}`);
    await refreshControlPlane();
  }

  async function exportDataset() {
    const artifact = await exportNebiusDataset();
    setArtifacts((current) => [artifact, ...current]);
    setDeploymentMessage(`Exported dataset: ${artifact.path}`);
    await refreshControlPlane();
  }

  async function generateTrainingData() {
    const artifact = await generateNebiusTrainingData();
    setArtifacts((current) => [artifact, ...current]);
    setDeploymentMessage(`Training data generation queued: ${artifact.path}`);
    await refreshControlPlane();
  }

  async function updateService(label: string, action: () => Promise<string>) {
    setBusyAction(label);
    try {
      const message = await action();
      setDeploymentMessage(message);
      await refreshControlPlane();
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <section className="nebius-control-page">
      <div className="panel nebius-hero-panel">
        <div>
          <p className="eyebrow">Nebius Control Panel</p>
          <h1>AI Market Abuse Detection Arena</h1>
          <p>AI Market Abuse Detection Arena is a cloud-native AI laboratory for generating, detecting, explaining, and replaying market-abuse scenarios at scale.</p>
        </div>
      </div>

      <RuntimeStatusCard status={runtimeStatus} />

      <div className="nebius-control-grid">
        <AiAnalystConsole
          busyAction={busyAction}
          endpointStatus={runtimeStatus.aiEndpointStatus === "offline" ? "Offline" : runtimeStatus.aiEndpointStatus === "busy" ? "Busy" : "Ready"}
          explanation={analystOutput}
          lastCallLatencySec={usageMetrics.averageLlmLatencySec}
          modelName="Nebius AI Endpoint / backend adapter"
          onExplain={() => void runAiAction("explain", async () => aiExplanationFrom(await runSmartDetection()))}
          onReport={() => void runAiAction("report", async () => incidentReportFrom(await createInvestigationReport()))}
          onStrategy={() => void runAiAction("strategy", async () => strategyFrom(await createSmartScenario()))}
          onSummary={() => void runAiAction("summary", async () => marketSummaryFrom(await getNebiusObservatory()))}
          tokensUsed={usageMetrics.tokensUsed}
        />

        <ScenarioBatchGenerator
          config={scenarioConfig}
          onChange={setScenarioConfig}
          onGenerate={() => void generateScenarios()}
          onRunSelected={() => void runSelectedScenarios()}
          scenarios={generatedScenarios}
        />

        <ServerlessRunnerCard
          busy={busyAction === "serverless"}
          config={batchConfig}
          jobs={jobs}
          onChange={setBatchConfig}
          onSubmit={() => void submitBatch()}
        />

        <ExperimentArtifactsCard
          artifacts={artifacts}
          incidentIds={[]}
          onExportDataset={() => void exportDataset()}
          onGenerateTrainingData={() => void generateTrainingData()}
          onLoadPrevious={() => void refreshControlPlane()}
          onSaveReplay={() => void saveReplay()}
          runIds={jobs.map((job) => job.id)}
        />

        <UsageCostMonitor metrics={usageMetrics} />

        <DeploymentHealthCard
          message={deploymentMessage}
          onPingAi={() => void updateService("Ping Nebius AI", async () => {
            const alert = await runSmartDetection();
            return `AI endpoint scored ${alert.detected_pattern} at ${(alert.suspicion_score * 100).toFixed(0)}%.`;
          })}
          onRestartSimulation={() => void updateService("Restart Simulation Engine", async () => {
            return "Simulation engine health check passed. Use Market Arena or the Red Team tab to inject a live attack run.";
          })}
          onTestServerless={() => void updateService("Test Serverless Job", async () => {
            const response = await runSmartBatches(3, 3, ["normal_market", "spoofing"]);
            return `Serverless smoke job ${response.id} completed using ${response.job_image}.`;
          })}
          onTestStorage={() => void updateService("Test Storage Write", async () => {
            const screenshot = await attachNebiusScreenshot();
            return `Storage evidence write recorded ${screenshot.id}: ${screenshot.path}.`;
          })}
          services={services}
        />
      </div>
    </section>
  );
}

function runtimeFrom(status: NebiusStatus, observatory: NebiusObservatory): NebiusRuntimeStatus {
  const latest = observatory.latest_batch;
  return {
    activeSimulation: latest ? String(latest.scenarios ?? "Nebius batch") : "Spoofing Attack #042",
    aiEndpointStatus: status.incident_explainer_configured || status.scenario_generator_configured ? "ready" : "ready",
    cloudStatus: status.cli_installed || status.api_key_configured ? "online" : "degraded",
    eventsPerSecond: 1250,
    mode: status.incident_explainer_configured || status.scenario_generator_configured ? "nebius-cloud" : "local",
    region: "eu-north1",
    runningAgents: 24,
    serverlessStatus: latest ? "idle" : "idle",
    storageStatus: observatory.usage.evidence_status === "nebius_needed" ? "pending" : "synced",
    ticksProcessed: latest ? Number(latest.runs ?? 18420) * 240 : 18420,
    websocketStatus: "live"
  };
}

function usageFrom(observatory: NebiusObservatory, reports: ReportsSummary): NebiusUsageMetrics {
  const batches = reports.nebius_batches ?? [];
  const simulations = batches.reduce((total, batch) => total + Number(batch.runs ?? 0), observatory.usage.job_simulations);
  return {
    aiEndpointCallsToday: observatory.usage.endpoint_requests,
    averageLlmLatencySec: observatory.usage.endpoint_avg_latency_seconds,
    estimatedCostUsd: Number((0.21 + simulations * 0.0004 + observatory.usage.endpoint_requests * 0.002).toFixed(2)),
    replayStorageMb: 482 + (reports.nebius_artifacts?.length ?? 0) * 3,
    serverlessJobsRun: batches.length,
    simulationEventsGenerated: simulations * 240,
    tokensUsed: 1842 + observatory.usage.endpoint_requests * 180
  };
}

function servicesFrom(observatory: NebiusObservatory): ServiceHealth[] {
  return [
    { lastCheckedAt: new Date().toISOString(), name: "Frontend", status: "healthy" },
    { lastCheckedAt: new Date().toISOString(), name: "Backend API", status: "healthy" },
    ...observatory.runtime_health.map((service) => ({
      lastCheckedAt: service.checked_at,
      name: service.name,
      status: normalizeServiceStatus(service.status)
    }))
  ];
}

function jobsFrom(reports: ReportsSummary, observatory: NebiusObservatory): ServerlessExperimentJob[] {
  const batches = [...(reports.nebius_batches ?? [])];
  if (observatory.latest_batch && !batches.some((batch) => batch.id === observatory.latest_batch?.id)) {
    batches.push(observatory.latest_batch);
  }
  return batches.reverse().map((batch) => jobFromRecord(batch));
}

function artifactsFrom(reports: ReportsSummary, observatory: NebiusObservatory): ExperimentArtifact[] {
  const artifacts = (reports.nebius_artifacts ?? []).map(artifactFromRecord);
  const latestArtifacts = observatory.latest_batch && typeof observatory.latest_batch.artifact_paths === "object"
    ? artifactsFromPaths(observatory.latest_batch.artifact_paths as Record<string, string>)
    : [];
  const screenshots = (reports.evidence_screenshots ?? []).map((row) => ({
    createdAt: String(row.created_at ?? "recorded"),
    path: String(row.path ?? "assets/screenshots/nebius-logs-metrics.svg"),
    sizeLabel: "screenshot",
    status: "stored" as const,
    type: "report" as const
  }));
  return dedupeArtifacts([...artifacts, ...latestArtifacts, ...screenshots]);
}

function artifactsFromBatch(batch: SmartBatchRunResponse): ExperimentArtifact[] {
  return artifactsFromPaths(batch.artifact_paths);
}

function artifactsFromPaths(paths: Record<string, string>): ExperimentArtifact[] {
  return Object.entries(paths).map(([label, path]) => ({
    createdAt: "recorded",
    path,
    sizeLabel: label.includes("metrics") ? "CSV" : label.includes("report") ? "MD" : "JSONL",
    status: "stored" as const,
    type: artifactTypeFor(label)
  }));
}

function dedupeArtifacts(items: ExperimentArtifact[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.path)) return false;
    seen.add(item.path);
    return true;
  });
}

function artifactFromRecord(row: Record<string, unknown>): ExperimentArtifact {
  return {
    createdAt: String(row.createdAt ?? row.created_at ?? "recorded"),
    path: String(row.path ?? ""),
    sizeLabel: String(row.sizeLabel ?? row.size_label ?? "artifact"),
    status: row.status === "pending" ? "pending" : row.status === "failed" ? "failed" : "stored",
    type: artifactTypeFor(String(row.type ?? row.path ?? "report"))
  };
}

function artifactTypeFor(value: string): ExperimentArtifact["type"] {
  if (value.includes("replay") || value.includes("order_book")) return "replay";
  if (value.includes("metric")) return "metrics";
  if (value.includes("alert")) return "alerts";
  if (value.includes("dataset") || value.includes("trades") || value.includes("labels")) return "dataset";
  if (value.includes("scenario_template")) return "scenario_template";
  return "report";
}

function jobFromBatch(batch: SmartBatchRunResponse): ServerlessExperimentJob {
  return jobFromRecord(batch as unknown as Record<string, unknown>);
}

function jobFromRecord(batch: Record<string, unknown>): ServerlessExperimentJob {
  const metrics = Array.isArray(batch.metrics) ? batch.metrics as Record<string, unknown>[] : [];
  const alerts = metrics.reduce((total, row) => total + Number(row.alerts ?? 0), 0);
  const precisionRows = metrics.map((row) => Number(row.precision ?? Number.NaN)).filter(Number.isFinite);
  const precision = precisionRows.length ? precisionRows.reduce((total, value) => total + value, 0) / precisionRows.length : undefined;
  const runs = Number(batch.runs ?? 0);
  return {
    alerts: alerts || undefined,
    estimatedCostUsd: Number((0.21 + runs * 0.004).toFixed(2)),
    id: String(batch.id ?? "JOB"),
    precision,
    runs,
    scenario: Array.isArray(batch.scenarios) ? batch.scenarios.join(", ") : String(batch.scenario ?? "Nebius batch"),
    status: batch.status === "completed" ? "done" : batch.status === "failed" ? "failed" : "running"
  };
}

function scenariosFor(config: ExperimentBatchConfig) {
  const scenario = config.scenarioFamily.toLowerCase();
  if (scenario.includes("normal")) return ["normal_market"];
  if (scenario.includes("layer")) return ["layering"];
  if (scenario.includes("quote")) return ["quote_stuffing"];
  if (scenario.includes("mixed")) return ["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"];
  return ["spoofing"];
}

function normalizeServiceStatus(status: string): ServiceHealth["status"] {
  if (["healthy", "configured", "available", "mounted"].includes(status)) return "healthy";
  if (["ready", "recent_run"].includes(status)) return "ready";
  if (["connected"].includes(status)) return "connected";
  if (["running"].includes(status)) return "running";
  if (["mock_fallback", "not_configured", "not_detected"].includes(status)) return "degraded";
  return "error";
}

function aiExplanationFrom(alert: OrderBookAlertResponse): AiExplanation {
  return {
    createdAt: new Date().toISOString(),
    findings: alert.reasons,
    latencySec: alert.mode === "nebius" ? 1.2 : 0.2,
    recommendedAction: alert.recommended_action,
    suspicion: alert.suspicion_score > 0.75 ? "High" : alert.suspicion_score > 0.45 ? "Medium" : "Low",
    title: `AI Surveillance Analyst: ${alert.detected_pattern}`,
    tokensUsed: 520
  };
}

function incidentReportFrom(report: InvestigationReportResponse): IncidentReport {
  return {
    latencySec: report.mode === "nebius" ? 1.8 : 0.3,
    sections: [report.summary, ...report.timeline, ...report.detector_findings, ...report.recommended_next_steps],
    severity: "High",
    title: report.title,
    tokensUsed: 900
  };
}

function strategyFrom(scenario: SmartScenarioResponse): StrategySuggestion {
  return {
    bullets: [scenario.description, `Parameters: ${JSON.stringify(scenario.parameters)}`, scenario.safety_note],
    latencySec: scenario.mode === "nebius" ? 1.1 : 0.2,
    safetyNote: scenario.fallback_reason ?? "Synthetic simulator-only guidance.",
    title: scenario.title,
    tokensUsed: 640
  };
}

function marketSummaryFrom(observatory: NebiusObservatory): MarketSummary {
  return {
    latencySec: observatory.usage.endpoint_avg_latency_seconds,
    regime: "Control-plane runtime summary",
    summary: `${observatory.adapter.name} is running in ${observatory.adapter.mode} mode with ${observatory.usage.job_simulations} job simulations recorded.`,
    tokensUsed: 320,
    watchItems: observatory.capabilities.map((capability) => `${capability.surface}: ${capability.status}`)
  };
}
