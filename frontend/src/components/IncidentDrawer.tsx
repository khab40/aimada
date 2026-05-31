import type { Incident } from "../types/incident";

export function IncidentDrawer({ incident }: { incident?: Incident }) {
  return (
    <aside>
      <h2>Incident</h2>
      <pre>{JSON.stringify(incident ?? null, null, 2)}</pre>
    </aside>
  );
}
