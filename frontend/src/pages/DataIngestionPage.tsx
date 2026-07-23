import { useCallback, useEffect, useState } from "react";
import {
  importLobsterCandidate,
  listImportedDatasets,
  listLobsterCandidates,
  type ImportedDataset,
  type LobsterCandidate
} from "@/api/client";

type ImportDuration = "1" | "5" | "full";
type ImportWindowSelection = {
  duration: ImportDuration;
  startTime: string;
};

export function DataIngestionPage() {
  const [candidates, setCandidates] = useState<LobsterCandidate[]>([]);
  const [datasets, setDatasets] = useState<ImportedDataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState<string | null>(null);
  const [importWindows, setImportWindows] = useState<Record<string, ImportWindowSelection>>({});
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextCandidates, nextDatasets] = await Promise.all([
        listLobsterCandidates(),
        listImportedDatasets()
      ]);
      setCandidates(nextCandidates);
      setDatasets(nextDatasets);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Data discovery failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!candidates.some((candidate) => candidate.status === "importing")) {
      return undefined;
    }
    const timer = window.setTimeout(() => void refresh(), 2_000);
    return () => window.clearTimeout(timer);
  }, [candidates, refresh]);

  async function importCandidate(candidate: LobsterCandidate) {
    const selectedWindow = resolveImportWindow(candidate, importWindows[candidate.candidate_id]);
    if (!selectedWindow.valid) {
      setError(selectedWindow.error);
      return;
    }
    setImporting(candidate.candidate_id);
    setError(null);
    try {
      await importLobsterCandidate(candidate.candidate_id, selectedWindow.request);
      await refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Import failed");
    } finally {
      setImporting(null);
    }
  }

  function updateImportWindow(candidate: LobsterCandidate, patch: Partial<ImportWindowSelection>) {
    setImportWindows((current) => ({
      ...current,
      [candidate.candidate_id]: {
        ...defaultImportWindow(candidate),
        ...current[candidate.candidate_id],
        ...patch
      }
    }));
  }

  return (
    <section className="administrative-page data-ingestion-page" aria-label="Data Ingestion">
      <section className="panel ingestion-intro">
        <div>
          <h2>LOBSTER batch import</h2>
          <p>
            Discover paired message and order-book CSV files under <code>data/lobster</code>,
            validate them, and register normalized Parquet datasets for historical replay.
          </p>
        </div>
        <button className="secondary-button" disabled={loading || importing !== null} onClick={() => void refresh()} type="button">
          {loading ? "Discovering…" : "Refresh"}
        </button>
      </section>

      {error ? <div className="empty-state warning" role="alert">{error}</div> : null}

      <section className="panel ingestion-section">
        <header>
          <h2>Available source datasets</h2>
          <span>{candidates.length} discovered</span>
        </header>
        {candidates.length === 0 && !loading ? (
          <div className="empty-state">No LOBSTER file pairs were found.</div>
        ) : (
          <div className="ingestion-table-wrap">
            <table className="ingestion-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Date</th>
                  <th>Time range</th>
                  <th>Depth</th>
                  <th>Message size</th>
                  <th>Order-book size</th>
                  <th>Import window</th>
                  <th>Status</th>
                  <th><span className="sr-only">Action</span></th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((candidate) => {
                  const selection = importWindows[candidate.candidate_id] ?? defaultImportWindow(candidate);
                  const selectedWindow = resolveImportWindow(candidate, selection);
                  return (
                  <tr key={candidate.candidate_id}>
                    <td><strong>{candidate.symbol}</strong></td>
                    <td>{candidate.trade_date}</td>
                    <td>{candidate.start_time}–{candidate.end_time}</td>
                    <td>{candidate.depth}</td>
                    <td>{formatBytes(candidate.message_file_size)}</td>
                    <td>{formatBytes(candidate.orderbook_file_size)}</td>
                    <td>
                      <div className="import-window-controls">
                        <label>
                          <span>Start</span>
                          <input
                            aria-label={`Import start time for ${candidate.symbol}`}
                            disabled={selection.duration === "full"}
                            max={formatTimeInput(candidate.end_time_ms)}
                            min={formatTimeInput(candidate.start_time_ms)}
                            onChange={(event) => updateImportWindow(candidate, { startTime: event.target.value })}
                            step="1"
                            type="time"
                            value={selection.startTime}
                          />
                        </label>
                        <label>
                          <span>Duration</span>
                          <select
                            aria-label={`Import duration for ${candidate.symbol}`}
                            onChange={(event) => updateImportWindow(candidate, { duration: event.target.value as ImportDuration })}
                            value={selection.duration}
                          >
                            <option value="1">1 minute</option>
                            <option value="5">5 minutes</option>
                            <option value="full">Full range</option>
                          </select>
                        </label>
                        <small className={selectedWindow.valid ? "" : "control-error"}>
                          {selectedWindow.valid ? selectedWindow.label : selectedWindow.error}
                        </small>
                      </div>
                    </td>
                    <td>
                      <span className={`ingestion-status ${candidate.status}`}>{candidate.status}</span>
                      {candidate.errors.length ? <small>{candidate.errors.join("; ")}</small> : null}
                    </td>
                    <td>
                      <button
                        className="primary-button"
                        disabled={!selectedWindow.valid || !["ready", "failed", "imported"].includes(candidate.status) || importing !== null}
                        onClick={() => void importCandidate(candidate)}
                        type="button"
                      >
                        {importing === candidate.candidate_id || candidate.status === "importing"
                          ? "Importing…"
                          : candidate.status === "imported"
                            ? "Import window"
                            : candidate.status === "failed"
                              ? "Retry"
                              : "Import window"}
                      </button>
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel ingestion-section">
        <header>
          <h2>Dataset registry</h2>
          <span>{datasets.length} ready</span>
        </header>
        {datasets.length === 0 ? (
          <div className="empty-state">Imported datasets will appear here and in Arena.</div>
        ) : (
          <div className="dataset-card-grid">
            {datasets.map((dataset) => (
              <article className="dataset-card" key={dataset.dataset_id}>
                <div><strong>{dataset.symbol}</strong><span>LOBSTER · depth {dataset.depth}</span></div>
                <p>{dataset.trade_date} · {dataset.start_time}–{dataset.end_time}</p>
                <p>{dataset.row_count.toLocaleString()} aligned events and snapshots</p>
                <code>{dataset.dataset_id}</code>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}

function defaultImportWindow(candidate: LobsterCandidate): ImportWindowSelection {
  return {
    duration: "1",
    startTime: formatTimeInput(candidate.start_time_ms)
  };
}

function resolveImportWindow(
  candidate: LobsterCandidate,
  selection = defaultImportWindow(candidate)
): {
  error: string;
  label: string;
  request: { start_time_ms?: number; end_time_ms?: number };
  valid: boolean;
} {
  if (selection.duration === "full") {
    return {
      error: "",
      label: `${candidate.start_time}–${candidate.end_time}`,
      request: {},
      valid: true
    };
  }
  const startTimeMs = parseTimeInput(selection.startTime);
  const durationMs = Number(selection.duration) * 60_000;
  const endTimeMs = startTimeMs + durationMs;
  if (
    !Number.isFinite(startTimeMs) ||
    startTimeMs < candidate.start_time_ms ||
    endTimeMs > candidate.end_time_ms
  ) {
    return {
      error: "Window must fit inside the source range.",
      label: "",
      request: {},
      valid: false
    };
  }
  return {
    error: "",
    label: `${formatTimeInput(startTimeMs)}–${formatTimeInput(endTimeMs)}`,
    request: { start_time_ms: startTimeMs, end_time_ms: endTimeMs },
    valid: true
  };
}

function parseTimeInput(value: string) {
  const parts = value.split(":").map(Number);
  if (parts.length < 2 || parts.some((part) => !Number.isFinite(part))) return Number.NaN;
  const [hours, minutes, seconds = 0] = parts;
  return ((hours * 60 + minutes) * 60 + seconds) * 1_000;
}

function formatTimeInput(value: number) {
  const hours = Math.floor(value / 3_600_000);
  const minutes = Math.floor((value % 3_600_000) / 60_000);
  const seconds = Math.floor((value % 60_000) / 1_000);
  return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
}

function formatBytes(value: number | null) {
  if (value === null) return "—";
  if (value < 1024) return `${value} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let amount = value / 1024;
  let unit = 0;
  while (amount >= 1024 && unit < units.length - 1) {
    amount /= 1024;
    unit += 1;
  }
  return `${amount.toFixed(amount >= 10 ? 1 : 2)} ${units[unit]}`;
}
