import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
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

const attackTypes: AttackScenarioInput["attackType"][] = ["Spoofing", "Layering", "Quote Stuffing", "Momentum Ignition", "Mixed Attack"];
const marketConditions: AttackScenarioInput["marketCondition"][] = ["Thin liquidity", "Normal liquidity", "High volatility", "News shock", "Low activity period"];
const objectives: AttackScenarioInput["objective"][] = ["Buy cheaper", "Sell higher", "Trigger stop-loss cascade", "Distort visible liquidity", "Test detector weakness"];
const stealthLevels: AttackScenarioInput["stealthLevel"][] = ["Obvious", "Medium", "Subtle"];
const durations: AttackScenarioInput["attackDuration"][] = ["Short", "Medium", "Long"];
const redTeamAgentCounts: AttackScenarioInput["redTeamAgentCount"][] = [1, 2, 5, 10];
const scenarioFamilies = ["Normal Market", "Spoofing Attack", "Layering Attack", "Quote Stuffing", "Mixed Abuse Scenario"];
const batchAttackTypes = ["Spoofing", "Layering", "Quote Stuffing", "Mixed"];
const detectorProfiles = [
  { detector: "Rule-based", difficulty: "Medium", label: "Rule-based wall detector" },
  { detector: "Rule-based", difficulty: "Hard", label: "Layering sequence detector" },
  { detector: "Rule-based", difficulty: "Hard", label: "Cross-agent trade pattern" },
  { detector: "Rule-based", difficulty: "Medium", label: "Message-rate detector" },
  { detector: "AI Investigator", difficulty: "Hard", label: "AI Investigator triage" }
] as const;

type ReusableScenarioTemplate = {
  attackInput: Partial<AttackScenarioInput>;
  batchAttackType: string;
  detectorProfile: string;
  difficulty: string;
  duration: string;
  key: string;
  market: string;
  scenarioFamily: string;
  title: string;
};

const reusableScenarioTemplates: ReusableScenarioTemplate[] = [
  {
    attackInput: { attackType: "Spoofing", detectorDifficulty: "Medium", marketCondition: "Thin liquidity", stealthLevel: "Medium" },
    batchAttackType: "Spoofing",
    detectorProfile: "Rule-based wall detector",
    difficulty: "Medium",
    duration: "Medium",
    key: "spoofing",
    market: "Thin liquidity",
    scenarioFamily: "Spoofing Attack",
    title: "spoofing"
  },
  {
    attackInput: { attackType: "Layering", detectorDifficulty: "Hard", marketCondition: "High volatility", stealthLevel: "Subtle" },
    batchAttackType: "Layering",
    detectorProfile: "Layering sequence detector",
    difficulty: "Hard",
    duration: "Long",
    key: "layering",
    market: "High volatility",
    scenarioFamily: "Layering Attack",
    title: "layering"
  },
  {
    attackInput: { attackType: "Mixed Attack", detectorDifficulty: "Hard", marketCondition: "Normal liquidity", objective: "Test detector weakness" },
    batchAttackType: "Mixed",
    detectorProfile: "Cross-agent trade pattern",
    difficulty: "Hard",
    duration: "Medium",
    key: "wash_trading",
    market: "Normal liquidity",
    scenarioFamily: "Mixed Abuse Scenario",
    title: "wash trading"
  },
  {
    attackInput: { attackType: "Quote Stuffing", detectorDifficulty: "Medium", marketCondition: "Low activity period", stealthLevel: "Obvious" },
    batchAttackType: "Quote Stuffing",
    detectorProfile: "Message-rate detector",
    difficulty: "Medium",
    duration: "Short",
    key: "quote_stuffing",
    market: "Low activity period",
    scenarioFamily: "Quote Stuffing",
    title: "quote stuffing"
  }
];

export function AttackScenarioGeneratorPage() {
  const [searchParams] = useSearchParams();
  const appliedDemoScenarioRef = useRef<string | null>(null);
  const [attackInput, setAttackInput] = useState<AttackScenarioInput>(initialAttackInput);
  const [attackScenario, setAttackScenario] = useState<AttackScenario | null>(null);
  const [attackVariants, setAttackVariants] = useState<AttackScenario[]>([]);
  const [batchConfig, setBatchConfig] = useState<ExperimentBatchConfig>(initialBatchConfig);
  const [busy, setBusy] = useState(false);
  const [detectorProfile, setDetectorProfile] = useState<string>(detectorProfiles[0].label);
  const [generatedScenarios, setGeneratedScenarios] = useState<GeneratedScenario[]>([]);
  const [jobs, setJobs] = useState<ServerlessExperimentJob[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [arenaRunReady, setArenaRunReady] = useState(false);
  const [scenarioConfig, setScenarioConfig] = useState<ScenarioGridConfig>(initialScenarioConfig);
  const [storedScenarios, setStoredScenarios] = useState<AttackScenario[]>([]);

  useEffect(() => {
    void refresh();
    void generateNebiusScenarioGrid(initialScenarioConfig).then(setGeneratedScenarios).catch(() => undefined);
  }, []);

  useEffect(() => {
    const demoScenario = searchParams.get("demoScenario");
    const attackKey = searchParams.get("attack");
    if (!demoScenario || appliedDemoScenarioRef.current === demoScenario) return;
    const template = reusableScenarioTemplates.find((item) => item.key === attackKey) ?? reusableScenarioTemplates[0];
    appliedDemoScenarioRef.current = demoScenario;
    applyScenarioTemplate(template);
    setMessage(`${template.title} demo scenario loaded. Start here, then continue to Arena and Nebius AI.`);
    // Demo query params intentionally load once per scenario id.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

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
    setArenaRunReady(false);
    setBatchConfig((current) => ({
      ...current,
      attackType: displayAttackType(scenario.attackType),
      scenarioFamily: scenario.name,
      sourceAttackScenarioId: scenario.id
    }));
    setMessage(`${scenario.id} selected as the source attack plan for grids and Nebius batches.`);
  }

  function applyScenarioTemplate(template: ReusableScenarioTemplate) {
    applyDetectorProfile(template.detectorProfile);
    setAttackInput((current) => ({
      ...current,
      ...template.attackInput,
      attackDuration: template.duration as AttackScenarioInput["attackDuration"]
    }));
    setBatchConfig((current) => ({
      ...current,
      attackType: template.batchAttackType,
      detector: "Rule-based",
      scenarioFamily: template.scenarioFamily
    }));
    setArenaRunReady(false);
    setMessage(`${template.title} template loaded. Generate the scenario, then run it in Arena.`);
  }

  function applyDetectorProfile(label: string) {
    const profile = detectorProfiles.find((item) => item.label === label) ?? detectorProfiles[0];
    setDetectorProfile(profile.label);
    setAttackInput((current) => ({
      ...current,
      detectorDifficulty: profile.difficulty as AttackScenarioInput["detectorDifficulty"]
    }));
    setBatchConfig((current) => ({
      ...current,
      detector: profile.detector
    }));
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
    setArenaRunReady(false);
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
    setArenaRunReady(false);
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
    setArenaRunReady(true);
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
          <h2>Attack Scenario Generator</h2>
        </div>
      </div>

      {message ? <div className="empty-state">{message}</div> : null}

      <div className="scenario-wizard panel">
        <div className="scenario-wizard-header">
          <div>
            <h2>Market / Attack / Detector / Execution</h2>
          </div>
          {busy ? <span className="endpoint-badge">Working with Nebius AI...</span> : null}
        </div>

        <section className="scenario-wizard-step">
          <div className="scenario-step-heading">
            <span>1</span>
            <div>
              <h3>Market</h3>
            </div>
          </div>
          <div className="scenario-control-grid">
            <Select label="Market condition" value={attackInput.marketCondition} options={marketConditions} onChange={(marketCondition) => setAttackInput({ ...attackInput, marketCondition: marketCondition as AttackScenarioInput["marketCondition"] })} />
            <Select label="Market volatility" value={scenarioConfig.marketVolatility} options={["Low", "Medium", "High"]} onChange={(marketVolatility) => setScenarioConfig({ ...scenarioConfig, marketVolatility: marketVolatility as ScenarioGridConfig["marketVolatility"] })} />
            <Select label="Liquidity" value={scenarioConfig.liquidity} options={["Thin", "Normal", "Deep"]} onChange={(liquidity) => setScenarioConfig({ ...scenarioConfig, liquidity: liquidity as ScenarioGridConfig["liquidity"] })} />
            <Select label="Agents in market" value={String(scenarioConfig.numberOfAgents)} options={["10", "50", "100", "500"]} onChange={(numberOfAgents) => setScenarioConfig({ ...scenarioConfig, numberOfAgents: Number(numberOfAgents) as ScenarioGridConfig["numberOfAgents"] })} />
          </div>
        </section>

        <section className="scenario-wizard-step">
          <div className="scenario-step-heading">
            <span>2</span>
            <div>
              <h3>Attack</h3>
            </div>
          </div>
          <div className="scenario-control-grid">
            <Select label="Attack type" value={attackInput.attackType} options={attackTypes} onChange={(attackType) => setAttackInput({ ...attackInput, attackType: attackType as AttackScenarioInput["attackType"] })} />
            <Select label="Attacker objective" value={attackInput.objective} options={objectives} onChange={(objective) => setAttackInput({ ...attackInput, objective: objective as AttackScenarioInput["objective"] })} />
            <Select label="Stealth level" value={attackInput.stealthLevel} options={stealthLevels} onChange={(stealthLevel) => setAttackInput({ ...attackInput, stealthLevel: stealthLevel as AttackScenarioInput["stealthLevel"] })} />
            <Select label="Attack duration" value={attackInput.attackDuration} options={durations} onChange={(attackDuration) => setAttackInput({ ...attackInput, attackDuration: attackDuration as AttackScenarioInput["attackDuration"] })} />
            <Select label="Red-team agents" value={String(attackInput.redTeamAgentCount)} options={redTeamAgentCounts.map(String)} onChange={(redTeamAgentCount) => setAttackInput({ ...attackInput, redTeamAgentCount: Number(redTeamAgentCount) as AttackScenarioInput["redTeamAgentCount"] })} />
            <Select label="Attack intensity" value={scenarioConfig.attackIntensity} options={["Subtle", "Medium", "Aggressive"]} onChange={(attackIntensity) => setScenarioConfig({ ...scenarioConfig, attackIntensity: attackIntensity as ScenarioGridConfig["attackIntensity"] })} />
          </div>
          <div className="nebius-button-row">
            {!attackScenario ? (
              <button className="scenario-primary-action" onClick={() => void runAction(generateAttack)} type="button">Generate</button>
            ) : (
              <button className="scenario-primary-action" disabled={busy} onClick={() => void runAction(injectScenario)} type="button">Run in Arena</button>
            )}
            {attackScenario ? <button onClick={() => void runAction(generateAttack)} type="button">Generate New</button> : null}
            <button onClick={() => void runAction(generateVariants)} type="button">Generate 10 Variants</button>
            {arenaRunReady ? <Link className="primary-link-button" to="/arena">Open Arena</Link> : null}
            <button disabled={!attackScenario} onClick={() => void runAction(saveTemplate)} type="button">Save Template</button>
          </div>
          <details className="scenario-advanced-panel">
            <summary>Attack plan and stored scenarios</summary>
            <div className="attack-plan-layout">
              <AttackPlanPreview scenario={attackScenario} />
              <ScenarioPicker
                scenario={attackScenario}
                storedScenarios={storedScenarios}
                variants={attackVariants}
                templates={reusableScenarioTemplates}
                onApplyTemplate={applyScenarioTemplate}
                onSelectScenario={selectAttackScenario}
              />
            </div>
          </details>
        </section>

        <section className="scenario-wizard-step">
          <div className="scenario-step-heading">
            <span>3</span>
            <div>
              <h3>Detector</h3>
            </div>
          </div>
          <div className="scenario-control-grid">
            <Select label="Detector profile" value={detectorProfile} options={detectorProfiles.map((profile) => profile.label)} onChange={applyDetectorProfile} />
          </div>
        </section>

        <section className="scenario-wizard-step">
          <div className="scenario-step-heading">
            <span>4</span>
            <div>
              <h3>Execution</h3>
            </div>
          </div>
          <div className="scenario-control-grid">
            <Select label="Scenario family" value={batchConfig.scenarioFamily} options={scenarioFamilies} onChange={(scenarioFamily) => setBatchConfig({ ...batchConfig, scenarioFamily })} />
            <Select label="Batch attack type" value={batchConfig.attackType} options={batchAttackTypes} onChange={(attackType) => setBatchConfig({ ...batchConfig, attackType })} />
            <NumberInput label="Number of runs" value={batchConfig.numberOfRuns} onChange={(numberOfRuns) => setBatchConfig({ ...batchConfig, numberOfRuns })} />
            <NumberInput label="Agents per run" value={batchConfig.agentsPerRun} onChange={(agentsPerRun) => setBatchConfig({ ...batchConfig, agentsPerRun })} />
          </div>
          <fieldset className="serverless-output-options">
            <legend>Outputs</legend>
            {[
              ["storeReplay", "Store replay"],
              ["storeMetrics", "Store metrics"],
              ["storeAlerts", "Store alerts"],
              ["generateIncidentReport", "Generate incident report"]
            ].map(([key, label]) => (
              <label key={key}>
                <input
                  checked={Boolean(batchConfig.outputs[key as keyof ExperimentBatchConfig["outputs"]])}
                  onChange={(event) => setBatchConfig({ ...batchConfig, outputs: { ...batchConfig.outputs, [key]: event.target.checked } })}
                  type="checkbox"
                />
                {label}
              </label>
            ))}
          </fieldset>
          <div className="nebius-button-row">
            <button onClick={() => void runAction(generateGrid)} type="button">Generate Experiment Grid</button>
            <button onClick={() => void runAction(() => submitBatch(64))} type="button">Run Grid on Nebius</button>
            <button disabled={busy} onClick={() => void runAction(() => submitBatch())} type="button">Run Managed Experiment</button>
          </div>
          <details className="scenario-advanced-panel">
            <summary>Generated scenarios and jobs</summary>
            <div className="scenario-execution-output">
              <div className="generated-scenario-list">
                {generatedScenarios.length ? generatedScenarios.map((scenario) => (
                  <ScenarioCard
                    key={scenario.id}
                    badge={scenario.id}
                    metadata={metadataFromGeneratedScenario(scenario, scenarioConfig, batchConfig)}
                    title={scenario.label}
                  />
                )) : <p className="empty-state">No experiment-grid scenarios generated yet.</p>}
              </div>
              <JobTable jobs={jobs} />
            </div>
          </details>
        </section>
      </div>
    </section>
  );
}

function AttackPlanPreview({ scenario }: { scenario: AttackScenario | null }) {
  if (!scenario) {
    return <p className="empty-state">Generate an attack scenario to preview its structured plan.</p>;
  }

  return (
    <div className="attack-plan-preview">
      <div className="attack-plan-header">
        <strong>{scenario.id}</strong>
        <span>{scenario.name}</span>
      </div>
      <dl className="attack-plan-meta">
        <div><dt>Type</dt><dd>{scenario.attackType}</dd></div>
        <div><dt>Target</dt><dd>{scenario.targetSide}</dd></div>
        <div><dt>Agents</dt><dd>{scenario.redTeamAgents.join(", ")}</dd></div>
        <div><dt>Duration</dt><dd>{scenario.durationTicks} ticks</dd></div>
        <div><dt>Stealth</dt><dd>{scenario.stealthLevel}</dd></div>
        <div><dt>Difficulty</dt><dd>{scenario.expectedDetectorDifficulty}</dd></div>
      </dl>
      <p>{scenario.objective}</p>
      <h3>Expected Signals</h3>
      <ul>{scenario.expectedSignals.map((signal) => <li key={signal}>{signal}</li>)}</ul>
      <h3>Plan Steps</h3>
      <ol>{scenario.planSteps.map((step) => <li key={step}>{step}</li>)}</ol>
    </div>
  );
}

function ScenarioPicker({
  onApplyTemplate,
  onSelectScenario,
  scenario,
  storedScenarios,
  templates,
  variants
}: {
  onApplyTemplate: (template: ReusableScenarioTemplate) => void;
  onSelectScenario: (scenario: AttackScenario) => void;
  scenario: AttackScenario | null;
  storedScenarios: AttackScenario[];
  templates: ReusableScenarioTemplate[];
  variants: AttackScenario[];
}) {
  return (
    <div className="attack-variant-list">
      <h3>Reusable Scenarios</h3>
      <div className="reusable-scenario-grid">
        {templates.map((template) => (
          <ScenarioCard
            active={batchConfigMatchesTemplate(template, scenario)}
            badge="Template"
            key={template.key}
            metadata={{
              detectorProfile: template.detectorProfile,
              difficulty: template.difficulty,
              duration: template.duration,
              market: template.market
            }}
            onClick={() => onApplyTemplate(template)}
            title={template.title}
          />
        ))}
      </div>

      <h3>Stored Scenarios</h3>
      <div className="reusable-scenario-grid">
        {storedScenarios.length ? storedScenarios.map((stored) => (
          <ScenarioCard
            active={scenario?.id === stored.id}
            badge={stored.id}
            key={stored.id}
            metadata={metadataFromAttackScenario(stored)}
            onClick={() => onSelectScenario(stored)}
            title={scenarioCardTitle(stored)}
          />
        )) : <p className="empty-state">No persisted scenarios yet.</p>}
      </div>

      <h3>Generated Variants</h3>
      <div className="reusable-scenario-grid">
        {variants.length ? variants.map((variant) => (
          <ScenarioCard
            active={scenario?.id === variant.id}
            badge={variant.id}
            key={variant.id}
            metadata={metadataFromAttackScenario(variant)}
            onClick={() => onSelectScenario(variant)}
            title={scenarioCardTitle(variant)}
          />
        )) : <p className="empty-state">No variants generated yet.</p>}
      </div>
    </div>
  );
}

type ScenarioCardMetadata = {
  detectorProfile: string;
  difficulty: string;
  duration: string;
  market: string;
};

function ScenarioCard({
  active = false,
  badge,
  metadata,
  onClick,
  title
}: {
  active?: boolean;
  badge: string;
  metadata: ScenarioCardMetadata;
  onClick?: () => void;
  title: string;
}) {
  const content = (
    <>
      <div className="reusable-scenario-header">
        <strong>{title}</strong>
        <span>{badge}</span>
      </div>
      <dl className="reusable-scenario-meta">
        <div><dt>Difficulty</dt><dd>{metadata.difficulty}</dd></div>
        <div><dt>Duration</dt><dd>{metadata.duration}</dd></div>
        <div><dt>Market</dt><dd>{metadata.market}</dd></div>
        <div><dt>Detector profile</dt><dd>{metadata.detectorProfile}</dd></div>
      </dl>
    </>
  );

  if (onClick) {
    return (
      <button className={active ? "reusable-scenario-card selected" : "reusable-scenario-card"} onClick={onClick} type="button">
        {content}
      </button>
    );
  }

  return <article className="reusable-scenario-card">{content}</article>;
}

function scenarioCardTitle(scenario: AttackScenario) {
  const mapping: Record<AttackScenario["attackType"], string> = {
    layering: "layering",
    mixed: "wash trading",
    momentum_ignition: "momentum ignition",
    quote_stuffing: "quote stuffing",
    spoofing: "spoofing"
  };
  return mapping[scenario.attackType];
}

function metadataFromAttackScenario(scenario: AttackScenario): ScenarioCardMetadata {
  return {
    detectorProfile: `${scenario.expectedDetectorDifficulty} detector`,
    difficulty: sentenceCase(scenario.expectedDetectorDifficulty),
    duration: `${scenario.durationTicks} ticks`,
    market: scenario.marketRegime || "Synthetic market"
  };
}

function metadataFromGeneratedScenario(
  scenario: GeneratedScenario,
  config: ScenarioGridConfig,
  batchConfig: ExperimentBatchConfig
): ScenarioCardMetadata {
  return {
    detectorProfile: `${batchConfig.detector}, threshold ${config.detectionThreshold.toFixed(2)}`,
    difficulty: config.attackIntensity,
    duration: `${batchConfig.numberOfRuns} runs`,
    market: `${config.marketVolatility} volatility / ${config.liquidity} liquidity`
  };
}

function batchConfigMatchesTemplate(template: ReusableScenarioTemplate, scenario: AttackScenario | null) {
  if (!scenario) return false;
  return scenarioCardTitle(scenario) === template.title;
}

function sentenceCase(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function JobTable({ jobs }: { jobs: ServerlessExperimentJob[] }) {
  return (
    <div className="report-table-wrap">
      <table className="benchmark-table compact-job-table">
        <thead>
          <tr>
            <th>Job</th>
            <th>Scenario</th>
            <th>Runs</th>
            <th>Status</th>
            <th>Alerts</th>
            <th>Precision</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {jobs.length ? jobs.map((job) => (
            <tr key={job.id}>
              <td>{job.id}</td>
              <td>{job.scenario}</td>
              <td>{job.runs}</td>
              <td><span className={`job-status ${job.status}`}>{job.status}</span></td>
              <td>{job.alerts ?? "-"}</td>
              <td>{job.precision === undefined ? "-" : job.precision.toFixed(2)}</td>
              <td>{job.estimatedCostUsd === undefined ? "-" : `$${job.estimatedCostUsd.toFixed(2)}`}</td>
            </tr>
          )) : (
            <tr>
              <td colSpan={7}>No managed experiment jobs yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function Select({ label, onChange, options, value }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="form-row">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => <option key={option}>{option}</option>)}
      </select>
    </label>
  );
}

function NumberInput({ label, onChange, value }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="form-row">
      {label}
      <input min={1} onChange={(event) => onChange(Number(event.target.value))} type="number" value={value} />
    </label>
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
