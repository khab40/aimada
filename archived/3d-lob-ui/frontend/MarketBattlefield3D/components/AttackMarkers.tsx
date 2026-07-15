import type { BattlefieldEvent } from "../types";

export function AttackMarkers({ currentTick, events }: { currentTick: number; events: BattlefieldEvent[] }) {
  const visibleEvents = events.filter((event) => event.tick <= currentTick).slice(-5).reverse();

  return (
    <section className="battlefield-events panel">
      <div className="section-heading-row">
        <h2>Red vs Blue Event Log</h2>
        <span>{visibleEvents.length} visible</span>
      </div>
      <ol>
        {visibleEvents.length ? visibleEvents.map((event) => (
          <li className={event.type.toLowerCase()} key={`${event.tick}-${event.type}`}>
            <span>T+{event.tick}</span>
            <strong>{event.type.replaceAll("_", " ")}</strong>
            <p>{event.description}</p>
          </li>
        )) : <li className="empty">No attack events visible yet.</li>}
      </ol>
    </section>
  );
}
