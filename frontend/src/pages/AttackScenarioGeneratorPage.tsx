import { useEffect, useState } from "react";
import {
  generateNebiusAttackScenario,
  generateNebiusAttackVariants,
  generateNebiusScenarioGrid,
  getReportsSummary,
  injectNebiusAttackScenario,
  listNebiusAttackScenarios,
  runSmartBatches,
  saveNebiusAttackTemplate,
  type ReportsSummary
} from "@/api/client";
import { AttackScenarioGenerator } from "@/features/nebius/components/AttackScenarioGenerator";
import { ScenarioBatchGenerator } from "@/features/nebius/components/ScenarioBatchGenerator";
import { ServerlessRunnerCard } from "@/features/nebius/components/ServerlessRunnerCard";
import { TeamMark } from "@/components/TeamMark";
import type {
  AttackScenario,
  AttackScenarioInput,
  ExperimentBatchConfig,
  GeneratedScenario,
  ScenarioGridConfig,
  ServerlessExperimentJob
} from "@/features/nebius/types";

const initialAttackInput: AttackScenarioInput = {
  attackDuration: "Medium",
  attackType: "Spoofing",
  detectorDifficulty: "Medium",
  marketCondition: "Thin liquidity",
  objective: "Buy cheaper",
  redTeamAgentCount: 1,
  stealthLevel: "Medium"
};

const initialScenarioConfig: ScenarioGridConfig = {
  attackIntensity: "Aggressive",
  detectionThreshold: 0.72,
  latencyModel: "Random",
  liquidity: "Thin",
  marketVolatility: "High",
  numberOfAgents: 50
};

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

export function AttackScenarioGeneratorPage() {
  const [attackInput, setAttackInput] = useState<AttackScenarioInput>(initialAttackInput);
  const [attackScenario, setAttackScenario] = useState<AttackScenario | null>(null);
  const [attackVariants, setAttackVariants] = useState<AttackScenario[]>([]);
  const [batchConfig, setBatchConfig] = useState<ExperimentBatchConfig>(initialBatchConfig);
  const [busy, setBusy] = useState(false);
  const [generatedScenarios, setGeneratedScenarios] = useState<GeneratedScenario[]>([]);
  const [jobs, setJobs] = useState<ServerlessExperimentJob[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [scenarioConfig, setScenarioConfig] = useState<ScenarioGridConfig>(initialScenarioConfig);
  const [storedScenarios, setStoredScenarios] = useState<AttackScenario[]>([]);

  useEffect(() => {
    void refresh();
    void generateNebiusScenarioGrid(initialScenarioConfig).then(setGeneratedScenarios).catch(() => undefined);
  }, []);

  async function refresh() {
    const [scenarios, reports] = await Promise.all([
      listNebiusAttackScenarios(),
      getReportsSummary()
    ]);
    setStoredScenarios(scenarios);
    setAttackScenario((current) => current ?? scenarios[0] ?? null);
    setJobs(jobsFromReports(reports));
  }

  function selectAttackScenario(scenario: AttackScenario) {
    setAttackScenario(scenario);
    setBatchConfig((current) => ({
      ...current,
      attackType: displayAttackType(scenario.attackType),
      scenarioFamily: scenario.name,
      sourceAttackScenarioId: scenario.id
    }));
    setMessage(`${scenario.id} selected as the source attack plan for grids and Nebius batches.`);
  }

  async function runAction(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Attack scenario action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function generateAttack() {
    const scenario = await generateNebiusAttackScenario(attackInput);
    setAttackScenario(scenario);
    setStoredScenarios((current) => [scenario, ...current.filter((item) => item.id !== scenario.id)]);
    setBatchConfig((current) => ({
      ...current,
      attackType: attackInput.attackType,
      scenarioFamily: scenario.name,
      sourceAttackScenarioId: scenario.id
    }));
    setMessage(`${scenario.id} persisted and ready for live injection or Nebius Managed Experiment batches.`);
    await refresh();
  }

  async function generateVariants() {
    const variants = await generateNebiusAttackVariants(attackInput, 10);
    setAttackVariants(variants);
    setStoredScenarios((current) => [...variants, ...current.filter((stored) => !variants.some((variant) => variant.id === stored.id))]);
    if (variants[0]) {
      selectAttackScenario(variants[0]);
    }
    setMessage(`Generated ${variants.length} attack variants and persisted them for later batch use.`);
    await refresh();
  }

  async function injectScenario() {
    if (!attackScenario) return;
    const response = await injectNebiusAttackScenario(attackScenario.id);
    setMessage(response.message);
  }

  async function saveTemplate() {
    if (!attackScenario) return;
    const response = await saveNebiusAttackTemplate(attackScenario.id);
    setMessage(response.message);
    await refresh();
  }

  async function generateGrid() {
    const scenarios = await generateNebiusScenarioGrid(scenarioConfig, attackScenario?.id);
    setGeneratedScenarios(scenarios);
    setMessage(
      attackScenario
        ? `${attackScenario.id} expanded into ${scenarios.length} experiment-grid variants.`
        : `Generated ${scenarios.length} experiment-grid variants.`
    );
  }

  async function submitBatch(runs = batchConfig.numberOfRuns) {
    const response = await runSmartBatches(runs, batchConfig.agentsPerRun, scenariosFor(batchConfig));
    setJobs((current) => [jobFromBatch(response), ...current.filter((job) => job.id !== response.id)]);
    setMessage(`${response.id} completed on ${response.deployment_target}. Artifacts are available in Detection.`);
    await refresh();
  }

  return (
    <section className="attack-scenario-page">
      <div className="panel lab-hero-panel team-hero red">
        <TeamMark team="red" />
        <div>
          <p className="eyebrow">Red-team planning workspace</p>
          <h2>Attack Scenario Generator</h2>
          <p>Create concrete attack plans, persist them, inject them into Arena, expand them into experiment grids, or run them as Nebius Managed Experiment batches.</p>
        </div>
        <div className="team-hero-badges">
          <span className="team-badge red">Red Team</span>
          <span className="endpoint-badge">{storedScenarios.length} stored plans</span>
        </div>
      </div>

      {message ? <div className="empty-state">{message}</div> : null}

      <div className="attack-scenario-page-grid">
        <AttackScenarioGenerator
          input={attackInput}
          onChange={setAttackInput}
          onGenerate={() => void runAction(generateAttack)}
          onGenerateVariants={() => void runAction(generateVariants)}
          onInject={() => void runAction(injectScenario)}
          onRunBatch={() => void runAction(() => submitBatch(100))}
          onSaveTemplate={() => void runAction(saveTemplate)}
          onSelectScenario={selectAttackScenario}
          scenario={attackScenario}
          storedScenarios={storedScenarios}
          statusMessage={busy ? "Working with backend Nebius AI adapter..." : null}
          variants={attackVariants}
        />

        <ScenarioBatchGenerator
          config={scenarioConfig}
          onChange={setScenarioConfig}
          onGenerate={() => void runAction(generateGrid)}
          onRunSelected={() => void runAction(() => submitBatch(64))}
          scenarios={generatedScenarios}
        />

        <ServerlessRunnerCard
          busy={busy}
          config={batchConfig}
          jobs={jobs}
          onChange={setBatchConfig}
          onSubmit={() => void runAction(() => submitBatch())}
        />
      </div>
    </section>
  );
}

function jobsFromReports(reports: ReportsSummary): ServerlessExperimentJob[] {
  return (reports.nebius_batches ?? []).slice().reverse().map(jobFromRecord);
}

function jobFromBatch(batch: { id: string; runs: number; scenarios: string[]; metrics: Record<string, string>[]; status: string }): ServerlessExperimentJob {
  return jobFromRecord(batch as unknown as Record<string, unknown>);
}

function jobFromRecord(batch: Record<string, unknown>): ServerlessExperimentJob {
  const metrics = Array.isArray(batch.metrics) ? batch.metrics as Record<string, unknown>[] : [];
  const runs = Number(batch.runs ?? 0);
  const alerts = metrics.reduce((total, row) => total + Number(row.alerts ?? 0), 0);
  const precisionRows = metrics.map((row) => Number(row.precision ?? Number.NaN)).filter(Number.isFinite);
  const precision = precisionRows.length ? precisionRows.reduce((total, value) => total + value, 0) / precisionRows.length : undefined;
  return {
    alerts: alerts || undefined,
    estimatedCostUsd: Number((0.21 + runs * 0.004).toFixed(2)),
    id: String(batch.id ?? "JOB"),
    precision,
    runs,
    scenario: Array.isArray(batch.scenarios) ? batch.scenarios.join(", ") : String(batch.scenario ?? "Nebius batch"),
    status: batch.status === "failed" ? "failed" : batch.status === "queued" ? "queued" : batch.status === "running" ? "running" : "done"
  };
}

function scenariosFor(config: ExperimentBatchConfig) {
  const scenario = `${config.scenarioFamily} ${config.attackType}`.toLowerCase();
  if (scenario.includes("normal")) return ["normal_market"];
  if (scenario.includes("layer")) return ["layering"];
  if (scenario.includes("quote")) return ["quote_stuffing"];
  if (scenario.includes("mixed")) return ["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"];
  return ["spoofing"];
}

function displayAttackType(value: AttackScenario["attackType"]) {
  const mapping: Record<AttackScenario["attackType"], string> = {
    layering: "Layering",
    mixed: "Mixed",
    momentum_ignition: "Momentum Ignition",
    quote_stuffing: "Quote Stuffing",
    spoofing: "Spoofing"
  };
  return mapping[value];
}
