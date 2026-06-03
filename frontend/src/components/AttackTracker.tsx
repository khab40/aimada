import type { AttackStage, AttackStageSnapshot, AttackTrackerState } from "@/types/arena";

const defaultStages: AttackStageSnapshot[] = [
  { label: "Armed", stage: "armed", status: "pending" },
  { label: "Wall Placed", stage: "wall_placed", status: "pending" },
  { label: "Pressure Phase", stage: "pressure_phase", status: "pending" },
  { label: "Wall Cancelled", stage: "wall_cancelled", status: "pending" },
  { label: "Incident Confirmed", stage: "incident_confirmed", status: "pending" },
  { label: "Done", stage: "done", status: "pending" }
];

const stageOrder: AttackStage[] = defaultStages.map((stage) => stage.stage);

export function AttackTracker({ attack }: { attack?: AttackTrackerState | null }) {
  if (!attack) {
    return (
      <section className="attack-tracker">
        <h2>Attack Tracker</h2>
        <div className="attack-card empty">
          <strong>No active red-team scenario</strong>
          <small>Launch a scenario to see the spoofing-like wall state machine.</small>
        </div>
      </section>
    );
  }

  const stages = normaliseStages(attack);

  return (
    <section className="attack-tracker">
      <div className="section-heading-row">
        <h2>Attack Tracker</h2>
        <span>{formatScenarioName(attack.scenario_name)}</span>
      </div>
      <div className="attack-card">
        <span>Agent</span>
        <strong>{attack.agent_id}</strong>
        <small>{attack.scenario_id}</small>
      </div>
      <ol className="attack-stage-list">
        {stages.map((stage) => (
          <li className={`attack-stage ${stage.status}`} key={stage.stage}>
            <div className="attack-stage-marker" aria-hidden="true" />
            <div>
              <strong>{stage.label}</strong>
              <small>{stage.status}</small>
            </div>
            <div className="attack-stage-meta">
              <span>{formatTimestamp(stage.timestamp)}</span>
              <span>{formatConfidence(stage.detector_confidence)}</span>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function normaliseStages(attack: AttackTrackerState) {
  if (attack.stages?.length) {
    return attack.stages;
  }

  const currentStage = stageOrder.includes(attack.status as AttackStage)
    ? attack.status as AttackStage
    : attack.current_stage;
  const currentIndex = currentStage ? stageOrder.indexOf(currentStage) : -1;

  return defaultStages.map((stage, index) => ({
    ...stage,
    status: index < currentIndex ? "completed" : index === currentIndex ? "active" : "pending"
  }));
}

function formatScenarioName(name: string) {
  return name
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTimestamp(timestamp?: number | null) {
  return timestamp ? new Date(timestamp).toLocaleTimeString() : "timestamp pending";
}

function formatConfidence(confidence?: number | null) {
  return confidence == null ? "confidence pending" : `confidence ${confidence.toFixed(2)}`;
}
