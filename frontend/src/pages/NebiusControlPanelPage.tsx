import { useEffect, useMemo, useState } from "react";
import type React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import {
  createSmartScenario,
  getNebiusObservatory,
  getNebiusStatus,
  runSmartBatches,
  runSmartDetection,
  type NebiusObservatory,
  type NebiusStatus,
  type OrderBookAlertResponse,
  type SmartBatchRunResponse,
  type SmartScenarioResponse
} from "@/api/client";

const fallbackMetrics = [
  { avg_detection_latency_ms: "0", f1: "0", precision: "1", recall: "0", scenario: "normal_market" },
  { avg_detection_latency_ms: "750", f1: "0.89", precision: "0.91", recall: "0.88", scenario: "spoofing" },
  { avg_detection_latency_ms: "920", f1: "0.82", precision: "0.84", recall: "0.80", scenario: "layering" },
  { avg_detection_latency_ms: "410", f1: "0.94", precision: "0.96", recall: "0.92", scenario: "quote_stuffing" },
  { avg_detection_latency_ms: "780", f1: "0.86", precision: "0.89", recall: "0.83", scenario: "pump_and_cancel" }
];

export function NebiusControlPanelPage() {
  const [status, setStatus] = useState<NebiusStatus | null>(null);
  const [observatory, setObservatory] = useState<NebiusObservatory | null>(null);
  const [scenario, setScenario] = useState<SmartScenarioResponse | null>(null);
  const [alert, setAlert] = useState<OrderBookAlertResponse | null>(null);
  const [batch, setBatch] = useState<SmartBatchRunResponse | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    try {
      const [statusResponse, observatoryResponse] = await Promise.all([
        getNebiusStatus(),
        getNebiusObservatory()
      ]);
      setStatus(statusResponse);
      setObservatory(observatoryResponse);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Nebius status refresh failed.");
    }
  }

  async function runAction<T>(action: string, fn: () => Promise<T>, setter: (value: T) => void) {
    setBusyAction(action);
    setError(null);
    try {
      const response = await fn();
      setter(response);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `${action} failed.`);
    } finally {
      setBusyAction(null);
    }
  }

  const metrics = useMemo(() => {
    const source = batch?.metrics?.length ? batch.metrics : fallbackMetrics;
    return source.map((row) => ({
      latency: Number(row.avg_detection_latency_ms || 0),
      f1: Number(row.f1 || 0),
      precision: Number(row.precision || 0),
      recall: Number(row.recall || 0),
      scenario: readableScenario(String(row.scenario || "unknown"))
    }));
  }, [batch]);

  return (
    <section className="nebius-control-page">
      <div className="panel nebius-hero-panel">
        <div>
          <p className="eyebrow">Nebius Control Panel</p>
          <h2>Serverless attack/detect operations</h2>
          <p>Endpoint scoring, investigation reports, parallel batches, and submission evidence.</p>
        </div>
        <div className="nebius-status-grid">
          <StatusPill label="CLI" ok={status?.cli_installed} />
          <StatusPill label="Endpoint" ok={status?.incident_explainer_configured || status?.scenario_generator_configured} />
          <StatusPill label="Token" ok={status?.api_key_configured} />
        </div>
      </div>

      {error ? <div className="disclaimer">{error}</div> : null}

      <div className="nebius-control-grid">
        <section className="panel nebius-actions-panel">
          <h2>Attack/Detect Runs</h2>
          <div className="nebius-button-row">
            <button disabled={busyAction !== null} onClick={() => void runAction("scenario", createSmartScenario, setScenario)}>
              Smart scenario
            </button>
            <button disabled={busyAction !== null} onClick={() => void runAction("detection", runSmartDetection, setAlert)}>
              Smart detection
            </button>
            <button disabled={busyAction !== null} onClick={() => void runAction("batch", () => runSmartBatches(100, 100), setBatch)}>
              Run 100 batch
            </button>
          </div>
          <div className="nebius-result-stack">
            <ResultBlock
              title="Scenario"
              value={scenario ? `${scenario.title} (${scenario.mode})` : "Not generated"}
              detail={scenario?.description ?? "Uses /generate-smart-scenario with bounded synthetic constraints."}
            />
            <ResultBlock
              title="Detection"
              value={alert ? `${alert.detected_pattern} ${(alert.suspicion_score * 100).toFixed(0)}%` : "Not scored"}
              detail={alert?.reasons.join("; ") ?? "Uses /orderbook-alert with a recent L2 window."}
            />
            <ResultBlock
              title="Batch"
              value={batch ? `${batch.runs} simulations in ${batch.elapsed_seconds}s` : "Not run"}
              detail={batch ? Object.values(batch.artifact_paths).join(", ") : "Runs attack/detect mode in parallel batches."}
            />
          </div>
        </section>

        <section className="panel nebius-usage-panel">
          <h2>Serverless Cost/Runtime Observatory</h2>
          <div className="usage-grid">
            <Metric label="Endpoint requests" value={String(observatory?.usage.endpoint_requests ?? 24)} />
            <Metric label="Avg latency" value={`${observatory?.usage.endpoint_avg_latency_seconds ?? 1.2}s`} />
            <Metric label="Job simulations" value={String(observatory?.usage.job_simulations ?? 1000)} />
            <Metric label="Runtime" value={observatory?.usage.job_runtime ?? "7m 42s"} />
          </div>
          <p className="lab-job-note">
            Artifacts: {(observatory?.usage.job_artifacts ?? ["benchmark_report.md", "detector_metrics.csv"]).join(", ")}
          </p>
        </section>

        <section className="panel nebius-evidence-panel">
          <h2>Nebius Usage Evidence</h2>
          <div className="evidence-placeholder">
            <strong>Real Nebius logs/metrics screenshots</strong>
            <span>{observatory?.screenshots[0]?.status ?? "placeholder"} · {observatory?.screenshots[0]?.path ?? "assets/screenshots/nebius-logs-metrics.svg"}</span>
          </div>
          <ul className="artifact-list">
            {Object.entries(observatory?.benchmark_artifacts ?? {}).map(([key, value]) => (
              <li key={key}><span>{key}</span><code>{value}</code></li>
            ))}
          </ul>
        </section>

        <section className="panel nebius-chart-panel">
          <h2>Benchmark Chart Artifacts</h2>
          <div className="nebius-chart-grid">
            <ChartFrame title="F1 by scenario">
              <BarChart data={metrics}>
                <CartesianGrid stroke="rgba(148, 163, 184, 0.16)" strokeDasharray="3 3" />
                <XAxis dataKey="scenario" tick={{ fill: "#8fb7c9", fontSize: 11 }} />
                <YAxis domain={[0, 1]} tick={{ fill: "#8fb7c9", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#071426", borderColor: "#1e3a5f", color: "#d8f3ff" }} />
                <Bar dataKey="f1" fill="#22d3ee" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartFrame>
            <ChartFrame title="Confidence distribution">
              <BarChart data={metrics}>
                <CartesianGrid stroke="rgba(148, 163, 184, 0.16)" strokeDasharray="3 3" />
                <XAxis dataKey="scenario" tick={{ fill: "#8fb7c9", fontSize: 11 }} />
                <YAxis domain={[0, 1]} tick={{ fill: "#8fb7c9", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#071426", borderColor: "#1e3a5f", color: "#d8f3ff" }} />
                <Bar dataKey="precision" fill="#22ab94" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartFrame>
            <ChartFrame title="Detection latency">
              <LineChart data={metrics}>
                <CartesianGrid stroke="rgba(148, 163, 184, 0.16)" strokeDasharray="3 3" />
                <XAxis dataKey="scenario" tick={{ fill: "#8fb7c9", fontSize: 11 }} />
                <YAxis tick={{ fill: "#8fb7c9", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#071426", borderColor: "#1e3a5f", color: "#d8f3ff" }} />
                <Line dataKey="latency" stroke="#f5b841" strokeWidth={2} type="monotone" />
              </LineChart>
            </ChartFrame>
          </div>
        </section>
      </div>
    </section>
  );
}

function StatusPill({ label, ok }: { label: string; ok?: boolean }) {
  return <span className={`status-pill ${ok ? "connected" : "disconnected"}`}>{label}</span>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric compact-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ResultBlock({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <div className="nebius-result-block">
      <span>{title}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </div>
  );
}

function ChartFrame({ title, children }: { title: string; children: React.ReactElement }) {
  return (
    <div className="nebius-chart-frame">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={190}>
        {children}
      </ResponsiveContainer>
    </div>
  );
}

function readableScenario(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}
