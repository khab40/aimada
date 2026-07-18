import type { ExchangeEvent } from "@/types/arena";

const MAX_VISIBLE_EVENTS = 18;

export function ExchangeEventTape({ events }: { events: ExchangeEvent[] }) {
  const visibleEvents = [...events].reverse().slice(0, MAX_VISIBLE_EVENTS);
  const latestSequence = events.at(-1)?.sequence;

  return (
    <section className="exchange-event-tape" aria-label="Canonical exchange event tape">
      <header>
        <div>
          <h2>Exchange Event Tape</h2>
          <p>Canonical simulation stream · newest first</p>
        </div>
        <span>{latestSequence ? `Seq ${latestSequence}` : "Waiting"}</span>
      </header>
      {!visibleEvents.length ? <div className="empty-state">No canonical exchange events yet.</div> : null}
      <ol>
        {visibleEvents.map((event) => (
          <li className={`exchange-event-row ${event.event_type}`} key={event.event_id}>
            <span className="exchange-sequence">#{event.sequence}</span>
            <strong>{event.event_type}</strong>
            <span className="exchange-event-summary">{formatExchangeEvent(event)}</span>
            <span className="exchange-event-context">{event.venue} · {event.symbol} · tick {event.tick ?? "—"}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function formatExchangeEvent(event: ExchangeEvent) {
  if (event.event_type === "snapshot") {
    return `L2 depth ${event.depth} · ${event.book.bids.length} bid / ${event.book.asks.length} ask levels`;
  }
  if (event.event_type === "execute") {
    return `${event.side.toUpperCase()} ${formatQuantity(event.quantity)} @ ${formatPrice(event.price)} · ${shortId(event.execution_id)}`;
  }
  if (event.event_type === "modify") {
    const priority = event.priority_preserved ? "priority kept" : "priority reset";
    return `${event.side.toUpperCase()} ${formatQuantity(event.previous_quantity)}→${formatQuantity(event.quantity)} @ ${formatPrice(event.previous_price)}→${formatPrice(event.price)} · ${priority}`;
  }
  return `${event.side.toUpperCase()} ${formatQuantity(event.quantity)} @ ${formatPrice(event.price)} · ${shortId(event.order_id)}`;
}

function formatPrice(value: number) {
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function formatQuantity(value: number) {
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function shortId(value: string) {
  return value.length > 22 ? `${value.slice(0, 10)}…${value.slice(-8)}` : value;
}
