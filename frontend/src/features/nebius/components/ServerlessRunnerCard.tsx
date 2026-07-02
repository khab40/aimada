import type { ExperimentBatchConfig, ServerlessExperimentJob } from "@/features/nebius/types";

type ServerlessRunnerCardProps = {
  config: ExperimentBatchConfig;
  jobs: ServerlessExperimentJob[];
  onChange: (config: ExperimentBatchConfig) => void;
  onSubmit: () => void;
  busy: boolean;
};

const scenarioFamilies = ["Normal Market", "Spoofing Attack", "Layering Attack", "Quote Stuffing", "Mixed Abuse Scenario"];
const attackTypes = ["Spoofing", "Layering", "Quote Stuffing", "Mixed"];
const detectors = ["Rule-based", "Isolation Forest placeholder", "AI Investigator placeholder"];

export function ServerlessRunnerCard({ busy, config, jobs, onChange, onSubmit }: ServerlessRunnerCardProps) {
  return (
    <section className="panel serverless-runner-card">
      <div className="nebius-card-heading">
        <div>
          <p className="eyebrow">Managed Experiment</p>
          <h2>Managed Experiment Runner</h2>
        </div>
        <button disabled={busy} onClick={onSubmit} type="button">Run Managed Experiment</button>
      </div>
      <p className="nebius-card-purpose">Run many simulation scenarios in parallel using Nebius Managed Experiment jobs.</p>
      <div className="serverless-config-grid">
        <Select label="Scenario family" value={config.scenarioFamily} options={scenarioFamilies} onChange={(scenarioFamily) => onChange({ ...config, scenarioFamily })} />
        <NumberInput label="Number of runs" value={config.numberOfRuns} onChange={(numberOfRuns) => onChange({ ...config, numberOfRuns })} />
        <NumberInput label="Agents per run" value={config.agentsPerRun} onChange={(agentsPerRun) => onChange({ ...config, agentsPerRun })} />
        <Select label="Attack type" value={config.attackType} options={attackTypes} onChange={(attackType) => onChange({ ...config, attackType })} />
        <Select label="Detector" value={config.detector} options={detectors} onChange={(detector) => onChange({ ...config, detector })} />
      </div>
      <fieldset className="serverless-output-options">
        <legend>Output</legend>
        {[
          ["storeReplay", "Store replay"],
          ["storeMetrics", "Store metrics"],
          ["storeAlerts", "Store alerts"],
          ["generateIncidentReport", "Generate incident report"]
        ].map(([key, label]) => (
          <label key={key}>
            <input
              checked={Boolean(config.outputs[key as keyof ExperimentBatchConfig["outputs"]])}
              onChange={(event) => onChange({ ...config, outputs: { ...config.outputs, [key]: event.target.checked } })}
              type="checkbox"
            />
            {label}
          </label>
        ))}
      </fieldset>
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
          {jobs.map((job) => (
            <tr key={job.id}>
              <td>{job.id}</td>
              <td>{job.scenario}</td>
              <td>{job.runs}</td>
              <td><span className={`job-status ${job.status}`}>{job.status}</span></td>
              <td>{job.alerts ?? "-"}</td>
              <td>{job.precision === undefined ? "-" : job.precision.toFixed(2)}</td>
              <td>{job.estimatedCostUsd === undefined ? "-" : `$${job.estimatedCostUsd.toFixed(2)}`}</td>
            </tr>
          ))}
        </tbody>
      </table>
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

function NumberInput({ label, onChange, value }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="form-row">
      {label}
      <input min={1} onChange={(event) => onChange(Number(event.target.value))} type="number" value={value} />
    </label>
  );
}
