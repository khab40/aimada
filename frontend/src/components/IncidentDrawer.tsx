import { useEffect, useState } from "react";
import { NebiusAIInvestigatorPanel } from "@/components/NebiusAIInvestigatorPanel";
import type { Incident } from "@/types/arena";

type IncidentDetailsMode = "live" | "replay";

type ReplayStep = {
  label: string;
  tickOffset: number;
  summary: string;
};

const replaySteps: ReplayStep[] = [
  { label: "Normal", tickOffset: -5, summary: "Baseline two-sided liquidity and normal message flow." },
  { label: "Wall Placed", tickOffset: -2, summary: "Large visible ask-side wall appears near the top of book." },
  { label: "Warning", tickOffset: 0, summary: "Detector confidence crosses warning threshold." },
  { label: "Cancelled", tickOffset: 2, summary: "Synthetic wall is removed before meaningful execution." },
  { label: "Confirmed", tickOffset: 5, summary: "Evidence bundle confirms the mock incident." }
];

export function IncidentDrawer({
  currentTick,
  incident,
  incidentTick,
  mode = "live"
}: {
  currentTick?: number;
  incident?: Incident | null;
  incidentTick?: number;
  mode?: IncidentDetailsMode;
}) {
  const [closedIncidentId, setClosedIncidentId] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    setStepIndex(0);
    setClosedIncidentId(null);
  }, [incident?.id]);

  if (!incident || closedIncidentId === incident.id) {
    return (
      <aside className="incident-replay-drawer empty">
        <div className="section-heading-row">
          <h2>Incident Details</h2>
          <span>{currentTick === undefined ? "no tick" : `current T${currentTick}`}</span>
        </div>
        <p>No incident detected yet. Run a scenario or wait for an alert.</p>
      </aside>
    );
  }

  const activeStep = replaySteps[stepIndex];
  const baseTick = incidentTick ?? incident.tick ?? currentTick;
  const live = mode === "live";

  return (
    <aside className="incident-replay-drawer">
      <div className="section-heading-row incident-widget-heading">
        <h2>Incident Details</h2>
        <span>{baseTick === undefined ? "tick n/a" : `${mode} T${baseTick}`}</span>
      </div>

      <div className="section-heading-row incident-title-row">
        <h3>{incident.title}</h3>
        <span className={`severity-chip ${incident.severity.toLowerCase()}`}>
          {live ? incident.severity : `Last ${incident.severity}`}
        </span>
      </div>

      <dl className="incident-replay-meta">
        <div><dt>Confidence</dt><dd>{incident.confidence.toFixed(2)}</dd></div>
        <div><dt>Type</dt><dd>{incident.type}</dd></div>
        <div><dt>Agent</dt><dd>{incident.agent}</dd></div>
        <div><dt>Tick</dt><dd>{baseTick === undefined ? "n/a" : `T${baseTick}`}</dd></div>
      </dl>

      <section className="incident-evidence-summary">
        <h3>Evidence Summary</h3>
        <ul>
          {incident.evidence.map((item) => (
            <li key={item.key}>
              <strong>{item.label}: </strong>
              {String(item.value)}
              {item.unit ? ` ${item.unit}` : ""}
            </li>
          ))}
        </ul>
      </section>

      <section className="incident-replay-timeline">
        <h3>Replay Timeline</h3>
        <ol>
          {replaySteps.map((step, index) => (
            <li className={index === stepIndex ? "active" : index < stepIndex ? "completed" : "pending"} key={step.label}>
              <span>{formatReplayTick(baseTick, step.tickOffset)}</span>
              <strong>{step.label}</strong>
            </li>
          ))}
        </ol>
        <p>
          <strong>{formatReplayTick(baseTick, activeStep.tickOffset)} {activeStep.label}: </strong>
          {activeStep.summary}
        </p>
      </section>

      <div className="incident-replay-controls">
        <button type="button" onClick={() => setStepIndex(0)}>Replay</button>
        <button type="button" onClick={() => setStepIndex((value) => Math.max(0, value - 1))}>Step Back</button>
        <button type="button" onClick={() => setStepIndex((value) => Math.min(replaySteps.length - 1, value + 1))}>Step Forward</button>
        <button type="button" onClick={() => setClosedIncidentId(incident.id)}>Close</button>
      </div>

      <NebiusAIInvestigatorPanel incident={incident} />
    </aside>
  );
}

function formatReplayTick(baseTick: number | undefined, offset: number) {
  if (baseTick === undefined) {
    return offset === 0 ? "T+0" : offset > 0 ? `T+${offset}` : `T${offset}`;
  }
  return `T${Math.max(0, baseTick + offset)}`;
}
