import type { GeneratedScenario, ScenarioGridConfig } from "@/features/nebius/types";

type ScenarioBatchGeneratorProps = {
  config: ScenarioGridConfig;
  scenarios: GeneratedScenario[];
  onChange: (config: ScenarioGridConfig) => void;
  onGenerate: () => void;
  onRunSelected: () => void;
};

export function ScenarioBatchGenerator({ config, onChange, onGenerate, onRunSelected, scenarios }: ScenarioBatchGeneratorProps) {
  return (
    <section className="panel scenario-generator-card">
      <div className="nebius-card-heading">
        <div>
          <p className="eyebrow">Experiment Grid</p>
          <h2>Scenario Batch Generator</h2>
        </div>
      </div>
      <p className="nebius-card-purpose">Generate experimental scenario grids for detector robustness testing.</p>
      <div className="scenario-generator-grid">
        <Select label="Market volatility" value={config.marketVolatility} options={["Low", "Medium", "High"]} onChange={(marketVolatility) => onChange({ ...config, marketVolatility: marketVolatility as ScenarioGridConfig["marketVolatility"] })} />
        <Select label="Liquidity" value={config.liquidity} options={["Thin", "Normal", "Deep"]} onChange={(liquidity) => onChange({ ...config, liquidity: liquidity as ScenarioGridConfig["liquidity"] })} />
        <Select label="Number of agents" value={String(config.numberOfAgents)} options={["10", "50", "100", "500"]} onChange={(numberOfAgents) => onChange({ ...config, numberOfAgents: Number(numberOfAgents) as ScenarioGridConfig["numberOfAgents"] })} />
        <Select label="Attack intensity" value={config.attackIntensity} options={["Subtle", "Medium", "Aggressive"]} onChange={(attackIntensity) => onChange({ ...config, attackIntensity: attackIntensity as ScenarioGridConfig["attackIntensity"] })} />
        <label className="form-row">
          Detection threshold
          <input max={1} min={0} onChange={(event) => onChange({ ...config, detectionThreshold: Number(event.target.value) })} step={0.01} type="range" value={config.detectionThreshold} />
          <span>{config.detectionThreshold.toFixed(2)}</span>
        </label>
        <Select label="Latency model" value={config.latencyModel} options={["None", "Random", "Agent-specific"]} onChange={(latencyModel) => onChange({ ...config, latencyModel: latencyModel as ScenarioGridConfig["latencyModel"] })} />
      </div>
      <div className="nebius-button-row">
        <button onClick={onGenerate} type="button">Generate 64 Experiments</button>
        <button onClick={onRunSelected} type="button">Run Selected on Nebius</button>
      </div>
      <div className="generated-scenario-list">
        {scenarios.map((scenario) => (
          <article key={scenario.id}>
            <span>{scenario.id}</span>
            <strong>{scenario.label}</strong>
          </article>
        ))}
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
