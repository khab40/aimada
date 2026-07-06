import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AttackBuilder } from "@/components/AttackBuilder";
import { AttackTracker } from "@/components/AttackTracker";
import { AgentTimeline } from "@/components/AgentTimeline";
import { DetectorConfidence } from "@/components/DetectorConfidence";
import { EvidencePanel } from "@/components/EvidencePanel";
import { IncidentDrawer } from "@/components/IncidentDrawer";
import { LiquidityHeatmap } from "@/components/LiquidityHeatmap";
import { MarketTimeline, type MarketTimelineFrame, type TimelineMarkerType } from "@/components/MarketTimeline";
import { OrderBookLadder } from "@/components/OrderBookLadder";
import { useArenaSource } from "@/hooks/useArenaSource";
import { getProductDemoConfig, type ProductDemoConfig } from "@/demoModes";
import { OrderBookTerrain } from "@/tabs/MarketBattlefield3D/components/OrderBookTerrain";
import { arenaStateToFrame } from "@/tabs/MarketBattlefield3D/hooks/useMarketBattlefieldData";
import type { BattlefieldFrame } from "@/tabs/MarketBattlefield3D/types";
import type { ArenaState, Incident, OrderBookSnapshot } from "@/types/arena";

const WIDGET_TICK_WINDOW = 48;

type HeatmapSnapshotFrame = {
  book: OrderBookSnapshot;
  tick: number;
};

type ArenaVisualizationMode = "standard" | "battlefield";
type DetectionSecondaryView = "evidence" | "timeline";
type MarketSecondaryView = "heatmap" | "timeline";

const scenarioLabels: Record<string, string> = Object.fromEntries(
  [
    ["spoofing_like_wall", "Spoofing-like Wall"],
    ["layering_like", "Layering-like Pattern"],
    ["quote_stuffing", "Quote Stuffing Burst"],
    ["liquidity_evaporation", "Liquidity Evaporation"]
  ]
);

function formatScenarioLabel(name?: string | null) {
  return name ? scenarioLabels[name] ?? name : "None";
}

export function ArenaPage() {
  const [searchParams] = useSearchParams();
  const demoConfig = getProductDemoConfig(searchParams.get("demo"));
  const { launchScenario, mode, pause, reset, running, sourceStatus, start, state, tick } = useArenaSource({
    demo: Boolean(demoConfig),
    demoScenario: demoConfig?.scenarioType,
    symbol: demoConfig?.marketSymbol
  });
  const [visualizationMode] = useState<ArenaVisualizationMode>("standard");
  const [secondaryView, setSecondaryView] = useState<DetectionSecondaryView>("evidence");
  const [marketSecondaryView, setMarketSecondaryView] = useState<MarketSecondaryView>("heatmap");
  const [heatmapSnapshots, setHeatmapSnapshots] = useState<HeatmapSnapshotFrame[]>(() => [toHeatmapSnapshotFrame(state)]);
  const [battlefieldFrames, setBattlefieldFrames] = useState<BattlefieldFrame[]>(() => [arenaStateToFrame(state)]);
  const [timeline, setTimeline] = useState<MarketTimelineFrame[]>(() => [toTimelineFrame(state)]);
  const lastRecordedTickRef = useRef(state.tick);
  const [pendingControl, setPendingControl] = useState<"pause" | "reset" | "start" | null>(null);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [incidentDetailsMode, setIncidentDetailsMode] = useState<"live" | "replay">("live");
  const incident = useMemo(() => createIncident(state), [state]);
  const [lastIncident, setLastIncident] = useState<Incident | null>(incident);
  const loading = mode === "websocket" && sourceStatus === "connecting";
  const connected = mode === "demo" || mode === "mock" || sourceStatus === "connected";
  const canReset = tick > 0 || running || state.events.length > 0 || Boolean(state.active_scenario) || Boolean(state.incidents?.length);

  useEffect(() => {
    if (incident) {
      setLastIncident(incident);
    }
  }, [incident]);

  useEffect(() => {
    if (state.tick === lastRecordedTickRef.current) {
      return;
    }
    lastRecordedTickRef.current = state.tick;
    setHeatmapSnapshots((snapshots) => [...snapshots, toHeatmapSnapshotFrame(state)].slice(-WIDGET_TICK_WINDOW));
    setBattlefieldFrames((frames) => [...frames, arenaStateToFrame(state)].slice(-WIDGET_TICK_WINDOW));
    setTimeline((points) => [...points, toTimelineFrame(state)].slice(-WIDGET_TICK_WINDOW));
  }, [state]);

  useEffect(() => {
    setPendingControl(null);
  }, [running, sourceStatus, tick]);

  const startArena = useCallback(() => {
    if (running || !connected) {
      return;
    }
    setPendingControl("start");
    start();
  }, [connected, running, start]);

  const pauseArena = useCallback(() => {
    if (!running || !connected) {
      return;
    }
    setPendingControl("pause");
    pause();
  }, [connected, pause, running]);

  const resetArena = useCallback(() => {
    if (!canReset || !connected) {
      return;
    }
    setPendingControl("reset");
    reset();
    lastRecordedTickRef.current = -1;
    setHeatmapSnapshots([]);
    setBattlefieldFrames([]);
    setTimeline([]);
    setLastIncident(null);
  }, [canReset, connected, reset]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target;
      if (isEditableTarget(target)) {
        return;
      }

      const key = event.key.toLowerCase();
      if (key === " ") {
        event.preventDefault();
        if (running) {
          pauseArena();
        } else {
          startArena();
        }
      }
      if (key === "s") {
        startArena();
      }
      if (key === "q") {
        pauseArena();
      }
      if (key === "r") {
        resetArena();
      }
      if (key === "l") {
        setIncidentDetailsMode((value) => value === "live" ? "replay" : "live");
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [pauseArena, resetArena, running, startArena]);

  return (
    <section className={`cockpit-page ${incident ? "incident-active" : ""}`} aria-label="Market workload generator">
      <TopStatusBar
        onPause={pauseArena}
        onReset={resetArena}
        onStart={startArena}
        canReset={canReset}
        connected={connected}
        pendingControl={pendingControl}
        running={running}
        selectedScenario={formatScenarioLabel(state.active_scenario?.scenario_name)}
        tick={tick}
        source={mode === "websocket" ? `backend websocket:${sourceStatus}` : mode === "demo" ? demoConfig?.title ?? "demo mode" : `local mock:${sourceStatus}`}
      />

      <div className="shortcut-help">
        <button
          aria-expanded={shortcutsOpen}
          aria-label="Keyboard shortcuts"
          className="shortcut-help-button"
          onClick={() => setShortcutsOpen((value) => !value)}
          type="button"
        >
          ?
        </button>
        {shortcutsOpen ? (
          <div className="shortcut-popover" role="dialog" aria-label="Keyboard shortcuts">
            <span><kbd>Space</kbd> start/pause</span>
            <span><kbd>S</kbd> start</span>
            <span><kbd>Q</kbd> pause</span>
            <span><kbd>R</kbd> reset</span>
            <span><kbd>L</kbd> live/replay</span>
          </div>
        ) : null}
      </div>

      {loading ? (
        <div className="loading-banner" role="status">
          Connecting to arena WebSocket source...
        </div>
      ) : null}

      {mode === "websocket" && (sourceStatus === "disconnected" || sourceStatus === "error") ? (
        <div className="empty-state warning" role="status">
          WebSocket arena source is {sourceStatus}. Switch `VITE_ARENA_MODE=mock` or start the backend stream.
        </div>
      ) : null}

      {incident ? (
        <div className="incident-alert-banner" role="alert">
          Incident alert: {incident.title} | confidence {incident.confidence.toFixed(2)}
        </div>
      ) : null}

      {demoConfig ? <ArenaDemoBanner config={demoConfig} /> : null}

      <div className="cockpit-grid">
        <section className="panel cockpit-left arena-column">
          <header className="arena-column-header">
            <h2>Scenario Setup</h2>
          </header>
          <AttackTracker attack={state.active_scenario} />
          <AttackBuilder onLaunchScenario={launchScenario} />
        </section>

        <section className="panel cockpit-center arena-column">
          <header className="arena-column-header market-visualization-header">
            <div>
              <h2>Market Workload Generator</h2>
              <div className="market-microstructure-strip" aria-label="Market microstructure metrics">
                <MetricPill label="Mid" value={formatNumber(state.mid)} />
                <MetricPill label="Spread" value={formatNumber(state.spread)} />
              </div>
            </div>
          </header>
          <div className="market-mode-panel" key={visualizationMode}>
            {visualizationMode === "standard" ? (
              <>
                <OrderBookLadder snapshot={state.book} />
                <section className="market-secondary-view">
                  <div className="widget-tab-row" role="tablist" aria-label="Secondary market views">
                    <button className={marketSecondaryView === "heatmap" ? "active" : ""} onClick={() => setMarketSecondaryView("heatmap")} type="button">Heatmap</button>
                    <button className={marketSecondaryView === "timeline" ? "active" : ""} onClick={() => setMarketSecondaryView("timeline")} type="button">Timeline</button>
                  </div>
                  <div className="tab-content-panel" key={marketSecondaryView}>
                    {marketSecondaryView === "heatmap" ? (
                      <LiquidityHeatmap maxFrames={WIDGET_TICK_WINDOW} snapshots={heatmapSnapshots} visibleLevels={20} />
                    ) : (
                      <MarketTimeline frames={timeline} />
                    )}
                  </div>
                </section>
              </>
            ) : (
              <OrderBookTerrain currentTick={tick} frames={battlefieldFrames.length ? battlefieldFrames : [arenaStateToFrame(state)]} />
            )}
          </div>
        </section>

        <section className="panel cockpit-right arena-column">
          <header className="arena-column-header">
            <h2>Incidents / Investigations</h2>
          </header>
          <DetectorConfidence detectors={state.detectors} />
          <section className="secondary-widget-drawer">
            <div className="widget-tab-row" role="tablist" aria-label="Secondary detection widgets">
              <button className={secondaryView === "evidence" ? "active" : ""} onClick={() => setSecondaryView("evidence")} type="button">📄 Evidence</button>
              <button className={secondaryView === "timeline" ? "active" : ""} onClick={() => setSecondaryView("timeline")} type="button">🕒 Timeline</button>
            </div>
            <div className="tab-content-panel" key={secondaryView}>
              {secondaryView === "evidence" ? (
                <EvidencePanel state={state} />
              ) : (
                <AgentTimeline events={state.events} layout="compact" title="Timeline" />
              )}
            </div>
          </section>
          <IncidentDrawer demoConfig={demoConfig} incident={incident ?? lastIncident} currentTick={tick} incidentTick={(incident ?? lastIncident)?.tick ?? tick} mode={incident ? incidentDetailsMode : "replay"} />
        </section>
      </div>
    </section>
  );
}

function ArenaDemoBanner({ config }: { config: ProductDemoConfig }) {
  return (
    <section className="panel arena-demo-banner" aria-label="Selected demo mode">
      <div>
        <span>Demo mode</span>
        <strong>{config.title}</strong>
      </div>
      <div>
        <span>Symbol</span>
        <strong>{config.marketSymbol}</strong>
      </div>
      <div>
        <span>Attack</span>
        <strong>{config.attackPattern}</strong>
      </div>
      <div>
        <span>Detector</span>
        <strong>{config.detectorProfile}</strong>
      </div>
      <div>
        <span>AI investigation</span>
        <strong>{config.aiInvestigationMode}</strong>
      </div>
    </section>
  );
}

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  return target.isContentEditable || ["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(target.tagName);
}

function TopStatusBar({
  canReset,
  connected,
  onPause,
  onReset,
  onStart,
  pendingControl,
  running,
  selectedScenario,
  tick,
  source
}: {
  canReset: boolean;
  connected: boolean;
  onPause: () => void;
  onReset: () => void;
  onStart: () => void;
  pendingControl: "pause" | "reset" | "start" | null;
  running: boolean;
  selectedScenario: string;
  source: string;
  tick: number;
}) {
  return (
    <header className="cockpit-status-bar">
      <MetricPill label="State" value={running ? "Running" : "Paused"} tone={running ? "good" : "warn"} />
      <MetricPill label="Tick" value={String(tick)} />
      <MetricPill label="Scenario" value={selectedScenario} />
      <MetricPill label="Source" value={source} />
      <div className="cockpit-controls">
        <button className="arena-start-button" type="button" disabled={!connected || running || pendingControl !== null} onClick={onStart}>{pendingControl === "start" ? "Starting..." : "Start"}</button>
        <button className="arena-pause-button" type="button" disabled={!connected || !running || pendingControl !== null} onClick={onPause}>{pendingControl === "pause" ? "Pausing..." : "Pause"}</button>
        <button className="arena-reset-button" type="button" disabled={!connected || !canReset || pendingControl !== null} onClick={onReset}>{pendingControl === "reset" ? "Resetting..." : "Reset"}</button>
      </div>
    </header>
  );
}

function MetricPill({ label, tone, value }: { label: string; tone?: "good" | "warn"; value: string }) {
  return (
    <div className={`cockpit-pill ${tone ?? ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function createIncident(state: ArenaState): Incident | null {
  if (state.incidents?.length) {
    return state.incidents[state.incidents.length - 1];
  }

  const alert = state.detectors.alerts[0];
  const scenario = state.active_scenario;
  if (!alert || !scenario || !state.features) {
    return null;
  }

  return {
    agent: scenario.agent_id,
    confidence: alert.confidence,
    evidence: [
      { key: "message_rate", label: "Message rate", value: state.features.message_rate ?? 0, unit: "updates/sec" },
      { key: "wall_size_ratio", label: "Wall size ratio", value: state.features.wall_size_ratio ?? 0 },
      { key: "spread_bps", label: "Spread", value: state.features.spread_bps ?? 0, unit: "bps" },
      { key: "depth_change_pct", label: "Depth change", value: state.features.depth_change_pct ?? 0, unit: "%" }
    ],
    explanation: `${scenarioLabels[scenario.scenario_name] ?? scenario.scenario_name} is active in the mock arena and has raised the ${alert.name} detector score.`,
    id: `MOCK-${scenario.scenario_id}-${alert.name}`,
    scenario_family: scenario.scenario_family,
    scenario_id: scenario.scenario_id,
    tick: state.tick,
    severity: alert.severity === "critical" ? "Critical" : alert.severity === "high" ? "High" : "Medium",
    title: `${alert.name} alert`,
    type: scenario.scenario_name
  };
}

function toHeatmapSnapshotFrame(state: ArenaState): HeatmapSnapshotFrame {
  return {
    book: state.book,
    tick: state.tick
  };
}

function toTimelineFrame(state: ArenaState): MarketTimelineFrame {
  return {
    detectorScores: state.detectors,
    features: state.features ?? {},
    markers: getTimelineMarkers(state),
    mid: state.mid ?? 0,
    tick: state.tick
  };
}

function getTimelineMarkers(state: ArenaState): TimelineMarkerType[] {
  const markers: TimelineMarkerType[] = [];
  const attack = state.active_scenario;
  if (attack && attack.start_tick === state.tick) {
    markers.push("attack_started");
  }
  if (state.detectors.alerts.some((alert) => alert.confidence > 0.75)) {
    markers.push("detector_warning");
  }
  if (attack?.current_stage === "incident_confirmed" || attack?.status === "incident_confirmed") {
    markers.push("incident_confirmed");
  }
  return markers;
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  if (Math.abs(value) >= 1_000) {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return value.toFixed(2);
}
