import type { AttackScenario, AttackScenarioInput } from "@/features/nebius/types";

type AttackScenarioGeneratorProps = {
  input: AttackScenarioInput;
  scenario: AttackScenario | null;
  storedScenarios: AttackScenario[];
  variants: AttackScenario[];
  statusMessage: string | null;
  onChange: (input: AttackScenarioInput) => void;
  onGenerate: () => void;
  onGenerateVariants: () => void;
  onInject: () => void;
  onRunBatch: () => void;
  onSaveTemplate: () => void;
  onSelectScenario: (scenario: AttackScenario) => void;
};

const attackTypes: AttackScenarioInput["attackType"][] = ["Spoofing", "Layering", "Quote Stuffing", "Momentum Ignition", "Mixed Attack"];
const marketConditions: AttackScenarioInput["marketCondition"][] = ["Thin liquidity", "Normal liquidity", "High volatility", "News shock", "Low activity period"];
const objectives: AttackScenarioInput["objective"][] = ["Buy cheaper", "Sell higher", "Trigger stop-loss cascade", "Distort visible liquidity", "Test detector weakness"];
const stealthLevels: AttackScenarioInput["stealthLevel"][] = ["Obvious", "Medium", "Subtle"];
const durations: AttackScenarioInput["attackDuration"][] = ["Short", "Medium", "Long"];
const redTeamAgentCounts: AttackScenarioInput["redTeamAgentCount"][] = [1, 2, 5, 10];
const detectorDifficulties: AttackScenarioInput["detectorDifficulty"][] = ["Easy", "Medium", "Hard"];

export function AttackScenarioGenerator({
  input,
  onChange,
  onGenerate,
  onGenerateVariants,
  onInject,
  onRunBatch,
  onSaveTemplate,
  onSelectScenario,
  scenario,
  storedScenarios,
  statusMessage,
  variants
}: AttackScenarioGeneratorProps) {
  return (
    <section className="panel attack-scenario-generator-card">
      <div className="nebius-card-heading">
        <div>
          <p className="eyebrow">Red-Team Attack Plan</p>
          <h2>Attack Scenario Generator</h2>
        </div>
      </div>
      <p className="nebius-card-purpose">
        Create concrete red-team attack plans that can be injected into the live simulator or submitted to Nebius Serverless Jobs.
      </p>

      <div className="attack-generator-grid">
        <Select label="Attack type" value={input.attackType} options={attackTypes} onChange={(attackType) => onChange({ ...input, attackType: attackType as AttackScenarioInput["attackType"] })} />
        <Select label="Market condition" value={input.marketCondition} options={marketConditions} onChange={(marketCondition) => onChange({ ...input, marketCondition: marketCondition as AttackScenarioInput["marketCondition"] })} />
        <Select label="Attacker objective" value={input.objective} options={objectives} onChange={(objective) => onChange({ ...input, objective: objective as AttackScenarioInput["objective"] })} />
        <Select label="Stealth level" value={input.stealthLevel} options={stealthLevels} onChange={(stealthLevel) => onChange({ ...input, stealthLevel: stealthLevel as AttackScenarioInput["stealthLevel"] })} />
        <Select label="Attack duration" value={input.attackDuration} options={durations} onChange={(attackDuration) => onChange({ ...input, attackDuration: attackDuration as AttackScenarioInput["attackDuration"] })} />
        <Select label="Red-team agents" value={String(input.redTeamAgentCount)} options={redTeamAgentCounts.map(String)} onChange={(redTeamAgentCount) => onChange({ ...input, redTeamAgentCount: Number(redTeamAgentCount) as AttackScenarioInput["redTeamAgentCount"] })} />
        <Select label="Detector difficulty" value={input.detectorDifficulty} options={detectorDifficulties} onChange={(detectorDifficulty) => onChange({ ...input, detectorDifficulty: detectorDifficulty as AttackScenarioInput["detectorDifficulty"] })} />
      </div>

      <div className="nebius-button-row">
        <button onClick={onGenerate} type="button">Generate Attack Scenario</button>
        <button onClick={onGenerateVariants} type="button">Generate 10 Variants</button>
        <button disabled={!scenario} onClick={onInject} type="button">Inject Into Live Simulation</button>
        <button disabled={!scenario} onClick={onRunBatch} type="button">Run as Batch on Nebius</button>
        <button disabled={!scenario} onClick={onSaveTemplate} type="button">Save Scenario Template</button>
      </div>

      {statusMessage ? <p className="artifact-action-message">{statusMessage}</p> : null}

      <div className="attack-plan-layout">
        <div className="attack-plan-preview">
          {scenario ? (
            <>
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
            </>
          ) : (
            <p className="empty-state">Generate an attack scenario to preview its structured plan.</p>
          )}
        </div>

        <div className="attack-variant-list">
          <h3>Stored Scenarios</h3>
          {storedScenarios.length ? storedScenarios.map((stored) => (
            <button
              className={scenario?.id === stored.id ? "attack-scenario-select selected" : "attack-scenario-select"}
              key={stored.id}
              onClick={() => onSelectScenario(stored)}
              type="button"
            >
              <strong>{stored.id}</strong>
              <span>{stored.name}</span>
              <em>{stored.attackType}</em>
            </button>
          )) : <p className="empty-state">No persisted scenarios yet.</p>}

          <h3>Generated Variants</h3>
          {variants.length ? variants.map((variant) => (
            <button
              className={scenario?.id === variant.id ? "attack-scenario-select selected" : "attack-scenario-select"}
              key={variant.id}
              onClick={() => onSelectScenario(variant)}
              type="button"
            >
              <strong>{variant.id}</strong>
              <span>{variant.name}</span>
              <em>{variant.expectedDetectorDifficulty}</em>
            </button>
          )) : <p className="empty-state">No variants generated yet.</p>}
        </div>
      </div>
    </section>
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
