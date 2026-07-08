import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  aggregateManagedExperiment,
  artifactDownloadUrl,
  createManagedExperiment,
  generateMarketAbuseScenario,
  generateManagedExperimentManifest,
  getManagedExperiment,
  getManagedExperimentLeaderboard,
  getManagedExperimentSummary,
  getManagedExperimentReportUrl,
  getNebiusObservatory,
  getNebiusStatus,
  getReportsSummary,
  getDetectorTournament,
  injectNebiusAttackScenario,
  listManagedExperimentJobs,
  listManagedExperiments,
  collectManagedExperimentNebiusArtifacts,
  refreshManagedExperimentJobs,
  renderManagedExperimentNebiusJobConfig,
  runAIInvestigationTeam,
  runManagedExperimentInvestigations,
  runServerlessSmokeDemo,
  runManagedExperimentLocalBatch,
  startDetectorTournament,
  submitManagedExperimentNebius,
  type AIInvestigationTeamResponse,
  type DetectorTournamentResponse,
  type DetectorTournamentStartRequest,
  type ExperimentJobRecord,
  type ExperimentLeaderboardRow,
  type ExperimentSummary,
  type MarketAbuseScenarioGenerationRequest,
  type MarketAbuseScenarioResponse,
  type ManagedExperiment,
  type ManagedExperimentCreateRequest,
  type NebiusObservatory,
  type NebiusStatus,
  type ReportsSummary,
  type ServerlessSmokeResponse
} from "@/api/client";
import { RuntimeStatusCard } from "@/features/nebius/components/RuntimeStatusCard";
import { UsageCostMonitor } from "@/features/nebius/components/UsageCostMonitor";
import type {
  ExperimentArtifact,
  NebiusRuntimeStatus,
  NebiusUsageMetrics
} from "@/features/nebius/types";
import {
  getStoredRuntimeMode,
  RUNTIME_MODE_EVENT,
  storeRuntimeMode,
  visibleRuntimeOptions,
  type RuntimeMode
} from "@/runtimeModes";

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

type ExperimentFormState = Required<Pick<ManagedExperimentCreateRequest, "name" | "attack_count" | "batch_size" | "scenarios" | "seed">>;
type DemoScenario = {
  attackKey: string;
  cta?: string;
  demonstrates: string[];
  duration?: string;
  id: string;
  purpose?: string;
  runtime: RuntimeMode;
  title: string;
};
type ExperimentAction =
  | "create-experiment"
  | "generate-ai-scenario"
  | "generate-manifest"
  | "run-local-batch"
  | "submit-nebius"
  | "refresh-job-status"
  | "collect-cloud-artifacts"
  | "run-serverless-smoke"
  | "render-job-config"
  | "test-endpoint-health"
  | "aggregate"
  | "run-investigations"
  | "run-investigation-team"
  | "run-ai-tournament"
  | "replay-ai-scenario";

const TOURNAMENT_POLL_INTERVAL_MS = 1000;
const TOURNAMENT_POLL_ATTEMPTS = 12;

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

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
  name: "AI-MADA detector tournament",
  scenarios: ["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"],
  seed: 42
};

const initialScenarioForm: MarketAbuseScenarioGenerationRequest = {
  difficulty: "medium",
  duration_ticks: 120,
  liquidity_regime: "thin",
  manipulation_type: "spoofing",
  seed: 42,
  symbol: "AIMD",
  volatility_regime: "high"
};

const initialTournamentForm: DetectorTournamentStartRequest = {
  detector_set: ["spoofing_like", "layering_like", "quote_stuffing"],
  difficulty_mix: { adversarial: 0.1, easy: 0.2, hard: 0.2, medium: 0.5 },
  execution_mode: "local_mock",
  manipulation_types: ["spoofing", "layering", "quote_stuffing"],
  number_of_scenarios: 100,
  random_seed: 42
};

const demoScenarios: DemoScenario[] = [
  {
    attackKey: "spoofing",
    cta: "Start",
    demonstrates: ["attack generation", "detection", "mock AI investigation", "simulated execution trace"],
    duration: "30 seconds",
    id: "local-lightweight",
    runtime: "local-demo",
    title: "Local Lightweight Demo"
  },
  {
    attackKey: "layering",
    demonstrates: ["fast classifier", "reasoning model", "simulated latency", "simulated cost"],
    id: "local-ai-pipeline",
    purpose: "Show AI architecture even offline.",
    runtime: "local-demo",
    title: "Local AI Pipeline Demo"
  },
  {
    attackKey: "quote_stuffing",
    demonstrates: ["real endpoint", "streaming explanation", "latency", "tokens", "cost"],
    id: "nebius-endpoint",
    runtime: "nebius-cloud",
    title: "Endpoint Demo"
  },
  {
    attackKey: "wash_trading",
    demonstrates: ["complete platform", "endpoint", "jobs", "benchmark", "artifacts", "execution trace"],
    id: "nebius-platform",
    runtime: "nebius-cloud",
    title: "Full Platform Demo"
  }
];

export function NebiusControlPanelPage() {
  const navigate = useNavigate();
  const [artifacts, setArtifacts] = useState<ExperimentArtifact[]>([]);
  const [runtimeStatus, setRuntimeStatus] = useState<NebiusRuntimeStatus>(fallbackRuntimeStatus);
  const [usageMetrics, setUsageMetrics] = useState<NebiusUsageMetrics>(fallbackUsageMetrics);
  const [experiment, setExperiment] = useState<ManagedExperiment | null>(null);
  const [experimentForm, setExperimentForm] = useState<ExperimentFormState>(initialExperimentForm);
  const [experimentJobs, setExperimentJobs] = useState<ExperimentJobRecord[]>([]);
  const [experimentLeaderboard, setExperimentLeaderboard] = useState<ExperimentLeaderboardRow[]>([]);
  const [experimentSummary, setExperimentSummary] = useState<ExperimentSummary | null>(null);
  const [scenarioForm, setScenarioForm] = useState<MarketAbuseScenarioGenerationRequest>(initialScenarioForm);
  const [generatedScenario, setGeneratedScenario] = useState<MarketAbuseScenarioResponse | null>(null);
  const [scenarioMessage, setScenarioMessage] = useState<string | null>(null);
  const [tournamentForm, setTournamentForm] = useState<DetectorTournamentStartRequest>(initialTournamentForm);
  const [detectorTournament, setDetectorTournament] = useState<DetectorTournamentResponse | null>(null);
  const [serverlessSmokeResult, setServerlessSmokeResult] = useState<ServerlessSmokeResponse | null>(null);
  const [tournamentMessage, setTournamentMessage] = useState<string | null>(null);
  const [investigationTeamReport, setInvestigationTeamReport] = useState<AIInvestigationTeamResponse | null>(null);
  const [experimentMessage, setExperimentMessage] = useState<string | null>(null);
  const [experimentBusyAction, setExperimentBusyAction] = useState<ExperimentAction | null>(null);
  const [nebiusStatus, setNebiusStatus] = useState<NebiusStatus | null>(null);
  const [nebiusObservatory, setNebiusObservatory] = useState<NebiusObservatory | null>(null);
  const [deploymentPanelMessage, setDeploymentPanelMessage] = useState<string | null>(null);
  const [runtimeMode, setRuntimeMode] = useState<RuntimeMode>(() => getStoredRuntimeMode());
  const [activeWorkflowStep, setActiveWorkflowStep] = useState(1);

  useEffect(() => {
    void refreshControlPlane();
    void refreshExperimentLab();
    // Initial control-plane hydration only; user-triggered refreshes keep this page current.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    function syncRuntimeMode(event: Event) {
      const next = event instanceof CustomEvent && typeof event.detail === "string"
        ? event.detail
        : getStoredRuntimeMode();
      if (next === "local-demo" || next === "hybrid" || next === "nebius-cloud") {
        setRuntimeMode(next);
      }
    }
    window.addEventListener(RUNTIME_MODE_EVENT, syncRuntimeMode);
    window.addEventListener("storage", syncRuntimeMode);
    return () => {
      window.removeEventListener(RUNTIME_MODE_EVENT, syncRuntimeMode);
      window.removeEventListener("storage", syncRuntimeMode);
    };
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
      setArtifacts(artifactsFrom(reports, observatory));
    } catch (error) {
      setDeploymentPanelMessage(error instanceof Error ? error.message : "Control plane refresh failed.");
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
      setExperimentMessage(error instanceof Error ? error.message : "Benchmark refresh failed.");
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

  async function runExperimentAction(action: ExperimentAction, fn: () => Promise<void>, onError?: (message: string) => void) {
    setExperimentBusyAction(action);
    setExperimentMessage(null);
    try {
      await fn();
      await refreshControlPlane();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Benchmark action failed.";
      setExperimentMessage(message);
      onError?.(message);
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

  function updateScenarioForm<K extends keyof MarketAbuseScenarioGenerationRequest>(
    key: K,
    value: MarketAbuseScenarioGenerationRequest[K]
  ) {
    setScenarioForm((current) => ({
      ...current,
      [key]: value
    }));
  }

  function updateTournamentForm<K extends keyof DetectorTournamentStartRequest>(
    key: K,
    value: DetectorTournamentStartRequest[K]
  ) {
    setTournamentForm((current) => ({
      ...current,
      [key]: value
    }));
  }

  function toggleTournamentManipulation(value: DetectorTournamentStartRequest["manipulation_types"][number]) {
    setTournamentForm((current) => {
      const selected = current.manipulation_types.includes(value)
        ? current.manipulation_types.filter((item) => item !== value)
        : [...current.manipulation_types, value];
      return { ...current, manipulation_types: selected.length ? selected : [value] };
    });
  }

  function toggleTournamentDetector(value: DetectorTournamentStartRequest["detector_set"][number]) {
    setTournamentForm((current) => {
      const selected = current.detector_set.includes(value)
        ? current.detector_set.filter((item) => item !== value)
        : [...current.detector_set, value];
      return { ...current, detector_set: selected.length ? selected : [value] };
    });
  }

  async function createExperimentFromForm() {
    await runExperimentAction("create-experiment", async () => {
      const created = await createManagedExperiment({
        attack_count: Math.max(1, experimentForm.attack_count),
        batch_size: Math.max(1, experimentForm.batch_size),
        name: experimentForm.name.trim() || "AI-MADA benchmark",
        scenarios: experimentForm.scenarios,
        seed: experimentForm.seed
      });
      setExperiment(created);
      setExperimentJobs([]);
      setExperimentLeaderboard([]);
      setExperimentSummary(null);
      setExperimentMessage(`Created benchmark ${created.id}.`);
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
      setExperimentMessage(job.status === "real_nebius_pending" ? "pending cloud job execution" : job.message);
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
          setExperimentMessage(`Produced ${result.investigation_count} Nebius AI Investigation summaries in ${result.investigation_mode} mode.`);
      await refreshExperimentDetails(experiment.id);
    });
  }

  async function runInvestigationTeam() {
    await runExperimentAction("run-investigation-team", async () => {
      const report = await runAIInvestigationTeam();
      setInvestigationTeamReport(report);
      setExperimentMessage(`Nebius AI Investigation Team consensus: ${report.consensus}`);
    });
  }

  async function generateAiScenario() {
    await runExperimentAction("generate-ai-scenario", async () => {
      const scenario = await generateMarketAbuseScenario(scenarioForm);
      setGeneratedScenario(scenario);
      setScenarioMessage(`Generated ${scenario.title} with ${scenario.events.length} simulator-compatible events.`);
    }, setScenarioMessage);
  }

  async function replayGeneratedScenario() {
    if (!generatedScenario) return;
    await runExperimentAction("replay-ai-scenario", async () => {
      const response = await injectNebiusAttackScenario(generatedScenario.scenario_id);
      setScenarioMessage(response.message);
      await refreshControlPlane();
    }, setScenarioMessage);
  }

  async function runAiDetectorTournament() {
    await runExperimentAction("run-ai-tournament", async () => {
      let tournament = await startDetectorTournament(tournamentForm);
      setDetectorTournament(tournament);
      setTournamentMessage(`${tournament.status.replaceAll("_", " ")}: ${tournament.summary}`);
      if (tournament.status === "queued" || tournament.status === "running") {
        for (
          let attempt = 0;
          attempt < TOURNAMENT_POLL_ATTEMPTS && tournament.status !== "completed" && tournament.status !== "failed";
          attempt += 1
        ) {
          await wait(TOURNAMENT_POLL_INTERVAL_MS);
          tournament = await getDetectorTournament(tournament.tournament_id);
          setDetectorTournament(tournament);
          setTournamentMessage(`${tournament.status.replaceAll("_", " ")}: ${tournament.summary}`);
        }
      }
      await refreshControlPlane();
    }, setTournamentMessage);
  }

  async function runServerlessSmoke() {
    await runExperimentAction("run-serverless-smoke", async () => {
      const result = await runServerlessSmokeDemo();
      setServerlessSmokeResult(result);
      setDetectorTournament(result.tournament);
      setInvestigationTeamReport(result.investigation ?? null);
      setTournamentMessage(`${result.mode.replaceAll("_", " ")}: ${result.summary}`);
    }, setTournamentMessage);
  }

  function switchRuntimeMode(nextMode: RuntimeMode) {
    storeRuntimeMode(nextMode);
    setRuntimeMode(nextMode);
  }

  function startDemoScenario(scenario: DemoScenario) {
    switchRuntimeMode(scenario.runtime);
    const params = new URLSearchParams({
      attack: scenario.attackKey,
      demoScenario: scenario.id,
      runtime: scenario.runtime
    });
    navigate(`/attack-scenarios?${params.toString()}`);
  }

  const runtimeLabel = visibleRuntimeOptions.find((option) => option.value === runtimeMode)?.label ?? "Local Demo";
  const endpointConfigured = Boolean(nebiusStatus?.incident_explainer_configured);
  const jobConfigured = Boolean(nebiusStatus?.job_submit_template_configured);
  const endpointWillUseNebius = runtimeMode !== "local-demo" && endpointConfigured;
  const jobWillUseNebius = runtimeMode !== "local-demo" && jobConfigured;
  const fallbackStatus = endpointWillUseNebius || jobWillUseNebius ? "cloud path available" : runtimeMode === "local-demo" ? "Simulated / Local Demo" : "fallback to deterministic mock";
  const deploymentRequired = runtimeMode === "nebius-cloud" && !(nebiusStatus?.api_key_configured || nebiusStatus?.cli_installed);
  const workflowSteps = [
    "Runtime",
    "Scenario Generator",
    "Investigation Team",
    "Detector Tournament",
    "Execution Trace"
  ];
  const activeWorkflowTitle = workflowSteps[activeWorkflowStep - 1] ?? workflowSteps[0];
  const goToPreviousWorkflowStep = () => setActiveWorkflowStep((step) => Math.max(1, step - 1));
  const goToNextWorkflowStep = () => setActiveWorkflowStep((step) => Math.min(workflowSteps.length, step + 1));

  return (
    <section className="nebius-control-page">
      <header className="ai-platform-header">
        <div>
          <h1>Command Center</h1>
          <p>Generate suspicious workload, detect incidents with Nebius AI, and run detector tournaments on Nebius Serverless Jobs.</p>
        </div>
      </header>

      <section className="command-center-service-grid" aria-label="AI command center capabilities">
        <CommandCenterServiceCard
          title="Serverless Endpoint"
          detail={nebiusStatus?.endpoint_base_url || "Mock endpoint active for local demo"}
          status={endpointWillUseNebius ? "configured" : runtimeMode === "nebius-cloud" ? "pending" : "mock mode"}
        />
        <CommandCenterServiceCard
          title="Investigation Team"
          detail={endpointWillUseNebius ? nebiusStatus?.model || "Model configured" : "Deterministic investigator fallback"}
          status={endpointWillUseNebius ? "active" : "mock mode"}
        />
        <CommandCenterServiceCard
          title="Scenario Generator"
          detail={nebiusStatus?.scenario_generator_configured ? "Scenario endpoint configured" : "Local scenario templates enabled"}
          status={nebiusStatus?.scenario_generator_configured ? "configured" : "mock mode"}
        />
        <CommandCenterServiceCard
          title="Serverless Jobs"
          detail={jobConfigured ? nebiusStatus?.job_image || "Job image configured" : "Local smart batch runner ready"}
          status={jobConfigured ? "configured" : runtimeMode === "nebius-cloud" ? "pending" : "mock mode"}
        />
        <CommandCenterServiceCard
          title="Detector Tournament"
          detail={experiment ? `${experiment.attack_count} workloads · batch ${experiment.batch_size}` : "Create a detector tournament"}
          status={experiment ? experiment.status.replaceAll("_", " ") : "pending"}
        />
      </section>

      <ServerlessSmokeDemoPanel
        busy={experimentBusyAction === "run-serverless-smoke"}
        result={serverlessSmokeResult}
        onRun={() => void runServerlessSmoke()}
      />

      <section className="command-center-wizard" aria-label="Command Center workflow">
        <div className="command-center-wizard-header">
          <button
            aria-label="Previous workflow step"
            className="secondary-button wizard-arrow-button"
            disabled={activeWorkflowStep === 1}
            onClick={goToPreviousWorkflowStep}
            type="button"
          >
            &lt;&lt;
          </button>
          <div>
            <span>Step {activeWorkflowStep} of {workflowSteps.length}</span>
            <strong>{activeWorkflowTitle}</strong>
          </div>
          <button
            aria-label="Next workflow step"
            className="secondary-button wizard-arrow-button"
            disabled={activeWorkflowStep === workflowSteps.length}
            onClick={goToNextWorkflowStep}
            type="button"
          >
            &gt;&gt;
          </button>
        </div>
        <div className="command-center-step-tabs" role="tablist" aria-label="Command Center steps">
          {workflowSteps.map((label, index) => {
            const step = index + 1;
            return (
              <button
                aria-selected={step === activeWorkflowStep}
                className={step === activeWorkflowStep ? "active" : ""}
                key={label}
                onClick={() => setActiveWorkflowStep(step)}
                role="tab"
                type="button"
              >
                <span>{step}</span>
                {label}
              </button>
            );
          })}
        </div>
      </section>

      <section className="nebius-infra-workflow">
        {activeWorkflowStep === 1 ? <InfrastructureSection
          step={1}
          title="Runtime"
          description="Current local demo, endpoint, job, artifact, and fallback status for the command-center workflow."
        >
          <RuntimeStatusCard status={runtimeStatus} usage={usageMetrics} />
          <InfrastructureMetricGrid>
            <MetricBlock label="Current mode" value={runtimeLabel} />
            <MetricBlock label="Frontend / backend / runner" value={runtimeMode === "nebius-cloud" ? "cloud" : "local"} />
            <MetricBlock label="Cloud connection status" value={nebiusStatus?.api_key_configured || nebiusStatus?.cli_installed ? "Connected" : deploymentRequired ? "Deployment required" : "Not configured"} />
            <MetricBlock label="Model name" value={nebiusStatus?.model || "mock deterministic model"} />
            <MetricBlock label="Endpoint mode" value={nebiusStatus?.endpoint_mode ?? nebiusObservatory?.endpoint_mode ?? "mock"} />
            <MetricBlock label="Endpoint availability" value={endpointWillUseNebius ? "real endpoint used" : runtimeMode === "nebius-cloud" ? "endpoint unavailable" : "mock fallback"} />
            <MetricBlock label="Job availability" value={jobWillUseNebius ? "cloud job available" : runtimeMode === "nebius-cloud" ? "Deployment required" : "deterministic fallback"} />
          </InfrastructureMetricGrid>
          <div className="nebius-button-row">
            <button className="secondary-button" onClick={() => switchRuntimeMode("local-demo")} type="button">Switch runtime: Local Demo</button>
            <button className="secondary-button" onClick={() => switchRuntimeMode("nebius-cloud")} type="button">Switch runtime: Cloud</button>
            <button className="secondary-button" disabled={experimentBusyAction === "test-endpoint-health"} onClick={() => void testEndpointHealth()} type="button">Test connection</button>
          </div>
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
            status={nebiusStatus}
          />
        </InfrastructureSection> : null}

        {activeWorkflowStep === 2 ? <InfrastructureSection
          step={2}
          title="Scenario Generator"
          description="Generate synthetic market-abuse workloads with ground truth, then replay them through the existing Arena scenario path."
        >
          <DemoScenariosSection
            deploymentRequired={deploymentRequired}
            onStart={startDemoScenario}
          />
          <AIScenarioGeneratorPanel
            busyAction={experimentBusyAction}
            form={scenarioForm}
            generatedScenario={generatedScenario}
            message={scenarioMessage}
            onGenerate={() => void generateAiScenario()}
            onReplay={() => void replayGeneratedScenario()}
            onUpdate={updateScenarioForm}
          />
        </InfrastructureSection> : null}

        {activeWorkflowStep === 3 ? <InfrastructureSection
          step={3}
          title="Investigation Team"
          description="Send detector incidents for explanation, report generation, and analyst-ready findings."
        >
          <InfrastructureMetricGrid>
            <MetricBlock label="Inference calls" value={String(usageMetrics.aiEndpointCallsToday)} />
            <MetricBlock label="Average latency" value={`${usageMetrics.averageLlmLatencySec.toFixed(2)}s`} />
            <MetricBlock label="Current incident explanation" value={endpointWillUseNebius ? "real endpoint used" : "mock fallback"} />
            <MetricBlock label="Model name" value={nebiusStatus?.model || "mock deterministic model"} />
            <MetricBlock label="Fallback status" value={endpointWillUseNebius ? "real endpoint used" : fallbackStatus} />
            <MetricBlock label="Report reasoning" value={runtimeMode !== "local-demo" && nebiusStatus?.investigation_report_configured ? "real endpoint used" : "mock fallback"} />
          </InfrastructureMetricGrid>
          <p className="fallback-note">{runtimeMode === "nebius-cloud" ? "Cloud mode calls a real endpoint when configured. If it fails, the response falls back to deterministic mock AI and is labeled clearly." : "Local Demo uses a deterministic mock response. Switch to Cloud to run this explanation on a real endpoint."}</p>
          <div className="nebius-button-row">
            <button className="primary-button" disabled={experimentBusyAction === "run-investigation-team"} onClick={() => void runInvestigationTeam()} type="button">
              {experimentBusyAction === "run-investigation-team" ? "Running..." : "Run Nebius AI Investigation Team"}
            </button>
            <button className="secondary-button" disabled={!experiment || experimentBusyAction === "run-investigations"} onClick={() => void runExperimentInvestigations()} type="button">Explain current incident</button>
          </div>
          {investigationTeamReport ? <InvestigationTeamReport report={investigationTeamReport} /> : null}
          {experimentMessage ? <p className="experiment-message">{experimentMessage}</p> : null}
        </InfrastructureSection> : null}

        {activeWorkflowStep === 4 ? <InfrastructureSection
          step={4}
          title="Detector Tournament"
          description="Run local or serverless detector tournaments over generated market workloads and compare detector outcomes."
        >
          <DetectorTournamentPanel
            busyAction={experimentBusyAction}
            form={tournamentForm}
            message={tournamentMessage}
            onRun={() => void runAiDetectorTournament()}
            onToggleDetector={toggleTournamentDetector}
            onToggleManipulation={toggleTournamentManipulation}
            onUpdate={updateTournamentForm}
            tournament={detectorTournament}
          />
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
        </InfrastructureSection> : null}

        {activeWorkflowStep === 5 ? <InfrastructureSection
          step={5}
          title="Execution Trace"
          description="Compact execution graph plus endpoint, jobs, latency, tokens, GPU, cost, artifacts, and real versus simulated status."
        >
          <ExecutionGraph endpointActive={endpointWillUseNebius} jobActive={jobWillUseNebius} runtimeMode={runtimeMode} />
          <InfrastructureMetricGrid>
            <MetricBlock label="Endpoint" value={endpointWillUseNebius ? "real endpoint used" : runtimeMode === "nebius-cloud" ? "endpoint unavailable" : "mock deterministic endpoint"} />
            <MetricBlock label="Jobs" value={jobWillUseNebius ? latestExperimentJob(experimentJobs)?.status.replaceAll("_", " ") ?? "cloud job available" : runtimeMode === "nebius-cloud" ? "Deployment required" : latestExperimentJob(experimentJobs)?.status.replaceAll("_", " ") ?? "deterministic mock results"} />
            <MetricBlock label="Latency" value={`${usageMetrics.averageLlmLatencySec.toFixed(2)}s`} />
            <MetricBlock label="Tokens" value={String(usageMetrics.tokensUsed)} />
            <MetricBlock label="GPU" value={runtimeMode === "nebius-cloud" && (endpointWillUseNebius || jobWillUseNebius) ? "GPU runtime" : "not used in Local Demo"} />
            <MetricBlock label="Cost" value={`$${usageMetrics.estimatedCostUsd.toFixed(2)}`} />
            <MetricBlock label="Model name" value={nebiusStatus?.model || "mock deterministic model"} />
            <MetricBlock label="Execution type" value={runtimeMode === "local-demo" ? "Simulated / Local Demo" : endpointWillUseNebius || jobWillUseNebius ? "real cloud execution" : "Simulated / fallback"} />
            <MetricBlock label="Fallback status" value={fallbackStatus} />
            <MetricBlock label="Artifacts" value={String(artifacts.length)} />
            <MetricBlock label="Replay storage" value={`${usageMetrics.replayStorageMb.toFixed(0)} MB`} />
          </InfrastructureMetricGrid>
          <p className="fallback-note">No credentials, Google login, or deployment are required in Local Demo. Benchmark results use deterministic mock data until Cloud mode is selected.</p>
          <UsageCostMonitor metrics={usageMetrics} />
          <ExperimentArtifactLinks artifacts={experiment ? experimentArtifactsFrom(experiment, experimentSummary) : []} experimentId={experiment?.id} />
        </InfrastructureSection> : null}
      </section>

    </section>
  );
}

function CommandCenterServiceCard({
  detail,
  status,
  title
}: {
  detail: string;
  status: string;
  title: string;
}) {
  return (
    <article className="command-center-service-card">
      <div>
        <h2>{title}</h2>
        <p>{detail}</p>
      </div>
      <span className={`runtime-status ${status.toLowerCase().replace(/\s+/g, "-")}`}>{status}</span>
    </article>
  );
}

function ServerlessSmokeDemoPanel({
  busy,
  onRun,
  result
}: {
  busy: boolean;
  onRun: () => void;
  result: ServerlessSmokeResponse | null;
}) {
  const jobStatus = String(result?.serverless_job.status ?? "not run");
  const jobId = result?.serverless_job.job_id ? String(result.serverless_job.job_id) : "pending";
  return (
    <section className="panel serverless-smoke-panel" aria-label="Nebius Serverless E2E demo">
      <div className="nebius-card-heading">
        <div>
          <span>Polished E2E demo</span>
          <h2>Nebius Serverless Spoofing Incident</h2>
          <p className="nebius-card-purpose">
            AI-generated spoofing incident {"->"} LOB simulation {"->"} detector alert {"->"} LLM explanation {"->"} investigation report {"->"} detector tournament {"->"} artifacts.
          </p>
        </div>
        <span className={`runtime-status ${result?.mode ?? "pending"}`}>{result?.mode.replaceAll("_", " ") ?? "ready"}</span>
      </div>
      <div className="nebius-button-row">
        <button className="primary-button" disabled={busy} onClick={onRun} type="button">
          {busy ? "Running E2E demo..." : "Run Serverless E2E Demo"}
        </button>
        {result ? <span className="fallback-note">Artifacts written to outputs/serverless-smoke/</span> : null}
      </div>
      {result ? (
        <>
          <InfrastructureMetricGrid>
            <MetricBlock label="Current mode" value={result.mode.replaceAll("_", " ")} />
            <MetricBlock label="Scenario" value={result.scenario_id} />
            <MetricBlock label="Incident" value={result.incident_id ?? "not created"} />
            <MetricBlock label="Detector alerts" value={String(result.detector_alerts.length)} />
            <MetricBlock label="Job status" value={jobStatus.replaceAll("_", " ")} />
            <MetricBlock label="Job id" value={jobId} />
          </InfrastructureMetricGrid>
          <div className="experiment-output-grid">
            <div className="nebius-result-block">
              <span>Incident explanation</span>
              <p>{result.explanation?.plain_english_summary ?? "No incident explanation available."}</p>
              {result.explanation?.evidence?.length ? (
                <ul>
                  {result.explanation.evidence.slice(0, 4).map((item) => <li key={item}>{item}</li>)}
                </ul>
              ) : null}
            </div>
            <div className="nebius-result-block">
              <span>Detector evidence</span>
              <ul>
                {result.detector_alerts.slice(0, 5).map((alert, index) => (
                  <li key={`${String(alert.name ?? alert.detector ?? "detector")}-${index}`}>
                    {String(alert.name ?? alert.detector ?? "detector")}: {String(alert.confidence ?? alert.suspicion_score ?? "n/a")}
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="experiment-output-grid">
            <div className="nebius-result-block">
              <span>Tournament leaderboard</span>
              <table className="leaderboard-table">
                <thead>
                  <tr>
                    <th>Detector</th>
                    <th>Scenario</th>
                    <th>F1</th>
                    <th>FP</th>
                    <th>FN</th>
                  </tr>
                </thead>
                <tbody>
                  {result.tournament.leaderboard.slice(0, 8).map((row) => (
                    <tr key={`${row.detector}-${row.scenario}`}>
                      <td>{row.detector}</td>
                      <td>{row.scenario}</td>
                      <td>{row.f1.toFixed(2)}</td>
                      <td>{row.false_positives}</td>
                      <td>{row.false_negatives}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="nebius-result-block">
              <span>Artifacts</span>
              <div className="artifact-link-list">
                {result.artifacts.map((artifact) => (
                  <a href={artifactDownloadUrl(artifact.path)} key={artifact.name}>
                    {artifact.name}
                  </a>
                ))}
              </div>
              <span>Serverless benefits</span>
              <ul>
                {result.benefits.map((benefit) => <li key={benefit}>{benefit}</li>)}
              </ul>
            </div>
          </div>
          {result.investigation ? <InvestigationTeamReport report={result.investigation} /> : null}
          {String(result.serverless_job.message ?? "") ? <p className="fallback-note">{String(result.serverless_job.message)}</p> : null}
        </>
      ) : null}
    </section>
  );
}

function InvestigationTeamReport({ report }: { report: AIInvestigationTeamResponse }) {
  return (
    <section className="nebius-result-block investigation-team-report" aria-label="AI Investigation Team result">
      <div className="nebius-card-heading">
        <div>
          <span>Final verdict</span>
          <h2>{report.manipulation_type.replaceAll("_", " ")}</h2>
          <p className="nebius-card-purpose">{report.executive_summary}</p>
        </div>
        <span className={`runtime-status ${report.mode}`}>{report.mode}</span>
      </div>
      <InfrastructureMetricGrid>
        <MetricBlock label="Investigation" value={report.investigation_id} />
        <MetricBlock label="Risk score" value={report.risk_score.toFixed(2)} />
        <MetricBlock label="Confidence" value={report.confidence.toFixed(2)} />
        <MetricBlock label="Consensus" value={report.consensus} />
      </InfrastructureMetricGrid>
      <div className="experiment-output-grid">
        <div className="nebius-result-block">
          <span>Agent findings</span>
          <div className="generated-scenario-list">
            {report.agents.map((agent) => (
              <article className="generated-scenario-card" key={agent.name}>
                <strong>{agent.name}</strong>
                <p>{agent.role}</p>
                <p>{agent.finding}</p>
                <span className="runtime-status configured">{agent.confidence.toFixed(2)}</span>
                <ul>
                  {agent.evidence.map((item) => (
                    <li key={`${agent.name}-${item.key}-${String(item.value)}`}>
                      {item.label}: {String(item.value)}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
        <div className="nebius-result-block">
          <span>Evidence timeline</span>
          <ol>
            {report.evidence_timeline.map((item) => (
              <li key={`${item.sequence}-${item.event}`}>
                {item.event}
              </li>
            ))}
          </ol>
          <p><strong>Recommended action</strong> {report.recommended_action}</p>
          {report.fallback_reason ? <p className="fallback-note">{report.fallback_reason}</p> : null}
        </div>
      </div>
    </section>
  );
}

function AIScenarioGeneratorPanel({
  busyAction,
  form,
  generatedScenario,
  message,
  onGenerate,
  onReplay,
  onUpdate
}: {
  busyAction: ExperimentAction | null;
  form: MarketAbuseScenarioGenerationRequest;
  generatedScenario: MarketAbuseScenarioResponse | null;
  message: string | null;
  onGenerate: () => void;
  onReplay: () => void;
  onUpdate: <K extends keyof MarketAbuseScenarioGenerationRequest>(
    key: K,
    value: MarketAbuseScenarioGenerationRequest[K]
  ) => void;
}) {
  const replaySupported = Boolean(generatedScenario?.replay?.supported ?? generatedScenario);
  return (
    <div className="experiment-output-grid ai-scenario-generator-panel">
      <div className="nebius-result-block">
        <span>Nebius AI Scenario Generator</span>
        <div className="experiment-form-grid">
          <label>
            Manipulation type
            <select
              value={form.manipulation_type}
              onChange={(event) => onUpdate("manipulation_type", event.target.value as MarketAbuseScenarioGenerationRequest["manipulation_type"])}
            >
              <option value="spoofing">Spoofing</option>
              <option value="layering">Layering</option>
              <option value="wash_trading">Wash trading</option>
              <option value="quote_stuffing">Quote stuffing</option>
            </select>
          </label>
          <label>
            Difficulty
            <select
              value={form.difficulty}
              onChange={(event) => onUpdate("difficulty", event.target.value as MarketAbuseScenarioGenerationRequest["difficulty"])}
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
              <option value="adversarial">Adversarial</option>
            </select>
          </label>
          <label>
            Symbol
            <input
              maxLength={16}
              value={form.symbol}
              onChange={(event) => onUpdate("symbol", event.target.value.toUpperCase())}
            />
          </label>
          <label>
            Duration
            <input
              max={600}
              min={30}
              type="number"
              value={form.duration_ticks}
              onChange={(event) => onUpdate("duration_ticks", Number(event.target.value))}
            />
          </label>
          <label>
            Liquidity
            <select
              value={form.liquidity_regime}
              onChange={(event) => onUpdate("liquidity_regime", event.target.value as MarketAbuseScenarioGenerationRequest["liquidity_regime"])}
            >
              <option value="thin">Thin</option>
              <option value="normal">Normal</option>
              <option value="deep">Deep</option>
            </select>
          </label>
          <label>
            Volatility
            <select
              value={form.volatility_regime}
              onChange={(event) => onUpdate("volatility_regime", event.target.value as MarketAbuseScenarioGenerationRequest["volatility_regime"])}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
        </div>
        <div className="nebius-button-row">
          <button className="primary-button" disabled={busyAction === "generate-ai-scenario"} onClick={onGenerate} type="button">
            {busyAction === "generate-ai-scenario" ? "Generating..." : "Generate AI Scenario"}
          </button>
          <button className="secondary-button" disabled={!generatedScenario || !replaySupported || busyAction === "replay-ai-scenario"} onClick={onReplay} type="button">
            {busyAction === "replay-ai-scenario" ? "Replaying..." : "Replay in Arena"}
          </button>
        </div>
        {message ? <p className="experiment-message">{message}</p> : null}
      </div>

      <div className="nebius-result-block">
        <span>Generated scenario preview</span>
        {generatedScenario ? (
          <div className="generated-scenario-card">
            <div className="nebius-card-heading">
              <div>
                <h3>{generatedScenario.title}</h3>
                <p className="nebius-card-purpose">{generatedScenario.description}</p>
              </div>
              <span className={`runtime-status ${generatedScenario.mode}`}>{generatedScenario.mode}</span>
            </div>
            <InfrastructureMetricGrid>
              <MetricBlock label="Scenario" value={generatedScenario.scenario_id} />
              <MetricBlock label="Risk" value={generatedScenario.expected_detector_behavior.expected_risk_score.toFixed(2)} />
              <MetricBlock label="Events" value={String(generatedScenario.events.length)} />
              <MetricBlock label="Replay route" value={String(generatedScenario.replay.route ?? "projection")} />
            </InfrastructureMetricGrid>
            <div>
              <strong>Ground truth</strong>
              <ul>
                <li>Label: {generatedScenario.ground_truth.label.replaceAll("_", " ")}</li>
                <li>Agents: {generatedScenario.ground_truth.manipulator_agent_ids.join(", ")}</li>
                <li>Signals: {generatedScenario.ground_truth.expected_detector_targets.join(", ")}</li>
              </ul>
            </div>
            <div>
              <strong>Timeline</strong>
              <ol>
                {generatedScenario.events.slice(0, 4).map((event) => (
                  <li key={event.event_id}>
                    tick {event.tick}: {event.message}
                  </li>
                ))}
              </ol>
            </div>
            {generatedScenario.fallback_reason ? <p className="fallback-note">{generatedScenario.fallback_reason}</p> : null}
          </div>
        ) : (
          <p className="fallback-note">Generate a scenario to preview ground truth, event timeline, and replay projection.</p>
        )}
      </div>
    </div>
  );
}

function DemoScenariosSection({
  deploymentRequired,
  onStart
}: {
  deploymentRequired: boolean;
  onStart: (scenario: DemoScenario) => void;
}) {
  return (
    <details className="demo-scenarios-section">
      <summary>
        <span>Demo Scenarios</span>
        <strong>Choose a guided path through Scenario Setup {"->"} Workload Generator {"->"} AI Investigation.</strong>
      </summary>
      <div className="demo-scenario-grid">
        {demoScenarios.map((scenario) => {
          const cloudScenario = scenario.runtime === "nebius-cloud";
          return (
            <article className="demo-scenario-card" key={scenario.id}>
              <div className="nebius-card-heading">
                <div>
                  <h3>{scenario.title}</h3>
                  <p className="nebius-card-purpose">Runtime: {scenario.runtime === "local-demo" ? "Local Demo" : "Cloud"}</p>
                </div>
                {cloudScenario && deploymentRequired ? <span className="runtime-status not_configured">Deployment required</span> : null}
              </div>
              <div>
                <span>Demonstrates</span>
                <ul>
                  {scenario.demonstrates.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
              {scenario.duration ? <p><strong>Duration</strong> {scenario.duration}</p> : null}
              {scenario.purpose ? <p><strong>Purpose</strong> {scenario.purpose}</p> : null}
              {cloudScenario && deploymentRequired ? <p className="fallback-note">Deployment required. Cloud status is shown honestly before execution.</p> : null}
              <button className="primary-button" onClick={() => onStart(scenario)} type="button">{scenario.cta ?? "Start"}</button>
            </article>
          );
        })}
      </div>
    </details>
  );
}

function InfrastructureSection({
  children,
  description,
  step,
  title
}: {
  children: ReactNode;
  description: string;
  step: number;
  title: string;
}) {
  return (
    <section className="panel nebius-infra-section">
      <div className="nebius-card-heading">
        <div>
          <div className="workflow-step-heading">
            <span>{step}</span>
            <h2>{title}</h2>
          </div>
          <p className="nebius-card-purpose">{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function InfrastructureMetricGrid({ children }: { children: ReactNode }) {
  return <div className="nebius-infra-metric-grid">{children}</div>;
}

function ExecutionGraph({
  endpointActive,
  jobActive,
  runtimeMode
}: {
  endpointActive: boolean;
  jobActive: boolean;
  runtimeMode: RuntimeMode;
}) {
  const endpointStatus = endpointActive ? "real endpoint" : runtimeMode === "nebius-cloud" ? "endpoint unavailable" : "mock endpoint";
  const jobStatus = jobActive ? "cloud job" : runtimeMode === "nebius-cloud" ? "deployment required" : "mock job";
  const resultsStatus = endpointActive || jobActive ? "real results" : "deterministic results";
  const steps = [
    ["Scenario", "ready"],
    ["Detector", "ready"],
    ["Endpoint", endpointStatus],
    ["Job", jobStatus],
    ["Result", resultsStatus]
  ];
  return (
    <ol className="execution-graph" aria-label="Execution graph">
      {steps.map(([label, status]) => (
        <li key={label}>
          <span>{label}</span>
          <strong>{status}</strong>
        </li>
      ))}
    </ol>
  );
}

function runtimeFrom(status: NebiusStatus, observatory: NebiusObservatory): NebiusRuntimeStatus {
  const latest = observatory.latest_batch;
  const endpointConfigured = status.incident_explainer_configured
    || status.scenario_generator_configured
    || status.orderbook_alert_configured
    || status.investigation_report_configured;
  return {
    activeSimulation: latest ? String(latest.scenarios ?? "Cloud batch") : "Spoofing Attack #042",
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

function DetectorTournamentPanel({
  busyAction,
  form,
  message,
  onRun,
  onToggleDetector,
  onToggleManipulation,
  onUpdate,
  tournament
}: {
  busyAction: ExperimentAction | null;
  form: DetectorTournamentStartRequest;
  message: string | null;
  onRun: () => void;
  onToggleDetector: (value: DetectorTournamentStartRequest["detector_set"][number]) => void;
  onToggleManipulation: (value: DetectorTournamentStartRequest["manipulation_types"][number]) => void;
  onUpdate: <K extends keyof DetectorTournamentStartRequest>(key: K, value: DetectorTournamentStartRequest[K]) => void;
  tournament: DetectorTournamentResponse | null;
}) {
  const manipulationOptions: DetectorTournamentStartRequest["manipulation_types"] = ["spoofing", "layering", "wash_trading", "quote_stuffing"];
  const detectorOptions: DetectorTournamentStartRequest["detector_set"] = ["spoofing_like", "layering_like", "quote_stuffing", "liquidity_shock"];
  return (
    <section className="nebius-result-block detector-tournament-panel" aria-label="AI Detector Tournament">
      <div className="nebius-card-heading">
        <div>
          <span>Powered by Nebius Serverless Jobs</span>
          <h2>Run Nebius AI Detector Tournament</h2>
          <p className="nebius-card-purpose">Compare detectors against synthetic ground truth with local fallback or a Nebius Serverless Job path.</p>
        </div>
        <span className={`runtime-status ${tournament?.execution_mode ?? "local_mock"}`}>{tournament?.execution_mode.replaceAll("_", " ") ?? "local mock"}</span>
      </div>
      <div className="experiment-lab-layout">
        <div className="experiment-form-card">
          <div className="experiment-number-grid">
            <label>
              <span>Scenarios</span>
              <input
                min={1}
                max={1000}
                type="number"
                value={form.number_of_scenarios}
                onChange={(event) => onUpdate("number_of_scenarios", Number(event.target.value))}
              />
            </label>
            <label>
              <span>Seed</span>
              <input
                type="number"
                value={form.random_seed}
                onChange={(event) => onUpdate("random_seed", Number(event.target.value))}
              />
            </label>
            <label>
              <span>Execution</span>
              <select
                value={form.execution_mode}
                onChange={(event) => onUpdate("execution_mode", event.target.value as DetectorTournamentStartRequest["execution_mode"])}
              >
                <option value="local_mock">Local Mock</option>
                <option value="local">Local Job Runner</option>
                <option value="nebius">Nebius Job</option>
              </select>
            </label>
          </div>
          <div className="experiment-scenario-picker" aria-label="Tournament manipulation types">
            {manipulationOptions.map((option) => (
              <button
                className={form.manipulation_types.includes(option) ? "scenario-pill selected" : "scenario-pill"}
                key={option}
                onClick={() => onToggleManipulation(option)}
                type="button"
              >
                {option.replaceAll("_", " ")}
              </button>
            ))}
          </div>
          <div className="experiment-scenario-picker" aria-label="Tournament detectors">
            {detectorOptions.map((option) => (
              <button
                className={form.detector_set.includes(option) ? "scenario-pill selected" : "scenario-pill"}
                key={option}
                onClick={() => onToggleDetector(option)}
                type="button"
              >
                {option.replaceAll("_", " ")}
              </button>
            ))}
          </div>
          <button className="primary-button" disabled={busyAction === "run-ai-tournament"} onClick={onRun} type="button">
            {busyAction === "run-ai-tournament" ? "Running..." : "Run Nebius AI Detector Tournament"}
          </button>
          {message ? <p className="experiment-message">{message}</p> : null}
        </div>
        <div className="experiment-progress-card">
          <div className="experiment-active-summary">
            <span>Latest Tournament</span>
            <strong>{tournament?.tournament_id ?? "No tournament run yet"}</strong>
            <p>{tournament?.summary ?? "Local Mock mode runs fully without Nebius credentials. Nebius Job mode keeps the cloud path visible and isolated."}</p>
          </div>
          {tournament ? (
            <>
              <InfrastructureMetricGrid>
                <MetricBlock label="Status" value={tournament.status.replaceAll("_", " ")} />
                <MetricBlock label="Macro F1" value={metricDisplay(tournament.metrics.macro_f1)} />
                <MetricBlock label="False positives" value={metricDisplay(tournament.metrics.false_positives)} />
                <MetricBlock label="False negatives" value={metricDisplay(tournament.metrics.false_negatives)} />
              </InfrastructureMetricGrid>
              <ExperimentLeaderboardTable
                leaderboard={tournament.leaderboard.slice(0, 8).map((row) => ({
                  alert_count: row.false_positives + row.false_negatives,
                  avg_detection_latency_ms: row.avg_detection_latency_ms,
                  f1: row.f1,
                  precision: row.precision,
                  recall: row.recall,
                  scenario: `${row.scenario} / ${row.detector}`
                }))}
              />
              <ExperimentArtifactLinks artifacts={artifactLinksFromTournament(tournament)} />
              {tournament.fallback_reason ? <p className="fallback-note">{tournament.fallback_reason}</p> : null}
            </>
          ) : null}
        </div>
      </div>
    </section>
  );
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
    <section className="experiment-lab-panel">
      <div className="nebius-card-heading">
        <div>
          <h2>Detector Tournament</h2>
        </div>
        <div className="nebius-button-row">
          <span className={`runtime-status ${experiment?.status ?? "missing"}`}>{experiment?.status.replaceAll("_", " ") ?? "no benchmark"}</span>
          <button className="secondary-button" onClick={onRefresh} type="button">Refresh</button>
        </div>
      </div>
      <div className="benchmark-capability-strip" aria-label="Benchmark capabilities">
        <span>Compare models</span>
        <span>Run Jobs</span>
        <span>Detector comparison</span>
        <span>Model comparison</span>
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
              <span>Workload count</span>
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
          <div className="experiment-scenario-picker" aria-label="Benchmark scenarios">
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
            {busyAction === "create-experiment" ? "Creating..." : "Create benchmark"}
          </button>
        </div>

        <div className="experiment-progress-card">
          <div className="experiment-active-summary">
            <span>Current Benchmark</span>
            <strong>{experiment?.name ?? "Create or refresh a detector tournament"}</strong>
            <p>{experiment ? `${experiment.id} · ${experiment.attack_count} workloads · batch ${experiment.batch_size}` : "Local Demo benchmark runs deterministic mock results locally, then Cloud mode can run the same benchmark as serverless jobs."}</p>
          </div>
          <div className="experiment-flow-actions">
            <button disabled={!canRun || busyAction === "generate-manifest"} onClick={onGenerateManifest} type="button">Generate manifest</button>
            <button disabled={!canRun || busyAction === "run-local-batch"} onClick={onRunLocalBatch} type="button">Run Local Demo tournament</button>
            <button disabled={!canRun || busyAction === "submit-nebius"} onClick={onSubmitNebius} type="button">Run serverless job</button>
            <button disabled={!canRun || busyAction === "aggregate"} onClick={onAggregate} type="button">Aggregate</button>
            <button disabled={!canRun || busyAction === "run-investigations"} onClick={onRunInvestigations} type="button">Run AI Investigation</button>
          </div>
          {message ? <p className="experiment-message">{message}</p> : null}
          {pendingNebiusJob ? <p className="experiment-pending-note">pending cloud job execution: {pendingNebiusJob.message}</p> : null}
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
  status: NebiusStatus | null;
}) {
  const cloudJob = latestExperimentJob(jobs.filter((job) => job.backend === "nebius_serverless_job"));
  const endpointHealth = status?.endpoint_health ?? observatory?.endpoint_health ?? null;
  const endpointMode = status?.endpoint_mode ?? observatory?.endpoint_mode ?? "mock";
  const hasExperiment = Boolean(experiment);

  return (
    <section className="experiment-lab-panel real-nebius-deployment-panel">
      <div className="nebius-card-heading">
        <div>
          <h2>Deployment Status</h2>
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
          Submit serverless job
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
          Job submit template is not configured. Submitting records pending cloud execution and keeps Local Demo fallback available.
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
      <MetricBlock label="AI Investigation" value={String(summary?.investigation_count ?? metricValue(experiment, "investigation_count") ?? 0)} />
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
      <span>Benchmark job runs</span>
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
      <span>Execution artifacts</span>
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
        <p>Artifacts appear after benchmark generation, local execution, cloud jobs, aggregation, or AI Investigation.</p>
      )}
    </div>
  );
}

function ExperimentLeaderboardTable({ leaderboard }: { leaderboard: ExperimentLeaderboardRow[] }) {
  return (
    <div className="nebius-result-block experiment-leaderboard-block">
      <span>Benchmark leaderboard</span>
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
        <p>Aggregate the benchmark to populate detector rankings.</p>
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

function artifactLinksFromTournament(tournament: DetectorTournamentResponse): Array<[string, string]> {
  return Object.entries(tournament.artifacts).filter(([, path]) => typeof path === "string" && path.length > 0);
}

function metricValue(experiment: ManagedExperiment | null, key: string): number | null {
  if (!experiment) return null;
  for (const row of experiment.metrics) {
    const value = row[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return null;
}

function metricDisplay(value: unknown): string {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  if (typeof value === "string") return value;
  return "n/a";
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
  if (!experiment) return "no benchmark";
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
