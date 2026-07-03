import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  artifactDownloadUrl,
  clearReportsData,
  exportArtifact,
  getManagedExperiment,
  getManagedExperimentLeaderboard,
  getManagedExperimentReport,
  getManagedExperimentReportUrl,
  getManagedExperimentSummary,
  getReportsSummary,
  listManagedExperimentJobs,
  listManagedExperimentInvestigations,
  listManagedExperiments,
  readArtifact,
  runManagedExperimentInvestigations,
  type ExperimentLeaderboardRow,
  type ExperimentJobRecord,
  type ExperimentSummary,
  type HistoryRecord,
  type InvestigationRunResponse,
  type InvestigationRecord,
  type ManagedExperiment,
  type ReportsSummary
} from "@/api/client";
import { ArtifactWorkbench, type ArtifactItem } from "@/components/ArtifactWorkbench";
import { NebiusExecutionTrace, type NebiusExecutionTraceData } from "@/components/NebiusExecutionTrace";

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
  const [searchParams] = useSearchParams();
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
  const [experimentJobs, setExperimentJobs] = useState<ExperimentJobRecord[]>([]);
  const [artifactIndexEntries, setArtifactIndexEntries] = useState<ArtifactIndexEntry[]>([]);
  const [experimentError, setExperimentError] = useState<string | null>(null);
  const [experimentLoading, setExperimentLoading] = useState(false);
  const [deepInvestigationBusy, setDeepInvestigationBusy] = useState(false);
  const [deepInvestigationMessage, setDeepInvestigationMessage] = useState<string | null>(null);
  const [deepInvestigationTrace, setDeepInvestigationTrace] = useState<NebiusExecutionTraceData>(() => createIdleDeepInvestigationTrace(null));
  const [reportExportBusy, setReportExportBusy] = useState<"json" | "pdf" | null>(null);
  const [reportExportMessage, setReportExportMessage] = useState<string | null>(null);

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
          setExperimentJobs(result.jobs);
          setArtifactIndexEntries(result.artifactIndexEntries);
          setDeepInvestigationTrace(createIdleDeepInvestigationTrace(result.experiment, searchParams.get("demo") === "batch-job"));
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
    const [experimentSummaryResult, leaderboard, report, investigations, jobs] = await Promise.all([
      getManagedExperimentSummary(experimentId).catch(() => null),
      getManagedExperimentLeaderboard(experimentId).catch(() => []),
      getManagedExperimentReport(experimentId).catch(() => ""),
      listManagedExperimentInvestigations(experimentId).catch(() => []),
      listManagedExperimentJobs(experimentId).catch(() => [])
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
      jobs,
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
  const complianceReport = useMemo(() => {
    const primaryIncident = detectionRows[0];
    const reportTimestamp = selectedExperiment?.updated_at ?? historyRows[0]?.created_at ?? new Date().toISOString();
    return {
      affectedSymbols: collectAffectedSymbols(summary),
      confidence: primaryIncident?.confidence ?? maxLeaderboardScore(experimentLeaderboard),
      evidenceCount: benchmarkArtifacts.length + artifactIndexArtifacts.length + localBatchArtifacts.length + explanationRows.length + (summary?.evidence_screenshots.length ?? 0),
      generatedBy: experimentInvestigations.length ? "Nebius AI Investigator" : "AI Market Abuse Detection Arena",
      incidentType: primaryIncident?.type ?? selectedExperiment?.scenarios[0]?.replaceAll("_", " ") ?? "No incident selected",
      timeline: `${historyRows.length} records / ${summary?.history_ticks.length ?? 0} ticks`,
      timestamp: reportTimestamp
    };
  }, [
    artifactIndexArtifacts.length,
    benchmarkArtifacts.length,
    detectionRows,
    experimentInvestigations.length,
    experimentLeaderboard,
    explanationRows.length,
    historyRows,
    localBatchArtifacts.length,
    selectedExperiment,
    summary
  ]);

  async function exportCompliancePdf() {
    const reportPath = selectedExperiment?.artifact_paths.benchmark_report;
    if (!reportPath) {
      setReportExportMessage("No report artifact is available for PDF export.");
      return;
    }
    setReportExportBusy("pdf");
    setReportExportMessage(null);
    try {
      const exported = await exportArtifact(reportPath, "pdf");
      window.open(exported.download_url || artifactDownloadUrl(exported.path), "_blank", "noreferrer");
      setReportExportMessage(`PDF export created: ${exported.path}`);
    } catch (nextError) {
      setReportExportMessage(nextError instanceof Error ? nextError.message : "PDF export failed.");
    } finally {
      setReportExportBusy(null);
    }
  }

  function exportComplianceJson() {
    setReportExportBusy("json");
    setReportExportMessage(null);
    try {
      downloadJson("incident-compliance-report.json", complianceReport);
      setReportExportMessage("JSON export created.");
    } catch {
      setReportExportMessage("JSON export failed.");
    } finally {
      setReportExportBusy(null);
    }
  }

  async function runDeepInvestigationJob() {
    const startedAt = performance.now();
    setDeepInvestigationBusy(true);
    setDeepInvestigationMessage(null);
    setDeepInvestigationTrace((current) => ({ ...current, status: "running" }));
    if (!selectedExperiment) {
      setDeepInvestigationTrace(createFallbackDeepInvestigationTrace(null, startedAt, "No persisted experiment selected."));
      setDeepInvestigationMessage("No experiment selected. Using deterministic simulated fallback.");
      setDeepInvestigationBusy(false);
      return;
    }
    try {
      const result = await runManagedExperimentInvestigations(selectedExperiment.id, 7);
      setExperimentInvestigations(result.investigations);
      setDeepInvestigationTrace(createDeepInvestigationTrace(selectedExperiment, result, startedAt));
      setDeepInvestigationMessage(`Deep investigation job completed for ${result.investigation_count} alert(s).`);
    } catch (nextError) {
      setDeepInvestigationTrace(createFallbackDeepInvestigationTrace(selectedExperiment, startedAt));
      setDeepInvestigationMessage(nextError instanceof Error ? `${nextError.message}. Using deterministic simulated fallback.` : "Using deterministic simulated fallback.");
    } finally {
      setDeepInvestigationBusy(false);
    }
  }

  return (
    <section className="reports-page">
      <div className="panel lab-hero-panel">
        <div>
          <h2>Incident Investigation</h2>
        </div>
      </div>
      {error ? <div className="empty-state warning">{error}</div> : null}
      {clearMessage ? <div className="empty-state">{clearMessage}</div> : null}

      <div className="reports-grid investigation-workflow">
        <section className="panel report-card wide experiment-reports-panel">
          <div className="section-heading-row">
            <div>
              <h3>Incident Summary</h3>
            </div>
          </div>
          <div className="surveillance-status-strip">
            <Metric label="Persisted Incidents" value={String(summary?.incidents.length ?? 0)} />
            <Metric label="AI Analyses" value={String((summary?.explanations.length ?? 0) + (summary?.nebius_investigation_reports.length ?? 0))} />
            <Metric label="Experiments" value={String(experiments.length)} />
            <Metric label="Selected Run" value={selectedExperiment?.id ?? "none"} />
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
              )) : <p className="empty-state">No Managed Experiments yet. Create one from the Nebius AI Managed Experiment Lab.</p>}
            </div>

            <div className="experiment-report-detail">
              <div className="experiment-report-header">
                <div>
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
                <Metric label="Investigation Reports" value={String(experimentInvestigations.length || experimentSummary?.investigation_count || 0)} />
                <Metric label="Failed Runs" value={String(experimentSummary?.failed_runs ?? 0)} />
                <Metric label="Nebius Jobs" value={String(experimentJobs.length)} />
              </div>

              <section className="nebius-result-block deep-investigation-job">
                <div className="artifact-preview-title">
                  <strong>Deep Investigation Job</strong>
                  <button disabled={deepInvestigationBusy || !selectedExperiment} onClick={() => void runDeepInvestigationJob()} type="button">
                    {deepInvestigationBusy ? "Running..." : "Run Deep Investigation Job"}
                  </button>
                </div>
                <p>
                  Sends incident replay, evidence, detector logs, and market snapshots into the Nebius job workflow.
                </p>
                <NebiusExecutionTrace trace={deepInvestigationTrace} />
                {deepInvestigationMessage ? <p className="empty-state">{deepInvestigationMessage}</p> : null}
              </section>

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
                  <span>Incident type summary</span>
                  <div className="detection-summary-list">
                    {detectionRows.map((item) => (
                      <article key={item.type}>
                        <div>
                          <strong>{item.type}</strong>
                          <span>{item.count} incidents</span>
                        </div>
                        <dl>
                          <div><dt>Confidence</dt><dd>{item.confidence.toFixed(2)}</dd></div>
                          <div><dt>Latency</dt><dd>{item.latency}</dd></div>
                        </dl>
                      </article>
                    ))}
                  </div>
                </section>
              </div>
            </div>
          </div>
        </section>

        <section className="panel report-card wide">
          <div className="section-heading-row">
            <div>
              <h3>Evidence</h3>
            </div>
          </div>
          <ArtifactWorkbench
            artifacts={benchmarkArtifacts}
            incidentIds={incidentIds}
            runIds={runIds}
            selectedRunId={runIds[0] ?? null}
            title="Evidence Artifacts"
          />
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
          <ArtifactWorkbench
            artifacts={explanationArtifacts}
            explanationRows={explanationRows}
            incidentIds={incidentIds}
            runIds={runIds}
            selectedRunId={runIds[0] ?? null}
            title="AI Explanation Evidence"
          />
        </section>

        <section className="panel report-card wide">
          <div className="section-heading-row">
            <div>
              <h3>Replay</h3>
            </div>
          </div>
          <div className="surveillance-status-strip">
            <Metric label="History Artifacts" value={String(summary?.history_artifacts.length ?? 0)} />
            <Metric label="Replay Ticks" value={String(summary?.history_ticks.length ?? 0)} />
            <Metric label="Investigation Reports" value={String(experimentInvestigations.length)} />
            <Metric label="Completed Runs" value={String(runRows.length)} />
          </div>
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
            <p className="empty-state">No replay history yet. Run a scenario or generate an investigation report.</p>
          )}
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

        <section className="panel report-card wide">
          <div className="section-heading-row">
            <div>
              <h3>Report</h3>
            </div>
            <button className="danger-button" onClick={() => setClearDialogOpen(true)} type="button">Clean Investigation Data</button>
          </div>
          <section className="nebius-result-block compliance-report-panel">
            <div className="artifact-preview-title">
              <strong>Compliance Report</strong>
              <div className="nebius-button-row">
                <button disabled={reportExportBusy !== null} onClick={() => void exportCompliancePdf()} type="button">
                  {reportExportBusy === "pdf" ? "Exporting..." : "Export PDF"}
                </button>
                <button disabled={reportExportBusy !== null} onClick={exportComplianceJson} type="button">
                  {reportExportBusy === "json" ? "Exporting..." : "Export JSON"}
                </button>
              </div>
            </div>
            <div className="compliance-card-grid">
              <ComplianceField label="Incident type" value={complianceReport.incidentType} />
              <ComplianceField label="Confidence" value={formatScore(complianceReport.confidence)} />
              <ComplianceField label="Evidence count" value={String(complianceReport.evidenceCount)} />
              <ComplianceField label="Timeline" value={complianceReport.timeline} />
              <ComplianceField label="Affected symbols" value={complianceReport.affectedSymbols.join(", ")} />
              <ComplianceField label="Generated by" value={complianceReport.generatedBy} />
              <ComplianceField label="Timestamp" value={formatSavedAt(complianceReport.timestamp)} />
            </div>
            {reportExportMessage ? <p className="empty-state">{reportExportMessage}</p> : null}
          </section>
          <div className="experiment-report-output-grid">
            <section className="nebius-result-block">
              <span>Investigation metrics appendix</span>
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
              <span>AI Investigator report files</span>
              {experimentInvestigations.length ? (
                <div className="detection-report-list">
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
              ) : <p>Run AI Investigator reports to populate report files.</p>}
            </section>
          </div>

          <section className="nebius-result-block">
            <span>Final report preview</span>
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

        </section>
      </div>
      {clearDialogOpen ? (
        <div className="dialog-backdrop" role="presentation">
          <section aria-labelledby="clear-reports-title" aria-modal="true" className="confirm-dialog" role="dialog">
            <div>
              <h2 id="clear-reports-title">Clean all investigation data?</h2>
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

function ComplianceField({ label, value }: { label: string; value: string }) {
  return (
    <article className="compliance-card">
      <span>{label}</span>
      <strong>{value || "n/a"}</strong>
    </article>
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

function createIdleDeepInvestigationTrace(experiment: ManagedExperiment | null, demo = false): NebiusExecutionTraceData {
  return {
    artifactLink: experiment?.artifact_paths.benchmark_report ?? experiment?.artifact_dir ?? null,
    endpointId: null,
    estimatedCost: "-",
    executionType: "job",
    fallback: demo || experiment?.nebius_mode !== "real_nebius_pending" ? "simulated" : "real",
    jobId: null,
    lastExecutionTime: "Not run yet",
    latency: "-",
    model: "Nebius investigation job",
    runId: experiment?.id ?? "no-experiment",
    runtimeGpu: demo ? "Deterministic demo fallback" : "Nebius Serverless Job",
    status: demo ? "Ready for batch demo" : "Idle",
    tokensIn: "-",
    tokensOut: "-"
  };
}

function createDeepInvestigationTrace(
  experiment: ManagedExperiment,
  result: InvestigationRunResponse,
  startedAt: number
): NebiusExecutionTraceData {
  const fallback = result.investigation_mode === "mock" || result.investigations.some((item) => item.fallback_reason) ? "simulated" : "real";
  const tokensIn = 2200 + result.selected_count * 420;
  const tokensOut = 900 + result.investigation_count * 180;
  return {
    artifactLink: result.investigations[0]?.markdown_path ?? experiment.artifact_paths.benchmark_report ?? experiment.artifact_dir,
    endpointId: "nebius-investigation-report",
    estimatedCost: fallback === "simulated" ? "$0.0000 simulated" : `$${((tokensIn * 0.00000045) + (tokensOut * 0.0000012)).toFixed(4)}`,
    executionType: "job",
    fallback,
    jobId: `JOB-${experiment.id}-INV`,
    lastExecutionTime: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    latency: `${Math.max(result.endpoint_avg_latency_seconds || 0, (performance.now() - startedAt) / 1000).toFixed(1)}s`,
    model: result.investigation_mode === "mock" ? "Deterministic fallback investigator" : "Nebius investigation model",
    runId: experiment.id,
    runtimeGpu: fallback === "simulated" ? "Local deterministic fallback" : "Nebius Serverless GPU job",
    status: fallback === "simulated" ? "Simulated fallback" : "Completed",
    tokensIn: tokensIn.toLocaleString(),
    tokensOut: tokensOut.toLocaleString()
  };
}

function createFallbackDeepInvestigationTrace(
  experiment: ManagedExperiment | null,
  startedAt: number,
  reason = "Nebius credentials or job configuration unavailable."
): NebiusExecutionTraceData {
  const tokensIn = 1800 + (experiment?.attack_count ?? 1) * 12;
  const tokensOut = 760;
  return {
    artifactLink: experiment?.artifact_paths.benchmark_report ?? experiment?.artifact_dir ?? null,
    endpointId: null,
    estimatedCost: "$0.0000 simulated",
    executionType: "job",
    fallback: "simulated",
    jobId: experiment ? `SIM-JOB-${experiment.id}` : "SIM-JOB-NO-EXPERIMENT",
    lastExecutionTime: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    latency: `${Math.max(0.2, (performance.now() - startedAt) / 1000).toFixed(1)}s`,
    model: "Deterministic fallback investigator",
    runId: experiment?.id ?? "no-experiment",
    runtimeGpu: "Local deterministic fallback",
    status: `Simulated fallback: ${reason}`,
    tokensIn: tokensIn.toLocaleString(),
    tokensOut: tokensOut.toLocaleString()
  };
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

function maxLeaderboardScore(rows: ExperimentLeaderboardRow[]) {
  const scores = rows.map((row) => row.f1).filter(Number.isFinite);
  return scores.length ? Math.max(...scores) : 0;
}

function collectAffectedSymbols(summary: ReportsSummary | null) {
  const symbols = new Set<string>();
  for (const row of [...(summary?.incidents ?? []), ...(summary?.history_artifacts ?? []), ...(summary?.history_ticks ?? [])]) {
    collectSymbolFromRecord(row as Record<string, unknown>, symbols);
  }
  return symbols.size ? Array.from(symbols) : ["AIMADA-SIM"];
}

function collectSymbolFromRecord(row: Record<string, unknown>, symbols: Set<string>) {
  for (const key of ["symbol", "ticker", "instrument"]) {
    const value = row[key];
    if (typeof value === "string" && value.trim()) {
      symbols.add(value.trim());
    }
  }
  const payload = row.payload;
  if (payload && typeof payload === "object") {
    collectSymbolFromRecord(payload as Record<string, unknown>, symbols);
  }
}

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
