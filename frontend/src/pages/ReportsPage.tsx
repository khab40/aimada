import { useEffect, useMemo, useState } from "react";
import { getReportsSummary, type ReportsSummary } from "@/api/client";

const previousRuns = [
  { id: "RUN-2026-0602-001", mode: "Detector tournament", scenarios: 4, incidents: 37, f1: 0.88, status: "completed" },
  { id: "RUN-2026-0602-002", mode: "Synthetic dataset", scenarios: 4, incidents: 126, f1: null, status: "completed" },
  { id: "RUN-2026-0602-003", mode: "Arena replay", scenarios: 1, incidents: 3, f1: 0.91, status: "draft" }
];

const detections = [
  { type: "Quote stuffing", count: 14, confidence: 0.94, latency: "410 ms" },
  { type: "Spoofing-like wall", count: 9, confidence: 0.88, latency: "840 ms" },
  { type: "Layering-like", count: 6, confidence: 0.81, latency: "980 ms" },
  { type: "Liquidity shock", count: 8, confidence: 0.86, latency: "760 ms" }
];

export function ReportsPage() {
  const [summary, setSummary] = useState<ReportsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getReportsSummary()
      .then((result) => {
        if (!cancelled) {
          setSummary(result);
        }
      })
      .catch((nextError: unknown) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Could not load reports.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const runRows = useMemo(() => {
    const benchmarkRuns = summary?.benchmark_runs ?? [];
    if (!benchmarkRuns.length) {
      return previousRuns;
    }
    return benchmarkRuns.map((run) => {
      const results = Array.isArray(run.results) ? run.results : [];
      const incidents = (summary?.incidents ?? []).length;
      const averageF1 = results.length
        ? results.reduce((total, row) => total + Number((row as { f1?: number }).f1 ?? 0), 0) / results.length
        : null;
      return {
        f1: averageF1,
        id: String(run.id ?? "RUN"),
        incidents,
        mode: String(run.mode ?? "Benchmark run"),
        scenarios: results.length,
        status: String(run.status ?? "completed")
      };
    });
  }, [summary]);

  const detectionRows = useMemo(() => {
    const incidents = summary?.incidents ?? [];
    if (!incidents.length) {
      return detections;
    }
    const grouped = new Map<string, { count: number; confidence: number }>();
    for (const incident of incidents) {
      const type = String(incident.type ?? "unknown");
      const current = grouped.get(type) ?? { count: 0, confidence: 0 };
      current.count += 1;
      current.confidence = Math.max(current.confidence, Number(incident.confidence ?? 0));
      grouped.set(type, current);
    }
    return Array.from(grouped.entries()).map(([type, value]) => ({
      confidence: value.confidence,
      count: value.count,
      latency: "recorded",
      type: type.replaceAll("_", " ")
    }));
  }, [summary]);

  return (
    <section className="reports-page">
      <div className="panel lab-hero-panel">
        <div>
          <p className="eyebrow">Mock reporting workspace</p>
          <h2>Reports</h2>
          <p>Placeholder screen for previous runs, detector summaries, generated reports, and export decisions.</p>
        </div>
        <span className="endpoint-badge">{summary ? "persisted local artifacts" : "mock fallback"}</span>
      </div>
      {error ? <div className="empty-state warning">{error}</div> : null}

      <div className="reports-grid">
        <section className="panel report-card wide">
          <h3>Previous Runs</h3>
          <div className="report-table-wrap">
            <table className="benchmark-table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Mode</th>
                  <th>Scenarios</th>
                  <th>Incidents</th>
                  <th>F1</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {runRows.map((run) => (
                  <tr key={run.id}>
                    <td>{run.id}</td>
                    <td>{run.mode}</td>
                    <td>{run.scenarios}</td>
                    <td>{run.incidents}</td>
                    <td>{run.f1 === null ? "n/a" : run.f1.toFixed(2)}</td>
                    <td><span className={`report-status ${run.status}`}>{run.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel report-card">
          <h3>Detection Summary</h3>
          <div className="detection-summary-list">
            {detectionRows.map((item) => (
              <article key={item.type}>
                <div>
                  <strong>{item.type}</strong>
                  <span>{item.count} detections</span>
                </div>
                <dl>
                  <div><dt>Confidence</dt><dd>{item.confidence.toFixed(2)}</dd></div>
                  <div><dt>Latency</dt><dd>{item.latency}</dd></div>
                </dl>
              </article>
            ))}
          </div>
        </section>

        <section className="panel report-card">
          <h3>Generated Artifacts</h3>
          <ul className="artifact-list">
            <li><code>benchmark_report.md</code><span>Detector tournament narrative</span></li>
            <li><code>metrics.csv</code><span>Precision, recall, F1, latency</span></li>
            <li><code>results.json</code><span>Machine-readable benchmark output</span></li>
            <li><code>events.jsonl</code><span>Synthetic event stream</span></li>
            <li><code>incidents.jsonl</code><span>Detected synthetic incidents</span></li>
            <li><code>experiments/attack_experiments.jsonl</code><span>Saved attack builder configs</span></li>
            <li><code>events/significant_events.jsonl</code><span>Detector, attack, and benchmark evidence log</span></li>
          </ul>
        </section>

        <section className="panel report-card wide">
          <h3>Decisions To Make Later</h3>
          <div className="decision-grid">
            <span>Export report to Markdown or PDF</span>
            <span>Compare multiple benchmark runs</span>
            <span>Replay selected incident windows</span>
            <span>Attach Nebius logs and metrics screenshots</span>
            <span>Promote selected run to challenge submission evidence</span>
          </div>
        </section>
      </div>
    </section>
  );
}
