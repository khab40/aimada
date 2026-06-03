import type { Incident } from "@/types/arena";

export function IncidentDrawer({ incident }: { incident?: Incident }) {
  if (!incident) {
    return (
      <aside className="incident-drawer empty">
        <h2>Incident Drawer</h2>
        <p>No detector alert is active.</p>
      </aside>
    );
  }

  return (
    <aside className="incident-drawer">
      <h2>{incident.title}</h2>
      <dl>
        <div><dt>Type</dt><dd>{incident.type}</dd></div>
        <div><dt>Agent</dt><dd>{incident.agent}</dd></div>
        <div><dt>Confidence</dt><dd>{incident.confidence.toFixed(2)}</dd></div>
        <div><dt>Severity</dt><dd>{incident.severity}</dd></div>
      </dl>
      <h3>Evidence</h3>
      <ul>
        {incident.evidence.map((item) => (
          <li key={item.key}>
            <strong>{item.label}: </strong>
            {String(item.value)}
            {item.unit ? ` ${item.unit}` : ""}
          </li>
        ))}
      </ul>
      <h3>Explanation</h3>
      <p>{incident.explanation}</p>
    </aside>
  );
}
