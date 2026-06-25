import { useEffect, useMemo, useState } from "react";
import {
  artifactDownloadUrl,
  clearReportsData,
  getManagedExperiment,
  getManagedExperimentLeaderboard,
  getManagedExperimentReport,
  getManagedExperimentReportUrl,
  getManagedExperimentSummary,
  getReportsSummary,
  listManagedExperimentInvestigations,
  listManagedExperiments,
  readArtifact,
  type ExperimentLeaderboardRow,
  type ExperimentSummary,
  type HistoryRecord,
  type InvestigationRecord,
  type ManagedExperiment,
  type ReportsSummary
} from "@/api/client";
import { ArtifactWorkbench, type ArtifactItem } from "@/components/ArtifactWorkbench";

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

const experimentArtifactKeys = new Set([
  "events",
  "trades",
  "labels",
  "alerts",
  "detector_metrics",
  "benchmark_report",
  "batch_manifest",
  "artifact_index",
  "experiment_summary",
  "leaderboard"
]);

type ArtifactIndexEntry = {
  key: string;
  source_path: string;
  normalized_path: string;
  exists: boolean;
};

export function ReportsPage() {
  const [summary, setSummary] = useState<ReportsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [clearConfirmation, setClearConfirmation] = useState("");
  const [clearMessage, setClearMessage] = useState<string | null>(null);
  const [clearBusy, setClearBusy] = useState(false);
  const [experiments, setExperiments] = useState<ManagedExperiment[]>([]);
  const [selectedExperimentId, setSelectedExperimentId] = useState<string | null>(null);
  const [selectedExperiment, setSelectedExperiment] = useState<ManagedExperiment | null>(null);
  const [experimentSummary, setExperimentSummary] = useState<ExperimentSummary | null>(null);
  const [experimentLeaderboard, setExperimentLeaderboard] = useState<ExperimentLeaderboardRow[]>([]);
  const [experimentReport, setExperimentReport] = useState("");
  const [experimentInvestigations, setExperimentInvestigations] = useState<InvestigationRecord[]>([]);
  const [artifactIndexEntries, setArtifactIndexEntries] = useState<ArtifactIndexEntry[]>([]);
  const [experimentError, setExperimentError] = useState<string | null>(null);
  const [experimentLoading, setExperimentLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([loadReports(), listManagedExperiments()])
      .then(([result, experimentRows]) => {
        if (!cancelled) {
          setSummary(result);
          const sorted = sortExperiments(experimentRows);
          setExperiments(sorted);
          setSelectedExperimentId((current) => current ?? sorted[0]?.id ?? null);
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

  useEffect(() => {
    if (!selectedExperimentId) {
      setSelectedExperiment(null);
      setExperimentSummary(null);
      setExperimentLeaderboard([]);
      setExperimentReport("");
      setExperimentInvestigations([]);
      setArtifactIndexEntries([]);
      return;
    }
    let cancelled = false;
    setExperimentLoading(true);
    setExperimentError(null);
    loadExperimentReports(selectedExperimentId)
      .then((result) => {
        if (!cancelled) {
          setSelectedExperiment(result.experiment);
          setExperimentSummary(result.summary);
          setExperimentLeaderboard(result.leaderboard);
          setExperimentReport(result.report);
          setExperimentInvestigations(result.investigations);
          setArtifactIndexEntries(result.artifactIndexEntries);
        }
      })
      .catch((nextError: unknown) => {
        if (!cancelled) {
          setExperimentError(nextError instanceof Error ? nextError.message : "Could not load experiment reports.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setExperimentLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedExperimentId]);

  async function loadReports() {
    setError(null);
    return getReportsSummary();
  }

  async function loadExperimentReports(experimentId: string) {
    const experiment = await getManagedExperiment(experimentId);
    const [experimentSummaryResult, leaderboard, report, investigations] = await Promise.all([
      getManagedExperimentSummary(experimentId).catch(() => null),
      getManagedExperimentLeaderboard(experimentId).catch(() => []),
      getManagedExperimentReport(experimentId).catch(() => ""),
      listManagedExperimentInvestigations(experimentId).catch(() => [])
    ]);
    const artifactIndexPath = experiment.artifact_paths.artifact_index;
    const artifactIndexEntriesResult = artifactIndexPath
      ? await readArtifact(artifactIndexPath)
        .then((artifact) => parseArtifactIndexEntries(artifact.content))
        .catch(() => [])
      : [];
    return {
      artifactIndexEntries: artifactIndexEntriesResult,
      experiment,
      investigations,
      leaderboard,
      report,
      summary: experimentSummaryResult
    };
  }

  async function clearEverything() {
    setClearBusy(true);
    setError(null);
    try {
      const response = await clearReportsData(clearConfirmation);
      setClearMessage(response.message);
      setClearDialogOpen(false);
      setClearConfirmation("");
      setSummary(await loadReports());
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Could not clear reports.");
    } finally {
      setClearBusy(false);
    }
  }

  const runRows = useMemo(() => {
    const benchmarkRuns = summary?.benchmark_runs ?? [];
    const nebiusBatches = summary?.nebius_batches ?? [];
    if (!benchmarkRuns.length && !nebiusBatches.length) {
      return previousRuns;
    }
    const benchmarkRows = benchmarkRuns.map((run) => {
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
    const nebiusRows = nebiusBatches.map((batch) => {
      const metrics = Array.isArray(batch.metrics) ? batch.metrics as Record<string, unknown>[] : [];
      const averageF1 = metrics.length
        ? metrics.reduce((total, row) => total + Number(row.f1 ?? 0), 0) / metrics.length
        : null;
      return {
        f1: averageF1,
        id: String(batch.id ?? "NEB"),
        incidents: metrics.reduce((total, row) => total + Number(row.alerts ?? 0), 0),
        mode: String(batch.deployment_target ?? batch.mode ?? "Nebius smart batch"),
        scenarios: Array.isArray(batch.scenarios) ? batch.scenarios.length : metrics.length,
        status: String(batch.status ?? "completed")
      };
    });
    return [...nebiusRows, ...benchmarkRows];
  }, [summary]);

  const detectionRows = useMemo(() => {
    const incidents = summary?.incidents ?? [];
    if (!incidents.length) {
      const nebiusMetrics = (summary?.nebius_batches ?? []).flatMap((batch) => Array.isArray(batch.metrics) ? batch.metrics as Record<string, unknown>[] : []);
      if (!nebiusMetrics.length) {
        return detections;
      }
      return nebiusMetrics.map((row) => ({
        confidence: Number(row.precision ?? 0),
        count: Number(row.alerts ?? 0),
        latency: `${row.avg_detection_latency_ms ?? "recorded"} ms`,
        type: String(row.scenario ?? "scenario").replaceAll("_", " ")
      }));
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

  const explanationRows = useMemo(() => {
    return summary?.explanations ?? [];
  }, [summary]);
  const benchmarkArtifacts = useMemo<ArtifactItem[]>(() => {
    const experiments = summary?.experiments ?? [];
    const runs = summary?.benchmark_runs ?? [];
    const nebiusBatches = summary?.nebius_batches ?? [];
    const nebiusArtifacts = summary?.nebius_artifacts ?? [];
    if (!experiments.length && !runs.length && !nebiusBatches.length && !nebiusArtifacts.length) {
      return [
        { description: "Detector tournament narrative", label: "benchmark_report.md", path: "outputs/benchmark/benchmark_report.md" },
        { description: "Precision, recall, F1, latency", label: "metrics.csv", path: "outputs/benchmark/metrics.csv" },
        { description: "Machine-readable benchmark output", label: "results.json", path: "outputs/benchmark/results.json" }
      ];
    }
    const experimentItems = experiments.flatMap((experiment) => {
      const paths = typeof experiment.artifact_paths === "object" && experiment.artifact_paths !== null
        ? experiment.artifact_paths as Record<string, string>
        : {};
      return Object.entries(paths)
        .filter(([label]) => experimentArtifactKeys.has(label))
        .map(([label, path]) => ({
          description: `${String(experiment.id ?? "experiment")} · ${path}`,
          label: `${String(experiment.id ?? "experiment")} · ${label.replaceAll("_", " ")}`,
          path
        }));
    });
    const benchmarkItems = runs.flatMap((run) => {
      const paths = typeof run.artifact_paths === "object" && run.artifact_paths !== null
        ? run.artifact_paths as Record<string, string>
        : {};
      return Object.entries(paths).map(([label, path]) => ({
        description: `${String(run.id ?? "run")} · ${path}`,
        label: `${String(run.id ?? "run")} · ${label.replaceAll("_", " ")}`,
        path
      }));
    });
    const batchItems = nebiusBatches.flatMap((batch) => {
      const paths = typeof batch.artifact_paths === "object" && batch.artifact_paths !== null
        ? batch.artifact_paths as Record<string, string>
        : {};
      return Object.entries(paths).map(([label, path]) => ({
        description: `${String(batch.id ?? "nebius")} · ${path}`,
        label: `${String(batch.id ?? "nebius")} · ${label.replaceAll("_", " ")}`,
        path
      }));
    });
    const explicitItems = nebiusArtifacts.map((artifact) => ({
      description: `${String(artifact.type ?? "artifact")} · ${String(artifact.status ?? "stored")}`,
      label: String(artifact.path ?? "artifact").split("/").at(-1) ?? "artifact",
      path: String(artifact.path ?? "")
    })).filter((item) => item.path);
    return [...explicitItems, ...experimentItems, ...batchItems, ...benchmarkItems];
  }, [summary]);
  const explanationArtifacts = useMemo<ArtifactItem[]>(() => [
    {
      description: "Persisted Nebius incident analyses",
      label: "incidents/explanations.jsonl",
      path: "outputs/incidents/explanations.jsonl"
    }
  ], []);
  const runIds = useMemo(() => [
    ...(summary?.nebius_batches ?? []).map((run) => String(run.id ?? "")),
    ...(summary?.benchmark_runs ?? []).map((run) => String(run.id ?? ""))
  ].filter(Boolean), [summary]);
  const incidentIds = useMemo(() => (summary?.incidents ?? []).map((incident) => String(incident.id ?? "")).filter(Boolean), [summary]);
  const historyRows = useMemo<HistoryRecord[]>(() => {
    return [...(summary?.history_artifacts ?? [])].reverse().slice(0, 25);
  }, [summary]);
  const historyCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of summary?.history_artifacts ?? []) {
      counts.set(row.kind, (counts.get(row.kind) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort(([left], [right]) => left.localeCompare(right));
  }, [summary]);
  const artifactIndexArtifacts = useMemo<ArtifactItem[]>(() => {
    if (!selectedExperiment) return [];
    const artifactIndexPath = selectedExperiment.artifact_paths.artifact_index;
    const items: ArtifactItem[] = artifactIndexPath
      ? [{
        description: "Normalized experiment artifact index",
        label: "artifact_index.json",
        path: artifactIndexPath
      }]
      : [];
    for (const entry of artifactIndexEntries) {
      if (entry.exists) {
        items.push({
          description: `normalized from ${entry.source_path}`,
          label: `${entry.key.replaceAll("_", " ")} · normalized`,
          path: entry.normalized_path
        });
      }
    }
    return dedupeArtifactItems(items);
  }, [artifactIndexEntries, selectedExperiment]);
  const localBatchArtifacts = useMemo<ArtifactItem[]>(() => {
    if (!selectedExperiment) return [];
    const fromExperiment = Object.entries(selectedExperiment.artifact_paths)
      .filter(([key]) => key.startsWith("local_batch_"))
      .map(([key, path]) => ({
        description: "Original local-batch artifact",
        label: key.replace("local_batch_", "").replaceAll("_", " "),
        path
      }));
    const fromIndex = artifactIndexEntries
      .filter((entry) => entry.exists)
      .map((entry) => ({
        description: `original source for ${entry.key}`,
        label: `${entry.key.replaceAll("_", " ")} · original`,
        path: entry.source_path
      }));
    return dedupeArtifactItems([...fromExperiment, ...fromIndex]);
  }, [artifactIndexEntries, selectedExperiment]);

  return (
    <section className="reports-page">
      <div className="panel lab-hero-panel">
        <div>
          <p className="eyebrow">Evidence workspace</p>
          <h2>Replay & Reports</h2>
          <p>Reload saved experiment evidence, incident replay windows, AI-generated reports, Nebius artifacts, exports, and promoted challenge evidence.</p>
        </div>
        <div className="reports-hero-actions">
          <span className="endpoint-badge">{summary ? "persisted evidence" : "loading evidence"}</span>
          <button className="danger-button" onClick={() => setClearDialogOpen(true)} type="button">Clean Replay & Reports Data</button>
        </div>
      </div>
      {error ? <div className="empty-state warning">{error}</div> : null}
      {clearMessage ? <div className="empty-state">{clearMessage}</div> : null}

      <div className="reports-grid">
        <section className="panel report-card wide experiment-reports-panel">
          <div className="section-heading-row">
            <div>
              <h3>Phase 4.5 Experiments</h3>
              <p className="empty-state">Synthetic educational benchmark reports generated by the local experiment manager.</p>
            </div>
            <span className="endpoint-badge">{experiments.length} experiments</span>
          </div>
          {experimentError ? <div className="empty-state warning">{experimentError}</div> : null}
          <div className="experiment-report-layout">
            <div className="experiment-list-panel" aria-label="Experiment list">
              {experiments.length ? experiments.map((experiment) => (
                <button
                  className={experiment.id === selectedExperimentId ? "selected" : ""}
                  key={experiment.id}
                  onClick={() => setSelectedExperimentId(experiment.id)}
                  type="button"
                >
                  <strong>{experiment.name}</strong>
                  <span>{experiment.id} · {experiment.status.replaceAll("_", " ")} · {experiment.attack_count} attacks</span>
                </button>
              )) : <p className="empty-state">No managed experiments yet. Create one from the Nebius Experiment Lab.</p>}
            </div>

            <div className="experiment-report-detail">
              <div className="experiment-report-header">
                <div>
                  <span className="eyebrow">Selected experiment</span>
                  <h3>{selectedExperiment?.name ?? "No experiment selected"}</h3>
                </div>
                <span className={`report-status ${selectedExperiment?.status ?? "draft"}`}>
                  {experimentLoading ? "loading" : selectedExperiment?.status.replaceAll("_", " ") ?? "none"}
                </span>
              </div>

              <div className="experiment-report-metrics">
                <Metric label="Attack Count" value={String(selectedExperiment?.attack_count ?? 0)} />
                <Metric label="Labeled Attacks" value={String(experimentSummary?.total_attacks ?? 0)} />
                <Metric label="Alerts" value={String(experimentSummary?.total_alerts ?? 0)} />
                <Metric label="Investigations" value={String(experimentInvestigations.length || experimentSummary?.investigation_count || 0)} />
                <Metric label="Failed Runs" value={String(experimentSummary?.failed_runs ?? 0)} />
              </div>

              <div className="experiment-report-sections">
                <section className="nebius-result-block">
                  <span>Selected experiment summary</span>
                  {experimentSummary ? (
                    <div className="experiment-summary-list">
                      <p><strong>Scenarios:</strong> {experimentSummary.scenarios.map((scenario) => scenario.replaceAll("_", " ")).join(", ")}</p>
                      <p><strong>Average detection latency:</strong> {experimentSummary.avg_detection_latency_ms == null ? "n/a" : `${experimentSummary.avg_detection_latency_ms.toFixed(0)} ms`}</p>
                      <p><strong>Artifacts:</strong> {Object.keys(experimentSummary.artifact_paths).length} indexed paths</p>
                    </div>
                  ) : (
                    <p>Aggregate the experiment to generate summary metrics.</p>
                  )}
                </section>

                <section className="nebius-result-block">
                  <span>Benchmark report viewer</span>
                  {selectedExperiment && experimentReport ? (
                    <>
                      <div className="artifact-preview-title">
                        <strong>benchmark_report.md</strong>
                        <a href={getManagedExperimentReportUrl(selectedExperiment.id)} target="_blank" rel="noreferrer">Open raw</a>
                      </div>
                      <pre className="markdown-report-preview">{experimentReport}</pre>
                    </>
                  ) : (
                    <p>Run aggregation to generate `benchmark_report.md`.</p>
                  )}
                </section>
              </div>
            </div>
          </div>

          <div className="experiment-report-output-grid">
            <section className="nebius-result-block">
              <span>Leaderboard</span>
              {experimentLeaderboard.length ? (
                <div className="report-table-wrap">
                  <table className="benchmark-table">
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
                      {experimentLeaderboard.map((row) => (
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
              ) : <p>Aggregate the experiment to populate detector leaderboard rows.</p>}
            </section>

            <section className="nebius-result-block">
              <span>Investigation reports</span>
              {experimentInvestigations.length ? (
                <div className="investigation-report-list">
                  {experimentInvestigations.map((report) => (
                    <article key={report.alert_id}>
                      <strong>{report.alert_id}</strong>
                      <span>{report.mode} · {report.latency_seconds.toFixed(2)}s</span>
                      {report.fallback_reason ? <p>{report.fallback_reason}</p> : null}
                      <div className="nebius-button-row">
                        <a href={artifactDownloadUrl(report.markdown_path)} target="_blank" rel="noreferrer">Markdown</a>
                        <a href={artifactDownloadUrl(report.json_path)} target="_blank" rel="noreferrer">JSON</a>
                      </div>
                    </article>
                  ))}
                </div>
              ) : <p>Run AI investigations to populate report files.</p>}
            </section>
          </div>

          <div className="experiment-artifact-workbench-grid">
            <ArtifactWorkbench
              artifacts={artifactIndexArtifacts}
              runIds={selectedExperiment ? [selectedExperiment.id] : []}
              selectedRunId={selectedExperiment?.id ?? null}
              title="Artifact Index"
            />
            <ArtifactWorkbench
              artifacts={localBatchArtifacts}
              runIds={selectedExperiment ? [selectedExperiment.id] : []}
              selectedRunId={selectedExperiment?.id ?? null}
              title="Local Batch Originals"
            />
          </div>
        </section>

        <section className="panel report-card wide">
          <h3>Unified History Model</h3>
          <div className="surveillance-status-strip">
            <Metric label="History Artifacts" value={String(summary?.history_artifacts.length ?? 0)} />
            <Metric label="Recent Ticks" value={String(summary?.history_ticks.length ?? 0)} />
            <Metric label="AI Reports" value={String((summary?.explanations.length ?? 0) + (summary?.nebius_investigation_reports.length ?? 0))} />
            <Metric label="Detections" value={String((summary?.incidents.length ?? 0) + (summary?.nebius_detections.length ?? 0))} />
          </div>
          {historyCounts.length ? (
            <div className="history-kind-list">
              {historyCounts.map(([kind, count]) => (
                <span className="endpoint-badge" key={kind}>{kind.replaceAll("_", " ")}: {count}</span>
              ))}
            </div>
          ) : null}
          {historyRows.length ? (
            <div className="report-table-wrap">
              <table className="benchmark-table">
                <thead>
                  <tr>
                    <th>Kind</th>
                    <th>Summary</th>
                    <th>Run</th>
                    <th>Tick</th>
                    <th>Saved</th>
                  </tr>
                </thead>
                <tbody>
                  {historyRows.map((row) => (
                    <tr key={row.history_id}>
                      <td>{row.kind.replaceAll("_", " ")}</td>
                      <td>{row.summary}</td>
                      <td>{row.run_id ?? row.scenario_id ?? "n/a"}</td>
                      <td>{row.tick ?? "n/a"}</td>
                      <td>{formatSavedAt(row.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty-state">No unified history records yet. Start surveillance, inject a red-team scenario, run detection, or generate a report.</p>
          )}
        </section>

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

        <section className="panel report-card wide">
          <h3>Generated Artifacts</h3>
          <ArtifactWorkbench
            artifacts={benchmarkArtifacts}
            incidentIds={incidentIds}
            runIds={runIds}
            selectedRunId={runIds[0] ?? null}
            title="Benchmark Reports"
          />
        </section>

        <section className="panel report-card wide">
          <h3>Nebius Analysis History</h3>
          {explanationRows.length ? (
            <div className="report-table-wrap">
              <table className="benchmark-table">
                <thead>
                  <tr>
                    <th>Explanation</th>
                    <th>Incident</th>
                    <th>Mode</th>
                    <th>Risk</th>
                    <th>Saved</th>
                  </tr>
                </thead>
                <tbody>
                  {explanationRows.map((row) => (
                    <tr key={String(row.id ?? row.explanation_id ?? row.created_at)}>
                      <td>{String(row.id ?? "EXP-AI")}</td>
                      <td>{String(row.incident_id ?? "n/a")}</td>
                      <td>{String(row.mode ?? "n/a")}</td>
                      <td>{String(row.risk_level ?? "n/a")}</td>
                      <td>{String(row.created_at ?? "recorded")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty-state">No persisted Nebius incident explanations yet.</p>
          )}
        </section>

        <section className="panel report-card wide">
          <ArtifactWorkbench
            artifacts={explanationArtifacts}
            explanationRows={explanationRows}
            incidentIds={incidentIds}
            runIds={runIds}
            selectedRunId={runIds[0] ?? null}
            title="Explanations"
          />
        </section>
      </div>
      {clearDialogOpen ? (
        <div className="dialog-backdrop" role="presentation">
          <section aria-labelledby="clear-reports-title" aria-modal="true" className="confirm-dialog" role="dialog">
            <div>
              <p className="eyebrow">Destructive action</p>
              <h2 id="clear-reports-title">Clean all Replay & Reports data?</h2>
              <p>
                This clears persisted report indexes, benchmark run history, Nebius batch records,
                incidents, explanations, screenshot evidence, exports, and promoted evidence from the local output store.
              </p>
            </div>
            <label className="form-row">
              Type <strong>DELETE REPORTS</strong> to confirm
              <input
                autoFocus
                onChange={(event) => setClearConfirmation(event.target.value)}
                value={clearConfirmation}
              />
            </label>
            <div className="nebius-button-row">
              <button onClick={() => { setClearDialogOpen(false); setClearConfirmation(""); }} type="button">Cancel</button>
              <button
                className="danger-button"
                disabled={clearBusy || clearConfirmation !== "DELETE REPORTS"}
                onClick={() => void clearEverything()}
                type="button"
              >
                {clearBusy ? "Cleaning..." : "Clean Everything"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="cockpit-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatSavedAt(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value || "recorded";
  }
  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short"
  }).format(parsed);
}

function sortExperiments(experiments: ManagedExperiment[]) {
  return [...experiments].sort((left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at));
}

function parseArtifactIndexEntries(content: string): ArtifactIndexEntry[] {
  try {
    const parsed = JSON.parse(content) as { artifacts?: unknown };
    if (!Array.isArray(parsed.artifacts)) return [];
    return parsed.artifacts.flatMap((entry) => {
      if (!entry || typeof entry !== "object") return [];
      const row = entry as Record<string, unknown>;
      const key = String(row.key ?? "");
      const sourcePath = String(row.source_path ?? "");
      const normalizedPath = String(row.normalized_path ?? "");
      if (!key || !sourcePath || !normalizedPath) return [];
      return [{
        exists: row.exists === true,
        key,
        normalized_path: normalizedPath,
        source_path: sourcePath
      }];
    });
  } catch {
    return [];
  }
}

function dedupeArtifactItems(items: ArtifactItem[]) {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (!item.path || seen.has(item.path)) return false;
    seen.add(item.path);
    return true;
  });
}

function formatScore(value: number) {
  return Number.isFinite(value) ? value.toFixed(3) : "n/a";
}
