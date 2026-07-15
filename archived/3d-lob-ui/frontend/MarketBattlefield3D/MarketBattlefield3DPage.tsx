import { AgentOverlay } from "./components/AgentOverlay";
import { AttackMarkers } from "./components/AttackMarkers";
import { ControlsPanel } from "./components/ControlsPanel";
import { DetectionPanel } from "./components/DetectionPanel";
import { OrderBookTerrain } from "./components/OrderBookTerrain";
import { SimulationTimeline } from "./components/SimulationTimeline";
import { useMarketBattlefieldData } from "./hooks/useMarketBattlefieldData";

export function MarketBattlefield3DPage() {
  const {
    events,
    frame,
    frames,
    pause,
    play,
    playbackState,
    reset,
    selectedIndex,
    setSelectedIndex,
    visibleFrames
  } = useMarketBattlefieldData();

  return (
    <section className="battlefield-page">
      <div className="panel battlefield-hero">
        <div>
          <h2>Market Abuse Battlefield</h2>
        </div>
      </div>

      <div className="battlefield-grid">
        <div className="battlefield-main panel">
          <OrderBookTerrain currentTick={frame.tick} frames={visibleFrames} />
        </div>

        <aside className="battlefield-side">
          <DetectionPanel frame={frame} />
          <AgentOverlay />
          <AttackMarkers currentTick={frame.tick} events={events} />
        </aside>

        <div className="battlefield-bottom">
          <ControlsPanel
            maxTick={frames.length - 1}
            onPause={pause}
            onPlay={play}
            onReset={reset}
            onTickChange={setSelectedIndex}
            playbackState={playbackState}
            sliderValue={selectedIndex}
            tick={frame.tick}
          />
          <SimulationTimeline currentTick={frame.tick} events={events} frames={frames} onTickSelect={setSelectedIndex} />
        </div>
      </div>
    </section>
  );
}
