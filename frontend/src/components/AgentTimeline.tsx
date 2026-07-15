import type { AgentEvent } from "@/types/arena";

type AgentEventKind = "normal" | "market_maker" | "red_team" | "detector" | "nebius";
type AgentTimelineLayout = "compact" | "full";

const eventLabels: Record<AgentEventKind, string> = {
  detector: "detector",
  market_maker: "market maker",
  nebius: "nebius",
  normal: "normal",
  red_team: "red team"
};

export function AgentTimeline({
  activeAgents = [],
  events,
  layout = "full",
  limit = layout === "compact" ? 12 : 20,
  title = "Agent Timeline"
}: {
  activeAgents?: string[];
  events: AgentEvent[];
  layout?: AgentTimelineLayout;
  limit?: number;
  title?: string;
}) {
  const latestEvents = [...events].sort((left, right) => (
    eventTick(right) - eventTick(left)
  )).slice(0, limit);

  return (
    <section className={`agent-timeline ${layout}`}>
      <div className="section-heading-row">
        <h2>{title}</h2>
        <span>Last {latestEvents.length} events</span>
      </div>
      <div className="agent-timeline-context" role="note">
        <div>
          <span>Clock · simulation ticks</span>
          <span>Venue · synthetic LOB</span>
          <span>Runtime · {getRuntimeLabel(events, activeAgents)}</span>
        </div>
        <p>Software-agent actions inside the simulator. No orders are routed to a real exchange.</p>
      </div>
      {!latestEvents.length ? <div className="empty-state">No timeline events yet.</div> : null}
      <ul className="event-tape">
        {latestEvents.map((event, index) => {
          const kind = getEventKind(event);
          return (
            <li className={`event-tape-item ${kind}`} key={`${event.timestamp ?? "event"}-${index}`}>
              <div className="event-tape-topline">
                <span className={`event-badge ${kind}`}>{eventLabels[kind]}</span>
                <time title="Simulation tick">{formatSimulationTick(eventTick(event))}</time>
              </div>
              <div className="event-agent-row">
                <strong>{event.agent_id ?? event.aggressor_agent_id ?? "exchange"}</strong>
                <span className="event-runtime-source">{getEventSourceLabel(event, kind)}</span>
              </div>
              {layout === "full" ? <small>{formatEvent(event)}</small> : null}
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

function formatSimulationTick(timestamp?: number) {
  return typeof timestamp === "number" && Number.isFinite(timestamp)
    ? `T${Math.max(0, Math.floor(timestamp))}`
    : "tick pending";
}

function eventTick(event: AgentEvent) {
  return Number(event.tick ?? event.timestamp ?? 0);
}

function getRuntimeLabel(events: AgentEvent[], activeAgents: string[]) {
  const runnerConfigured = activeAgents.some((agentId) => agentId.startsWith("remote_runner:"));
  const runnerActive = events.some((event) => event.runtime_source === "agent_runner" || event.agent_id?.startsWith("REMOTE_"));
  if (runnerActive) {
    return "backend + Agent Runner";
  }
  return runnerConfigured ? "backend + Agent Runner configured" : "backend simulator";
}

function getEventSourceLabel(event: AgentEvent, kind: AgentEventKind) {
  if (event.runtime_source === "agent_runner" || event.agent_id?.startsWith("REMOTE_")) {
    return "Agent Runner";
  }
  if (kind === "red_team") {
    return "Scenario engine";
  }
  if (kind === "detector") {
    return "Detector engine";
  }
  if (kind === "nebius") {
    return "Nebius AI";
  }
  return "Backend agent";
}
