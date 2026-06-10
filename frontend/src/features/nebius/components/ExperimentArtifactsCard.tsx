import type { ExperimentArtifact } from "@/features/nebius/types";
import { ArtifactWorkbench } from "@/components/ArtifactWorkbench";

type ExperimentArtifactsCardProps = {
  artifacts: ExperimentArtifact[];
  incidentIds?: string[];
  onSaveReplay: () => void;
  onLoadPrevious: () => void;
  onExportDataset: () => void;
  onGenerateTrainingData: () => void;
  runIds?: string[];
};

export function ExperimentArtifactsCard({
  artifacts,
  incidentIds = [],
  onExportDataset,
  onGenerateTrainingData,
  onLoadPrevious,
  onSaveReplay,
  runIds = []
}: ExperimentArtifactsCardProps) {
  return (
    <section className="panel experiment-artifacts-card">
      <div className="nebius-card-heading">
        <div>
          <p className="eyebrow">Replay Storage</p>
          <h2>Experiment Artifacts</h2>
        </div>
      </div>
      <p className="nebius-card-purpose">Store and reload simulation evidence: replay files, metrics, alerts, incident reports, and generated LOB datasets.</p>
      <div className="nebius-button-row">
        <button onClick={onSaveReplay} type="button">Save Current Replay</button>
        <button onClick={onLoadPrevious} type="button">Load Previous Experiment</button>
        <button onClick={onExportDataset} type="button">Export Dataset</button>
        <button onClick={onGenerateTrainingData} type="button">Generate Training Data</button>
      </div>
      <ArtifactWorkbench
        artifacts={artifacts.map((artifact) => ({
          description: `${artifact.type} · ${artifact.sizeLabel} · ${artifact.status}`,
          label: artifact.path.split("/").at(-1) ?? artifact.path,
          path: artifact.path
        }))}
        incidentIds={incidentIds}
        runIds={runIds}
        selectedRunId={runIds[0] ?? null}
        title="Control Panel Artifacts"
      />
    </section>
  );
}
