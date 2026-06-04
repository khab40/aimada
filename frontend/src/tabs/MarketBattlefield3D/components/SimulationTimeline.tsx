import type { BattlefieldEvent, BattlefieldFrame } from "../types";

const eventLabels: Record<BattlefieldEvent["type"], string> = {
  CANCEL_BURST: "Cancel",
  DETECTION: "Detect",
  PRICE_MOVE: "Move",
  SPOOF_ORDER: "Wall"
};

export function SimulationTimeline({
  currentTick,
  events,
  frames,
  onTickSelect
}: {
  currentTick: number;
  events: BattlefieldEvent[];
  frames: BattlefieldFrame[];
  onTickSelect: (tick: number) => void;
}) {
  return (
    <section className="battlefield-timeline panel">
      <div className="section-heading-row">
        <h2>Attack Replay Timeline</h2>
        <span>{frames.length} ticks</span>
      </div>
      <div className="battlefield-tick-rail">
        {frames.map((frame) => {
          const index = frames.indexOf(frame);
          const event = events.find((item) => item.tick === frame.tick);
          return (
            <button
              aria-label={`Go to tick ${frame.tick}`}
              className={`battlefield-tick ${frame.tick === currentTick ? "active" : ""} ${event ? "has-event" : ""}`}
              key={frame.tick}
              onClick={() => onTickSelect(index)}
              title={event?.description ?? `Tick ${frame.tick}`}
              type="button"
            >
              {event ? eventLabels[event.type] : ""}
            </button>
          );
        })}
      </div>
    </section>
  );
}
