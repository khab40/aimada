import { useEffect, useState } from "react";
import {
  attachNebiusScreenshot,
  aggregateManagedExperiment,
  artifactDownloadUrl,
  createInvestigationReport,
  createManagedExperiment,
  createSmartScenario,
  exportNebiusDataset,
  generateNebiusScenarioGrid,
  generateManagedExperimentManifest,
  getManagedExperiment,
  getManagedExperimentLeaderboard,
  getManagedExperimentSummary,
  getManagedExperimentReportUrl,
  generateNebiusTrainingData,
  getNebiusObservatory,
  getNebiusStatus,
  getReportsSummary,
  listManagedExperimentJobs,
  listManagedExperiments,
  collectManagedExperimentNebiusArtifacts,
  refreshManagedExperimentJobs,
  renderManagedExperimentNebiusJobConfig,
  runSmartBatches,
  runSmartDetection,
  runManagedExperimentInvestigations,
  runManagedExperimentLocalBatch,
  saveNebiusEvidenceBundle,
  submitManagedExperimentNebius,
  type ExperimentJobRecord,
  type ExperimentLeaderboardRow,
  type ExperimentSummary,
  type InvestigationReportResponse,
  type ManagedExperiment,
  type ManagedExperimentCreateRequest,
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

type ExperimentFormState = Required<Pick<ManagedExperimentCreateRequest, "name" | "attack_count" | "batch_size" | "scenarios" | "seed">>;
type ExperimentAction =
  | "create-experiment"
  | "generate-manifest"
  | "run-local-batch"
  | "submit-nebius"
  | "refresh-job-status"
  | "collect-cloud-artifacts"
  | "render-job-config"
  | "test-endpoint-health"
  | "test-orderbook-alert"
  | "test-investigation-report"
  | "aggregate"
  | "run-investigations";

const experimentScenarioOptions = [
  "normal_market",
  "spoofing",
  "layering",
  "quote_stuffing",
  "pump_and_cancel"
];

const initialExperimentForm: ExperimentFormState = {
  attack_count: 100,
  batch_size: 20,
  name: "AI-MADA detector benchmark",
  scenarios: ["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"],
  seed: 42
};

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
  const [experiment, setExperiment] = useState<ManagedExperiment | null>(null);
  const [experimentForm, setExperimentForm] = useState<ExperimentFormState>(initialExperimentForm);
  const [experimentJobs, setExperimentJobs] = useState<ExperimentJobRecord[]>([]);
  const [experimentLeaderboard, setExperimentLeaderboard] = useState<ExperimentLeaderboardRow[]>([]);
  const [experimentSummary, setExperimentSummary] = useState<ExperimentSummary | null>(null);
  const [experimentMessage, setExperimentMessage] = useState<string | null>(null);
  const [experimentBusyAction, setExperimentBusyAction] = useState<ExperimentAction | null>(null);
  const [nebiusStatus, setNebiusStatus] = useState<NebiusStatus | null>(null);
  const [nebiusObservatory, setNebiusObservatory] = useState<NebiusObservatory | null>(null);
  const [deploymentPanelMessage, setDeploymentPanelMessage] = useState<string | null>(null);

  useEffect(() => {
    void refreshControlPlane();
    void refreshExperimentLab();
    void generateNebiusScenarioGrid(initialScenarioConfig).then(setGeneratedScenarios);
    // Initial control-plane hydration only; user-triggered refreshes keep this page current.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshControlPlane() {
    try {
      const [status, observatory, reports] = await Promise.all([
        getNebiusStatus(),
        getNebiusObservatory(),
        getReportsSummary()
      ]);
      setNebiusStatus(status);
      setNebiusObservatory(observatory);
      setRuntimeStatus(runtimeFrom(status, observatory));
      setUsageMetrics(usageFrom(observatory, reports));
      setServices(servicesFrom(observatory));
      setJobs(jobsFrom(reports, observatory));
      setArtifacts(artifactsFrom(reports, observatory));
    } catch (error) {
      setDeploymentMessage(error instanceof Error ? error.message : "Control plane refresh failed.");
    }
  }

  async function refreshExperimentLab(experimentId?: string) {
    try {
      const targetId = experimentId ?? experiment?.id;
      if (!targetId) {
        const experiments = await listManagedExperiments();
        const latest = latestExperiment(experiments);
        if (!latest) return;
        setExperiment(latest);
        await refreshExperimentDetails(latest.id);
        return;
      }
      await refreshExperimentDetails(targetId);
    } catch (error) {
      setExperimentMessage(error instanceof Error ? error.message : "Experiment Lab refresh failed.");
    }
  }

  async function refreshExperimentDetails(experimentId: string) {
    const [latest, jobs] = await Promise.all([
      getManagedExperiment(experimentId),
      listManagedExperimentJobs(experimentId).catch(() => [])
    ]);
    setExperiment(latest);
    setExperimentJobs(jobs);

    const [summary, leaderboard] = await Promise.all([
      getManagedExperimentSummary(experimentId).catch(() => null),
      getManagedExperimentLeaderboard(experimentId).catch(() => [])
    ]);
    setExperimentSummary(summary);
    setExperimentLeaderboard(leaderboard);
  }

  async function runExperimentAction(action: ExperimentAction, fn: () => Promise<void>) {
    setExperimentBusyAction(action);
    setExperimentMessage(null);
    try {
      await fn();
      await refreshControlPlane();
    } catch (error) {
      setExperimentMessage(error instanceof Error ? error.message : "Experiment action failed.");
    } finally {
      setExperimentBusyAction(null);
    }
  }

  function updateExperimentForm<K extends keyof ExperimentFormState>(key: K, value: ExperimentFormState[K]) {
    setExperimentForm((current) => ({
      ...current,
      [key]: value
    }));
  }

  function toggleExperimentScenario(scenario: string) {
    setExperimentForm((current) => {
      const next = current.scenarios.includes(scenario)
        ? current.scenarios.filter((item) => item !== scenario)
        : [...current.scenarios, scenario];
      return {
        ...current,
        scenarios: next.length ? next : [scenario]
      };
    });
  }

  async function createExperimentFromForm() {
    await runExperimentAction("create-experiment", async () => {
      const created = await createManagedExperiment({
        attack_count: Math.max(1, experimentForm.attack_count),
        batch_size: Math.max(1, experimentForm.batch_size),
        name: experimentForm.name.trim() || "AI-MADA experiment",
        scenarios: experimentForm.scenarios,
        seed: experimentForm.seed
      });
      setExperiment(created);
      setExperimentJobs([]);
      setExperimentLeaderboard([]);
      setExperimentSummary(null);
      setExperimentMessage(`Created experiment ${created.id}.`);
      await refreshExperimentDetails(created.id);
    });
  }

  async function generateExperimentManifest() {
    if (!experiment) return;
    await runExperimentAction("generate-manifest", async () => {
      const manifest = await generateManagedExperimentManifest(experiment.id);
      setExperimentMessage(`Generated ${manifest.attack_count} attack rows at ${manifest.path}.`);
      await refreshExperimentDetails(experiment.id);
    });
  }

  async function runExperimentLocalBatch() {
    if (!experiment) return;
    await runExperimentAction("run-local-batch", async () => {
      const batch = await runManagedExperimentLocalBatch(experiment.id);
      setExperimentMessage(`${batch.status === "completed" ? "Completed" : "Failed"} local batch in ${batch.elapsed_seconds.toFixed(1)}s.`);
      await refreshExperimentDetails(experiment.id);
    });
  }

  async function submitExperimentToNebius() {
    if (!experiment) return;
    await runExperimentAction("submit-nebius", async () => {
      const job = await submitManagedExperimentNebius(experiment.id);
      setExperimentMessage(job.status === "real_nebius_pending" ? "pending real Nebius execution" : job.message);
      await refreshExperimentDetails(experiment.id);
    });
  }

  async function renderExperimentJobConfig() {
    if (!experiment) return;
    await runExperimentAction("render-job-config", async () => {
      const rendered = await renderManagedExperimentNebiusJobConfig(experiment.id);
      setDeploymentPanelMessage(`Rendered job config: ${rendered.path}`);
      await refreshExperimentDetails(experiment.id);
    });
  }

  async function refreshExperimentJobStatus() {
    if (!experiment) return;
    await runExperimentAction("refresh-job-status", async () => {
      const refreshed = await refreshManagedExperimentJobs(experiment.id);
      setExperimentJobs(refreshed);
      const latest = latestExperimentJob(refreshed);
      setDeploymentPanelMessage(latest ? `Latest cloud job status: ${latest.status.replaceAll("_", " ")}` : "No job records yet.");
      await refreshExperimentDetails(experiment.id);
    });
  }

  async function collectExperimentCloudArtifacts() {
    if (!experiment) return;
    await runExperimentAction("collect-cloud-artifacts", async () => {
      const result = await collectManagedExperimentNebiusArtifacts(experiment.id);
      setDeploymentPanelMessage(result.status === "collected" ? `Collected ${result.copied_count} cloud artifacts.` : result.message);
      await refreshExperimentDetails(experiment.id);
    });
  }

  async function testEndpointHealth() {
    await runExperimentAction("test-endpoint-health", async () => {
      const status = await getNebiusStatus();
      setNebiusStatus(status);
      setDeploymentPanelMessage(`Endpoint health: ${healthStatusLabel(status.endpoint_health)}.`);
    });
  }

  async function testOrderbookAlert() {
    await runExperimentAction("test-orderbook-alert", async () => {
      const alert = await runSmartDetection();
      setDeploymentPanelMessage(`Orderbook alert returned ${alert.mode}: ${alert.detected_pattern} (${(alert.confidence * 100).toFixed(0)}%).`);
    });
  }

  async function testInvestigationReport() {
    await runExperimentAction("test-investigation-report", async () => {
      const report = await createInvestigationReport();
      setDeploymentPanelMessage(`Investigation report returned ${report.mode}: ${report.title}.`);
    });
  }

  async function aggregateExperimentResults() {
    if (!experiment) return;
    await runExperimentAction("aggregate", async () => {
      const result = await aggregateManagedExperiment(experiment.id);
      setExperimentSummary(result.summary);
      setExperimentLeaderboard(result.leaderboard);
      setExperimentMessage(`Aggregated ${result.summary.total_alerts} alerts into ${result.leaderboard.length} leaderboard rows.`);
      await refreshExperimentDetails(experiment.id);
    });
  }

  async function runExperimentInvestigations() {
    if (!experiment) return;
    await runExperimentAction("run-investigations", async () => {
      const result = await runManagedExperimentInvestigations(experiment.id);
      setExperimentMessage(`Ran ${result.investigation_count} AI investigations in ${result.investigation_mode} mode.`);
      await refreshExperimentDetails(experiment.id);
    });
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

      <ExperimentLab
        busyAction={experimentBusyAction}
        experiment={experiment}
        form={experimentForm}
        jobs={experimentJobs}
        leaderboard={experimentLeaderboard}
        message={experimentMessage}
        onAggregate={() => void aggregateExperimentResults()}
        onCreate={() => void createExperimentFromForm()}
        onGenerateManifest={() => void generateExperimentManifest()}
        onRefresh={() => void refreshExperimentLab()}
        onRunInvestigations={() => void runExperimentInvestigations()}
        onRunLocalBatch={() => void runExperimentLocalBatch()}
        onSubmitNebius={() => void submitExperimentToNebius()}
        onToggleScenario={toggleExperimentScenario}
        onUpdateForm={updateExperimentForm}
        summary={experimentSummary}
      />

      <RealNebiusDeploymentPanel
        busyAction={experimentBusyAction}
        experiment={experiment}
        jobs={experimentJobs}
        message={deploymentPanelMessage}
        observatory={nebiusObservatory}
        onCollectArtifacts={() => void collectExperimentCloudArtifacts()}
        onRefreshJobStatus={() => void refreshExperimentJobStatus()}
        onRenderJobConfig={() => void renderExperimentJobConfig()}
        onSubmitNebius={() => void submitExperimentToNebius()}
        onTestEndpointHealth={() => void testEndpointHealth()}
        onTestInvestigationReport={() => void testInvestigationReport()}
        onTestOrderbookAlert={() => void testOrderbookAlert()}
        status={nebiusStatus}
      />

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
  const endpointConfigured = status.incident_explainer_configured
    || status.scenario_generator_configured
    || status.orderbook_alert_configured
    || status.investigation_report_configured;
  return {
    activeSimulation: latest ? String(latest.scenarios ?? "Nebius batch") : "Spoofing Attack #042",
    aiEndpointStatus: endpointConfigured ? "ready" : "ready",
    cloudStatus: status.cli_installed || status.api_key_configured ? "online" : "degraded",
    eventsPerSecond: 1250,
    mode: endpointConfigured ? "nebius-cloud" : "local",
    region: "eu-north1",
    runningAgents: 24,
    serverlessStatus: latest ? "idle" : "idle",
    storageStatus: observatory.usage.evidence_status === "nebius_needed" ? "pending" : "synced",
    ticksProcessed: latest ? Number(latest.runs ?? 18420) * 240 : 18420,
    websocketStatus: "live"
  };
}

function ExperimentLab({
  busyAction,
  experiment,
  form,
  jobs,
  leaderboard,
  message,
  onAggregate,
  onCreate,
  onGenerateManifest,
  onRefresh,
  onRunInvestigations,
  onRunLocalBatch,
  onSubmitNebius,
  onToggleScenario,
  onUpdateForm,
  summary
}: {
  busyAction: ExperimentAction | null;
  experiment: ManagedExperiment | null;
  form: ExperimentFormState;
  jobs: ExperimentJobRecord[];
  leaderboard: ExperimentLeaderboardRow[];
  message: string | null;
  onAggregate: () => void;
  onCreate: () => void;
  onGenerateManifest: () => void;
  onRefresh: () => void;
  onRunInvestigations: () => void;
  onRunLocalBatch: () => void;
  onSubmitNebius: () => void;
  onToggleScenario: (scenario: string) => void;
  onUpdateForm: <K extends keyof ExperimentFormState>(key: K, value: ExperimentFormState[K]) => void;
  summary: ExperimentSummary | null;
}) {
  const canRun = Boolean(experiment);
  const artifacts = experiment ? experimentArtifactsFrom(experiment, summary) : [];
  const pendingNebiusJob = jobs.find((job) => job.status === "real_nebius_pending");

  return (
    <section className="panel experiment-lab-panel">
      <div className="nebius-card-heading">
        <div>
          <p className="eyebrow">Experiment Lab</p>
          <h2>Experiment Lab</h2>
        </div>
        <div className="nebius-button-row">
          <span className={`runtime-status ${experiment?.status ?? "missing"}`}>{experiment?.status.replaceAll("_", " ") ?? "no experiment"}</span>
          <button className="secondary-button" onClick={onRefresh} type="button">Refresh</button>
        </div>
      </div>

      <div className="experiment-lab-layout">
        <div className="experiment-form-card">
          <label>
            <span>Name</span>
            <input
              onChange={(event) => onUpdateForm("name", event.target.value)}
              value={form.name}
            />
          </label>
          <div className="experiment-number-grid">
            <label>
              <span>Attack count</span>
              <input
                min={1}
                onChange={(event) => onUpdateForm("attack_count", Number(event.target.value))}
                type="number"
                value={form.attack_count}
              />
            </label>
            <label>
              <span>Batch size</span>
              <input
                min={1}
                onChange={(event) => onUpdateForm("batch_size", Number(event.target.value))}
                type="number"
                value={form.batch_size}
              />
            </label>
            <label>
              <span>Seed</span>
              <input
                onChange={(event) => onUpdateForm("seed", Number(event.target.value))}
                type="number"
                value={form.seed}
              />
            </label>
          </div>
          <div className="experiment-scenario-picker" aria-label="Experiment scenarios">
            {experimentScenarioOptions.map((scenario) => (
              <button
                className={form.scenarios.includes(scenario) ? "scenario-pill selected" : "scenario-pill"}
                key={scenario}
                onClick={() => onToggleScenario(scenario)}
                type="button"
              >
                {scenario.replaceAll("_", " ")}
              </button>
            ))}
          </div>
          <button
            className="primary-button"
            disabled={busyAction === "create-experiment"}
            onClick={onCreate}
            type="button"
          >
            {busyAction === "create-experiment" ? "Creating..." : "Create experiment"}
          </button>
        </div>

        <div className="experiment-progress-card">
          <div className="experiment-active-summary">
            <span>Current experiment</span>
            <strong>{experiment?.name ?? "Create or refresh an experiment"}</strong>
            <p>{experiment ? `${experiment.id} · ${experiment.attack_count} attacks · batch ${experiment.batch_size}` : "The managed experiment flow runs through FastAPI and keeps Nebius calls behind the backend boundary."}</p>
          </div>
          <div className="experiment-flow-actions">
            <button disabled={!canRun || busyAction === "generate-manifest"} onClick={onGenerateManifest} type="button">Generate manifest</button>
            <button disabled={!canRun || busyAction === "run-local-batch"} onClick={onRunLocalBatch} type="button">Run local batch</button>
            <button disabled={!canRun || busyAction === "submit-nebius"} onClick={onSubmitNebius} type="button">Submit to Nebius</button>
            <button disabled={!canRun || busyAction === "aggregate"} onClick={onAggregate} type="button">Aggregate</button>
            <button disabled={!canRun || busyAction === "run-investigations"} onClick={onRunInvestigations} type="button">Run AI investigations</button>
          </div>
          {message ? <p className="experiment-message">{message}</p> : null}
          {pendingNebiusJob ? <p className="experiment-pending-note">pending real Nebius execution: {pendingNebiusJob.message}</p> : null}
          <ExperimentProgressSummary experiment={experiment} summary={summary} jobs={jobs} />
        </div>
      </div>

      <div className="experiment-output-grid">
        <ExperimentJobsTable jobs={jobs} />
        <ExperimentArtifactLinks artifacts={artifacts} experimentId={experiment?.id} />
        <ExperimentLeaderboardTable leaderboard={leaderboard} />
      </div>
    </section>
  );
}

function RealNebiusDeploymentPanel({
  busyAction,
  experiment,
  jobs,
  message,
  observatory,
  onCollectArtifacts,
  onRefreshJobStatus,
  onRenderJobConfig,
  onSubmitNebius,
  onTestEndpointHealth,
  onTestInvestigationReport,
  onTestOrderbookAlert,
  status
}: {
  busyAction: ExperimentAction | null;
  experiment: ManagedExperiment | null;
  jobs: ExperimentJobRecord[];
  message: string | null;
  observatory: NebiusObservatory | null;
  onCollectArtifacts: () => void;
  onRefreshJobStatus: () => void;
  onRenderJobConfig: () => void;
  onSubmitNebius: () => void;
  onTestEndpointHealth: () => void;
  onTestInvestigationReport: () => void;
  onTestOrderbookAlert: () => void;
  status: NebiusStatus | null;
}) {
  const cloudJob = latestExperimentJob(jobs.filter((job) => job.backend === "nebius_serverless_job"));
  const endpointHealth = status?.endpoint_health ?? observatory?.endpoint_health ?? null;
  const endpointMode = status?.endpoint_mode ?? observatory?.endpoint_mode ?? "mock";
  const hasExperiment = Boolean(experiment);

  return (
    <section className="panel experiment-lab-panel real-nebius-deployment-panel">
      <div className="nebius-card-heading">
        <div>
          <p className="eyebrow">Real Nebius Deployment</p>
          <h2>Real Nebius Deployment</h2>
        </div>
        <span className={`runtime-status ${cloudJob?.status ?? "missing"}`}>
          {cloudJob?.status.replaceAll("_", " ") ?? "no cloud job"}
        </span>
      </div>

      <div className="experiment-summary-grid real-nebius-summary-grid">
        <MetricBlock label="Endpoint base URL" value={status?.endpoint_base_url || "not configured"} />
        <MetricBlock label="Endpoint health" value={healthStatusLabel(endpointHealth)} />
        <MetricBlock label="Endpoint mode" value={endpointMode} />
        <MetricBlock label="Model" value={status?.model || "not configured"} />
        <MetricBlock label="Job image" value={status?.job_image || "not configured"} />
        <MetricBlock
          label="Rendered config"
          value={experiment?.artifact_paths.nebius_job_config ?? "not rendered"}
        />
        <MetricBlock
          label="Submit template"
          value={status?.job_submit_template_configured ? "yes" : "no"}
        />
        <MetricBlock
          label="Latest cloud job"
          value={cloudJob ? `${cloudJob.status.replaceAll("_", " ")} · ${cloudJob.job_id}` : "no cloud job"}
        />
        <MetricBlock label="Artifact collection" value={artifactCollectionStatus(experiment)} />
      </div>

      <div className="nebius-button-row">
        <button
          className="secondary-button"
          disabled={busyAction === "test-endpoint-health"}
          onClick={onTestEndpointHealth}
          type="button"
        >
          Test endpoint health
        </button>
        <button
          className="secondary-button"
          disabled={busyAction === "test-orderbook-alert"}
          onClick={onTestOrderbookAlert}
          type="button"
        >
          Test orderbook-alert
        </button>
        <button
          className="secondary-button"
          disabled={busyAction === "test-investigation-report"}
          onClick={onTestInvestigationReport}
          type="button"
        >
          Test investigation-report
        </button>
        <button
          className="secondary-button"
          disabled={!hasExperiment || busyAction === "render-job-config"}
          onClick={onRenderJobConfig}
          type="button"
        >
          Render job config
        </button>
        <button
          className="secondary-button"
          disabled={!hasExperiment || busyAction === "submit-nebius"}
          onClick={onSubmitNebius}
          type="button"
        >
          Submit real Nebius job
        </button>
        <button
          className="secondary-button"
          disabled={!hasExperiment || busyAction === "refresh-job-status"}
          onClick={onRefreshJobStatus}
          type="button"
        >
          Refresh job status
        </button>
        <button
          className="secondary-button"
          disabled={!hasExperiment || busyAction === "collect-cloud-artifacts"}
          onClick={onCollectArtifacts}
          type="button"
        >
          Collect cloud artifacts
        </button>
      </div>

      {status?.job_submit_template_configured ? null : (
        <p className="experiment-pending-note">
          Real job submit template is not configured. Submitting records pending real Nebius execution instead of fake cloud success.
        </p>
      )}
      {cloudJob?.message ? <p className="experiment-message">{cloudJob.message}</p> : null}
      {message ? <p className="experiment-message">{message}</p> : null}
    </section>
  );
}

function ExperimentProgressSummary({
  experiment,
  jobs,
  summary
}: {
  experiment: ManagedExperiment | null;
  jobs: ExperimentJobRecord[];
  summary: ExperimentSummary | null;
}) {
  const completedJobs = jobs.filter((job) => job.status === "completed").length;
  const failedJobs = jobs.filter((job) => job.status === "failed").length;
  return (
    <div className="experiment-summary-grid">
      <MetricBlock label="Status" value={experiment?.status.replaceAll("_", " ") ?? "draft"} />
      <MetricBlock label="Jobs" value={`${completedJobs}/${jobs.length} done`} />
      <MetricBlock label="Alerts" value={summary ? String(summary.total_alerts) : "not aggregated"} />
      <MetricBlock label="Failed runs" value={String(summary?.failed_runs ?? failedJobs)} />
      <MetricBlock label="Investigations" value={String(summary?.investigation_count ?? metricValue(experiment, "investigation_count") ?? 0)} />
    </div>
  );
}

function MetricBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="runtime-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ExperimentJobsTable({ jobs }: { jobs: ExperimentJobRecord[] }) {
  return (
    <div className="nebius-result-block experiment-jobs-block">
      <span>Job records</span>
      {jobs.length ? (
        <div className="benchmark-table-panel">
          <table className="benchmark-table compact-job-table">
            <thead>
              <tr>
                <th>Job</th>
                <th>Backend</th>
                <th>Status</th>
                <th>Attacks</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.job_id}>
                  <td>{job.job_id}</td>
                  <td>{job.backend.replaceAll("_", " ")}</td>
                  <td>{job.status.replaceAll("_", " ")}</td>
                  <td>{job.attack_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>No jobs recorded yet.</p>
      )}
    </div>
  );
}

function ExperimentArtifactLinks({
  artifacts,
  experimentId
}: {
  artifacts: Array<[string, string]>;
  experimentId?: string;
}) {
  return (
    <div className="nebius-result-block experiment-artifacts-block">
      <span>Artifact links</span>
      {artifacts.length ? (
        <div className="experiment-artifact-list">
          {artifacts.map(([label, path]) => (
            <a href={artifactDownloadUrl(path)} key={`${label}-${path}`} target="_blank" rel="noreferrer">
              {label.replaceAll("_", " ")}
            </a>
          ))}
          {experimentId ? (
            <a href={getManagedExperimentReportUrl(experimentId)} target="_blank" rel="noreferrer">
              benchmark report
            </a>
          ) : null}
        </div>
      ) : (
        <p>Artifacts appear after manifest generation, local batch execution, normalization, aggregation, or investigations.</p>
      )}
    </div>
  );
}

function ExperimentLeaderboardTable({ leaderboard }: { leaderboard: ExperimentLeaderboardRow[] }) {
  return (
    <div className="nebius-result-block experiment-leaderboard-block">
      <span>Detector leaderboard</span>
      {leaderboard.length ? (
        <div className="benchmark-table-panel">
          <table className="benchmark-table compact-job-table">
            <thead>
              <tr>
                <th>Scenario</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1</th>
                <th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((row) => (
                <tr key={row.scenario}>
                  <td>{row.scenario.replaceAll("_", " ")}</td>
                  <td>{formatScore(row.precision)}</td>
                  <td>{formatScore(row.recall)}</td>
                  <td>{formatScore(row.f1)}</td>
                  <td>{row.avg_detection_latency_ms == null ? "n/a" : `${row.avg_detection_latency_ms.toFixed(0)} ms`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>Aggregate the experiment to populate detector rankings.</p>
      )}
    </div>
  );
}

function experimentArtifactsFrom(experiment: ManagedExperiment, summary: ExperimentSummary | null): Array<[string, string]> {
  const entries = Object.entries({
    ...experiment.artifact_paths,
    ...(summary?.artifact_paths ?? {})
  }).filter(([, path]) => typeof path === "string" && path.includes("."));
  const seen = new Set<string>();
  return entries.filter(([, path]) => {
    if (seen.has(path)) return false;
    seen.add(path);
    return true;
  });
}

function metricValue(experiment: ManagedExperiment | null, key: string): number | null {
  if (!experiment) return null;
  for (const row of experiment.metrics) {
    const value = row[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return null;
}

function formatScore(value: number) {
  return Number.isFinite(value) ? value.toFixed(3) : "n/a";
}

function latestExperiment(experiments: ManagedExperiment[]) {
  return [...experiments].sort((left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at))[0] ?? null;
}

function latestExperimentJob(jobs: ExperimentJobRecord[]) {
  return [...jobs].sort((left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at))[0] ?? null;
}

function healthStatusLabel(health: Record<string, unknown> | null | undefined) {
  if (!health) return "not checked";
  const status = health.status;
  if (typeof status === "string" && status.trim()) return status.replaceAll("_", " ");
  return "available";
}

function artifactCollectionStatus(experiment: ManagedExperiment | null) {
  if (!experiment) return "no experiment";
  if (experiment.status === "cloud_artifacts_pending") return "cloud artifacts pending";
  if (experiment.artifact_paths.artifact_index) return "collected";
  return "not collected";
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
