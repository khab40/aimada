import { useEffect, useState, type ReactNode } from "react";
import {
  aggregateManagedExperiment,
  artifactDownloadUrl,
  createManagedExperiment,
  generateManagedExperimentManifest,
  getManagedExperiment,
  getManagedExperimentLeaderboard,
  getManagedExperimentSummary,
  getManagedExperimentReportUrl,
  getNebiusObservatory,
  getNebiusStatus,
  getReportsSummary,
  listManagedExperimentJobs,
  listManagedExperiments,
  collectManagedExperimentNebiusArtifacts,
  refreshManagedExperimentJobs,
  renderManagedExperimentNebiusJobConfig,
  runManagedExperimentInvestigations,
  runManagedExperimentLocalBatch,
  submitManagedExperimentNebius,
  type ExperimentJobRecord,
  type ExperimentLeaderboardRow,
  type ExperimentSummary,
  type ManagedExperiment,
  type ManagedExperimentCreateRequest,
  type NebiusObservatory,
  type NebiusStatus,
  type ReportsSummary
} from "@/api/client";
import { RuntimeStatusCard } from "@/features/nebius/components/RuntimeStatusCard";
import { UsageCostMonitor } from "@/features/nebius/components/UsageCostMonitor";
import type {
  ExperimentArtifact,
  NebiusRuntimeStatus,
  NebiusUsageMetrics
} from "@/features/nebius/types";

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
type ExperimentAction =
  | "create-experiment"
  | "generate-manifest"
  | "run-local-batch"
  | "submit-nebius"
  | "refresh-job-status"
  | "collect-cloud-artifacts"
  | "render-job-config"
  | "test-endpoint-health"
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
  const [artifacts, setArtifacts] = useState<ExperimentArtifact[]>([]);
  const [runtimeStatus, setRuntimeStatus] = useState<NebiusRuntimeStatus>(fallbackRuntimeStatus);
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
      setExperimentMessage(error instanceof Error ? error.message : "Managed Experiment Lab refresh failed.");
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
      setExperimentMessage(`Ran ${result.investigation_count} AI Investigator reports in ${result.investigation_mode} mode.`);
      await refreshExperimentDetails(experiment.id);
    });
  }

  return (
    <section className="nebius-control-page">
      <div className="panel nebius-hero-panel">
        <div>
          <h1>Why Nebius?</h1>
          <p>Nebius turns detector analysis into scalable AI infrastructure: model-backed inference, parallel batch execution, GPU-ready runtimes, durable artifacts, and cost visibility.</p>
        </div>
      </div>

      <section className="nebius-infra-workflow">
        <InfrastructureSection
          step={1}
          title="Models"
          description="Select and validate the hosted Nebius AI model used by backend inference adapters."
        >
          <InfrastructureMetricGrid>
            <MetricBlock label="Configured model" value={nebiusStatus?.model || "not configured"} />
            <MetricBlock label="Endpoint mode" value={nebiusStatus?.endpoint_mode ?? nebiusObservatory?.endpoint_mode ?? "mock"} />
            <MetricBlock label="Endpoint base URL" value={nebiusStatus?.endpoint_base_url || "not configured"} />
            <MetricBlock label="API key" value={nebiusStatus?.api_key_configured ? "configured" : "not configured"} />
          </InfrastructureMetricGrid>
          <div className="nebius-button-row">
            <button className="secondary-button" disabled={experimentBusyAction === "test-endpoint-health"} onClick={() => void testEndpointHealth()} type="button">Test endpoint health</button>
          </div>
        </InfrastructureSection>

        <InfrastructureSection
          step={2}
          title="Inference"
          description="Use Nebius for model-backed incident analysis and report generation behind the backend boundary."
        >
          <InfrastructureMetricGrid>
            <MetricBlock label="Inference calls" value={String(usageMetrics.aiEndpointCallsToday)} />
            <MetricBlock label="Average latency" value={`${usageMetrics.averageLlmLatencySec.toFixed(2)}s`} />
            <MetricBlock label="Incident explainer" value={nebiusStatus?.incident_explainer_configured ? "configured" : "not configured"} />
            <MetricBlock label="Report adapter" value={nebiusStatus?.investigation_report_configured ? "configured" : "not configured"} />
          </InfrastructureMetricGrid>
          <div className="nebius-button-row">
            <button className="secondary-button" disabled={!experiment || experimentBusyAction === "run-investigations"} onClick={() => void runExperimentInvestigations()} type="button">Run AI Investigator reports</button>
          </div>
          {experimentMessage ? <p className="experiment-message">{experimentMessage}</p> : null}
        </InfrastructureSection>

        <InfrastructureSection
          step={3}
          title="Batch Jobs"
          description="Run managed experiment batches without tying compute to the browser session."
        >
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
        </InfrastructureSection>

        <InfrastructureSection
          step={4}
          title="GPU Runtime"
          description="Prepare serverless job configs and track GPU-oriented job execution on Nebius."
        >
          <RuntimeStatusCard status={runtimeStatus} usage={usageMetrics} />
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
        </InfrastructureSection>

        <InfrastructureSection
          step={5}
          title="Artifacts"
          description="Collect reports, normalized batches, manifests, and datasets produced by Nebius workloads."
        >
          <ExperimentArtifactLinks artifacts={experiment ? experimentArtifactsFrom(experiment, experimentSummary) : []} experimentId={experiment?.id} />
          <InfrastructureMetricGrid>
            <MetricBlock label="Collected artifacts" value={String(artifacts.length)} />
            <MetricBlock label="Replay storage" value={`${usageMetrics.replayStorageMb.toFixed(0)} MB`} />
            <MetricBlock label="Artifact collection" value={artifactCollectionStatus(experiment)} />
          </InfrastructureMetricGrid>
        </InfrastructureSection>

        <InfrastructureSection
          step={6}
          title="Costs"
          description="Track endpoint calls, serverless jobs, token usage, and estimated infrastructure spend."
        >
          <UsageCostMonitor metrics={usageMetrics} />
        </InfrastructureSection>
      </section>

    </section>
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
    <section className="experiment-lab-panel">
      <div className="nebius-card-heading">
        <div>
          <h2>Managed Experiment Lab</h2>
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
            {busyAction === "create-experiment" ? "Creating..." : "Create Managed Experiment"}
          </button>
        </div>

        <div className="experiment-progress-card">
          <div className="experiment-active-summary">
            <span>Current Managed Experiment</span>
            <strong>{experiment?.name ?? "Create or refresh a Managed Experiment"}</strong>
            <p>{experiment ? `${experiment.id} · ${experiment.attack_count} workloads · batch ${experiment.batch_size}` : "The Managed Experiment flow runs through FastAPI and keeps Nebius AI calls behind the backend boundary."}</p>
          </div>
          <div className="experiment-flow-actions">
            <button disabled={!canRun || busyAction === "generate-manifest"} onClick={onGenerateManifest} type="button">Generate manifest</button>
            <button disabled={!canRun || busyAction === "run-local-batch"} onClick={onRunLocalBatch} type="button">Run local batch</button>
            <button disabled={!canRun || busyAction === "submit-nebius"} onClick={onSubmitNebius} type="button">Submit to Nebius</button>
            <button disabled={!canRun || busyAction === "aggregate"} onClick={onAggregate} type="button">Aggregate</button>
            <button disabled={!canRun || busyAction === "run-investigations"} onClick={onRunInvestigations} type="button">Run AI Investigator reports</button>
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
      <MetricBlock label="Detection Reports" value={String(summary?.investigation_count ?? metricValue(experiment, "investigation_count") ?? 0)} />
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
