import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { runBenchmarkExperiment, type BenchmarkRunResponse } from "@/api/client";
import { BenchmarkTable } from "@/components/BenchmarkTable";
import type { BenchmarkResult } from "@/types/arena";

type JobStatus = "queued" | "running" | "generating report" | "completed";

const jobStatuses: JobStatus[] = ["queued", "running", "generating report", "completed"];
const marketRegimes = ["calm", "volatile", "thin liquidity"];
const scenarios = ["spoofing", "layering", "quote stuffing", "liquidity evaporation"];
const detectors = ["baseline", "tuned", "hybrid"];

const defaultBenchmarkRows: BenchmarkResult[] = [
  { avg_detection_latency_ms: 840, f1: 0.88, precision: 0.91, recall: 0.86, scenario: "Spoofing" },
  { avg_detection_latency_ms: 980, f1: 0.81, precision: 0.84, recall: 0.79, scenario: "Layering" },
  { avg_detection_latency_ms: 410, f1: 0.94, precision: 0.96, recall: 0.92, scenario: "Quote stuffing" },
  { avg_detection_latency_ms: 760, f1: 0.86, precision: 0.89, recall: 0.83, scenario: "Liquidity evaporation" }
];

export function ExperimentLabPage() {
  const [currentStatusIndex, setCurrentStatusIndex] = useState<number | null>(null);
  const [runs, setRuns] = useState("500");
  const [selectedDetector, setSelectedDetector] = useState("tuned");
  const [selectedRegime, setSelectedRegime] = useState("volatile");
  const [selectedScenarios, setSelectedScenarios] = useState(() => new Set(scenarios));
  const [benchmarkRows, setBenchmarkRows] = useState<BenchmarkResult[]>(defaultBenchmarkRows);
  const [jobRun, setJobRun] = useState<BenchmarkRunResponse | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const isJobRunning = currentStatusIndex !== null && currentStatusIndex < jobStatuses.length - 1;

  useEffect(() => {
    if (currentStatusIndex === null || currentStatusIndex >= jobStatuses.length - 1) {
      return undefined;
    }

    const handle = window.setTimeout(() => {
      setCurrentStatusIndex((index) => index === null ? null : Math.min(index + 1, jobStatuses.length - 1));
    }, 900);

    return () => window.clearTimeout(handle);
  }, [currentStatusIndex]);

  async function runJob() {
    if (isJobRunning || selectedScenarios.size === 0) {
      return;
    }
    setCurrentStatusIndex(0);
    setJobError(null);
    try {
      const response = await runBenchmarkExperiment({
        detectors: selectedDetector,
        market_regime: selectedRegime,
        runs: Number(runs),
        scenarios: Array.from(selectedScenarios)
      });
      setJobRun(response);
      setBenchmarkRows(response.results.length ? response.results : defaultBenchmarkRows);
      setCurrentStatusIndex(jobStatuses.length - 1);
    } catch (error) {
      setJobError(error instanceof Error ? error.message : "Benchmark run failed.");
      setCurrentStatusIndex(null);
    }
  }

  function toggleScenario(scenario: string) {
    setSelectedScenarios((current) => {
      const next = new Set(current);
      if (next.has(scenario)) {
        next.delete(scenario);
      } else {
        next.add(scenario);
      }
      return next;
    });
  }

  return (
    <section className="experiment-lab-page">
      <div className="panel lab-hero-panel">
        <div>
          <p className="eyebrow">Nebius Serverless Jobs</p>
          <h2>Experiment Lab</h2>
          <p>Configure a small synthetic batch benchmark and run it as a visible Nebius Serverless Job flow.</p>
        </div>
        <span className="endpoint-badge">Nebius Serverless AI Job</span>
      </div>
      <div className="lab-grid">
        <form className="panel experiment-form" onSubmit={(event) => { event.preventDefault(); void runJob(); }}>
          <h2>Batch Experiment</h2>

          <fieldset>
            <legend>Runs</legend>
            <div className="segmented-options">
              {["100", "500", "1000"].map((value) => (
                <label className={runs === value ? "selected" : ""} key={value}>
                  <input checked={runs === value} name="runs" onChange={() => setRuns(value)} type="radio" />
                  {value}
                </label>
              ))}
            </div>
          </fieldset>

          <label className="form-row">
            Market regime
            <select value={selectedRegime} onChange={(event) => setSelectedRegime(event.target.value)}>
              {marketRegimes.map((regime) => <option key={regime}>{regime}</option>)}
            </select>
          </label>

          <fieldset>
            <legend>Scenarios</legend>
            <div className="checkbox-grid">
              {scenarios.map((scenario) => (
                <label key={scenario}>
                  <input checked={selectedScenarios.has(scenario)} onChange={() => toggleScenario(scenario)} type="checkbox" />
                  {scenario}
                </label>
              ))}
            </div>
          </fieldset>

          <label className="form-row">
            Detector
            <select value={selectedDetector} onChange={(event) => setSelectedDetector(event.target.value)}>
              {detectors.map((detector) => <option key={detector}>{detector}</option>)}
            </select>
          </label>

          <button disabled={isJobRunning || selectedScenarios.size === 0} type="submit">
            {isJobRunning ? "Running Serverless Job..." : "Run on Nebius Serverless Job"}
          </button>
          {jobRun ? <p className="lab-job-note">Recorded run {jobRun.id}. Artifacts: {Object.values(jobRun.artifact_paths).join(", ")}</p> : null}
          {jobError ? <p className="lab-job-note error">{jobError}</p> : null}
        </form>

        <section className="panel job-status-panel">
          <h2>Job Status</h2>
          <p className="mock-endpoint">
            {jobRun ? jobRun.command.join(" ") : `serverless.jobs.run_batch_benchmark --runs ${runs} --detector ${selectedDetector} --regime ${selectedRegime}`}
          </p>
          <p className="lab-job-note">
            Job purpose: detector tournament benchmark plus bounded synthetic dataset generation. Keep run counts small
            while testing real Nebius wiring.
          </p>
          <ol className="job-status-timeline">
            {jobStatuses.map((status, index) => (
              <li className={getStatusClass(index, currentStatusIndex)} key={status}>
                <span>{status}</span>
              </li>
            ))}
          </ol>
        </section>

        <section className="panel benchmark-results-panel">
          <BenchmarkTable rows={benchmarkRows} />
        </section>

        <section className="panel f1-chart-panel">
          <h2>F1 by Scenario</h2>
          <div className="f1-chart-frame">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={benchmarkRows} margin={{ top: 10, right: 12, bottom: 8, left: -18 }}>
                <CartesianGrid stroke="rgba(148, 163, 184, 0.16)" strokeDasharray="3 3" />
                <XAxis dataKey="scenario" tick={{ fill: "#8fb7c9", fontSize: 11 }} />
                <YAxis domain={[0, 1]} tick={{ fill: "#8fb7c9", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#071426", borderColor: "#1e3a5f", color: "#d8f3ff" }} />
                <Bar dataKey="f1" fill="#22d3ee" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
    </section>
  );
}

function getStatusClass(index: number, currentStatusIndex: number | null) {
  if (currentStatusIndex === null) {
    return "pending";
  }
  if (index < currentStatusIndex) {
    return "completed";
  }
  if (index === currentStatusIndex) {
    return "active";
  }
  return "pending";
}
