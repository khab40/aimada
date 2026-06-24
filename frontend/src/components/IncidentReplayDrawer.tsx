import { useEffect, useState } from "react";
import { NebiusAIInvestigatorPanel } from "@/components/NebiusAIInvestigatorPanel";
import type { Incident } from "@/types/arena";

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

export function IncidentReplayDrawer({
  activeIncident,
  currentTick,
  incidentTick,
  live = true
}: {
  activeIncident?: Incident | null;
  currentTick?: number;
  incidentTick?: number;
  live?: boolean;
}) {
  const [closedIncidentId, setClosedIncidentId] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    setStepIndex(0);
    setClosedIncidentId(null);
  }, [activeIncident?.id]);

  if (!activeIncident || closedIncidentId === activeIncident.id) {
    return (
      <aside className="incident-replay-drawer empty">
        <div className="section-heading-row">
          <h2>Incidents</h2>
          <span>{currentTick === undefined ? "no tick" : `current T${currentTick}`}</span>
        </div>
        <p>No active incident replay.</p>
      </aside>
    );
  }

  const activeStep = replaySteps[stepIndex];
  const baseTick = incidentTick ?? activeIncident.tick ?? currentTick;

  return (
    <aside className="incident-replay-drawer">
      <div className="section-heading-row incident-widget-heading">
        <h2>Incidents</h2>
        <span>{baseTick === undefined ? "tick n/a" : `${live ? "live" : "last"} T${baseTick}`}</span>
      </div>

      <div className="section-heading-row incident-title-row">
        <h3>{activeIncident.title}</h3>
        <span className={`severity-chip ${activeIncident.severity.toLowerCase()}`}>
          {live ? activeIncident.severity : `Last ${activeIncident.severity}`}
        </span>
      </div>

      <dl className="incident-replay-meta">
        <div><dt>Confidence</dt><dd>{activeIncident.confidence.toFixed(2)}</dd></div>
        <div><dt>Type</dt><dd>{activeIncident.type}</dd></div>
        <div><dt>Agent</dt><dd>{activeIncident.agent}</dd></div>
        <div><dt>Tick</dt><dd>{baseTick === undefined ? "n/a" : `T${baseTick}`}</dd></div>
      </dl>

      <section className="incident-evidence-summary">
        <h3>Evidence Summary</h3>
        <ul>
          {activeIncident.evidence.map((item) => (
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
        <button type="button" onClick={() => setClosedIncidentId(activeIncident.id)}>Close</button>
      </div>

      <NebiusAIInvestigatorPanel incident={activeIncident} />
    </aside>
  );
}

function formatReplayTick(baseTick: number | undefined, offset: number) {
  if (baseTick === undefined) {
    return offset === 0 ? "T+0" : offset > 0 ? `T+${offset}` : `T${offset}`;
  }
  return `T${Math.max(0, baseTick + offset)}`;
}
