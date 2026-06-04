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
          <p className="eyebrow">3D market heatmap concept</p>
          <h2>Market Abuse Battlefield</h2>
          <p>
            A live terrain view of the same exchange ticker used by Arena: price across the valley,
            simulation time into the screen, liquidity as height, and anomaly risk as heat.
          </p>
        </div>
        <span className="endpoint-badge">LOB terrain prototype</span>
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
