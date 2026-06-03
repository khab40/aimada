import type { AgentEvent } from "@/types/arena";

type AgentEventKind = "normal" | "market_maker" | "red_team" | "detector" | "nebius";

const eventLabels: Record<AgentEventKind, string> = {
  detector: "detector",
  market_maker: "market maker",
  nebius: "nebius",
  normal: "normal",
  red_team: "red team"
};

export function AgentEventTape({ events }: { events: AgentEvent[] }) {
  const latestEvents = [...events].sort((left, right) => (
    Number(right.timestamp ?? 0) - Number(left.timestamp ?? 0)
  )).slice(0, 20);

  return (
    <section className="agent-event-tape">
      <div className="section-heading-row">
        <h2>Agent Event Tape</h2>
        <span>Last {latestEvents.length} events</span>
      </div>
      {!latestEvents.length ? <div className="empty-state">No agent events yet.</div> : null}
      <ul className="event-tape">
        {latestEvents.map((event, index) => {
          const kind = getEventKind(event);
          return (
            <li className={`event-tape-item ${kind}`} key={`${event.timestamp ?? "event"}-${index}`}>
              <div className="event-tape-topline">
                <span className={`event-badge ${kind}`}>{eventLabels[kind]}</span>
                <time>{formatTimestamp(event.timestamp)}</time>
              </div>
              <strong>{event.agent_id ?? event.aggressor_agent_id ?? "exchange"}</strong>
              <small>{formatEvent(event)}</small>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function getEventKind(event: AgentEvent): AgentEventKind {
  if (event.kind === "nebius" || event.type.includes("nebius")) {
    return "nebius";
  }
  if (event.kind === "detector" || event.type.includes("detector") || event.type.includes("alert")) {
    return "detector";
  }
  if (event.kind === "red_team" || event.scenario_name || event.scenario_family || event.type.includes("scenario")) {
    return "red_team";
  }
  if (event.kind === "market_maker" || event.agent_id === "MarketMakerAgent") {
    return "market_maker";
  }
  return "normal";
}

function formatEvent(event: AgentEvent) {
  const price = typeof event.price === "number" ? ` @ ${event.price.toFixed(2)}` : "";
  const quantity = typeof event.quantity === "number" ? ` size ${event.quantity.toFixed(3)}` : "";
  const side = event.side ? ` ${event.side}` : "";
  const scenario = event.scenario_name ? ` [${formatScenario(event.scenario_name)}]` : "";
  return `${event.type}${scenario}${side}${quantity}${price}`;
}

function formatScenario(name: string) {
  return name
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatTimestamp(timestamp?: number) {
  return timestamp ? new Date(timestamp).toLocaleTimeString() : "time pending";
}
