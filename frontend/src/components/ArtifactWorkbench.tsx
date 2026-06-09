import { useMemo, useState } from "react";
import type React from "react";
import {
  artifactDownloadUrl,
  attachNebiusScreenshot,
  compareBenchmarkRuns,
  exportArtifact,
  promoteBenchmarkRun,
  readArtifact,
  replayIncidentWindow
} from "@/api/client";

export type ArtifactItem = {
  label: string;
  path: string;
  description?: string;
};

type ArtifactWorkbenchProps = {
  title: string;
  artifacts: ArtifactItem[];
  runIds?: string[];
  selectedRunId?: string | null;
  incidentIds?: string[];
  explanationRows?: Record<string, unknown>[];
};

export function ArtifactWorkbench({
  artifacts,
  explanationRows = [],
  incidentIds = [],
  runIds = [],
  selectedRunId = null,
  title
}: ArtifactWorkbenchProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [previewTitle, setPreviewTitle] = useState("No artifact selected");
  const [preview, setPreview] = useState("Select an artifact or explanation to preview it here.");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const selectableItems = useMemo(() => {
    const artifactItems = artifacts.map((artifact) => ({
      kind: "artifact" as const,
      key: `artifact:${artifact.path}`,
      label: artifact.label,
      path: artifact.path,
      description: artifact.description ?? artifact.path,
      payload: artifact
    }));
    const explanationItems = explanationRows.map((row, index) => ({
      kind: "explanation" as const,
      key: `explanation:${String(row.id ?? row.explanation_id ?? index)}`,
      label: String(row.id ?? row.explanation_id ?? `Explanation ${index + 1}`),
      path: "",
      description: String(row.incident_id ?? row.created_at ?? "Nebius explanation"),
      payload: row
    }));
    return [...artifactItems, ...explanationItems];
  }, [artifacts, explanationRows]);

  const selected = selectableItems[selectedIndex] ?? null;
  const selectedArtifact = selected?.kind === "artifact" ? selected.payload : null;
  const primaryRunId = selectedRunId ?? runIds[0] ?? null;
  const primaryIncidentId = incidentIds[0] ?? explanationRows.map((row) => String(row.incident_id ?? "")).find(Boolean) ?? null;

  async function openSelected(item = selected) {
    if (!item) {
      return;
    }
    setBusy("open");
    setMessage(null);
    try {
      if (item.kind === "artifact") {
        const response = await readArtifact(item.path);
        setPreviewTitle(`${response.name} · ${response.content_type}`);
        setPreview(response.content);
      } else {
        setPreviewTitle(item.label);
        setPreview(JSON.stringify(item.payload, null, 2));
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Preview failed.");
    } finally {
      setBusy(null);
    }
  }

  function moveSelection(nextIndex: number) {
    const bounded = Math.max(0, Math.min(selectableItems.length - 1, nextIndex));
    setSelectedIndex(bounded);
  }

  function handleListKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (!selectableItems.length) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveSelection(selectedIndex + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveSelection(selectedIndex - 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      moveSelection(0);
    } else if (event.key === "End") {
      event.preventDefault();
      moveSelection(selectableItems.length - 1);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      void openSelected();
    }
  }

  async function runAction(label: string, action: () => Promise<string>) {
    setBusy(label);
    setMessage(null);
    try {
      setMessage(await action());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : `${label} failed.`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="artifact-workbench">
      <div className="artifact-workbench-header">
        <h3>{title}</h3>
        <span>{selectableItems.length} items</span>
      </div>

      <div className="artifact-workbench-layout">
        <div
          aria-activedescendant={selected ? itemDomId(selected.key) : undefined}
          aria-label={`${title} items`}
          className="artifact-nav-list"
          onKeyDown={handleListKeyDown}
          role="listbox"
          tabIndex={0}
        >
          {selectableItems.length ? selectableItems.map((item, index) => (
            <button
              aria-selected={index === selectedIndex}
              className={index === selectedIndex ? "selected" : ""}
              id={itemDomId(item.key)}
              key={item.key}
              onClick={() => {
                setSelectedIndex(index);
                void openSelected(item);
              }}
              role="option"
              type="button"
            >
              <strong>{item.label}</strong>
              <span>{item.description}</span>
            </button>
          )) : <p className="empty-state">No artifacts recorded yet.</p>}
        </div>

        <div className="artifact-preview-panel">
          <div className="artifact-preview-title">
            <strong>{previewTitle}</strong>
            {selectedArtifact ? <a href={artifactDownloadUrl(selectedArtifact.path)}>Download</a> : null}
          </div>
          <pre tabIndex={0}>{preview}</pre>
        </div>
      </div>

      <div className="artifact-action-bar" aria-label="Artifact actions">
        <button
          disabled={!selectedArtifact || busy !== null}
          onClick={() => selectedArtifact && void runAction("markdown", async () => {
            const exported = await exportArtifact(selectedArtifact.path, "markdown");
            return `Markdown export created: ${exported.path}`;
          })}
          type="button"
        >
          Export Markdown
        </button>
        <button
          disabled={!selectedArtifact || busy !== null}
          onClick={() => selectedArtifact && void runAction("pdf", async () => {
            const exported = await exportArtifact(selectedArtifact.path, "pdf");
            return `PDF export created: ${exported.path}`;
          })}
          type="button"
        >
          Export PDF
        </button>
        <button
          disabled={runIds.length < 2 || busy !== null}
          onClick={() => void runAction("compare", async () => {
            const comparison = await compareBenchmarkRuns(runIds.slice(0, 5));
            setPreviewTitle(`Benchmark comparison · ${comparison.run_ids.join(", ")}`);
            setPreview(JSON.stringify(comparison.rows, null, 2));
            return `Compared ${comparison.run_ids.length} benchmark runs.`;
          })}
          type="button"
        >
          Compare Runs
        </button>
        <button
          disabled={!primaryIncidentId || busy !== null}
          onClick={() => primaryIncidentId && void runAction("replay", async () => {
            const replay = await replayIncidentWindow(primaryIncidentId);
            setPreviewTitle(`Incident replay · ${replay.incident_id}`);
            setPreview(JSON.stringify(replay, null, 2));
            return `Loaded replay window for ${replay.incident_id}.`;
          })}
          type="button"
        >
          Replay Incident
        </button>
        <button
          disabled={busy !== null}
          onClick={() => void runAction("screenshot", async () => {
            const screenshot = await attachNebiusScreenshot();
            return `Attached screenshot evidence ${screenshot.id}: ${screenshot.path}`;
          })}
          type="button"
        >
          Attach Screenshots
        </button>
        <button
          disabled={!primaryRunId || busy !== null}
          onClick={() => primaryRunId && void runAction("promote", async () => {
            const promoted = await promoteBenchmarkRun(primaryRunId);
            return `Promoted ${promoted.run_id}: ${promoted.path}`;
          })}
          type="button"
        >
          Promote Evidence
        </button>
      </div>
      {message ? <p className="artifact-action-message">{message}</p> : null}
    </section>
  );
}

function itemDomId(key: string) {
  return `artifact-${key.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}
