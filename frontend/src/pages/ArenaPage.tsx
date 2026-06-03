import { useEffect, useMemo, useState } from "react";
import { AttackTracker } from "@/components/AttackTracker";
import { AgentEventTape } from "@/components/AgentEventTape";
import { DetectorConfidencePanel } from "@/components/DetectorConfidencePanel";
import { EvidencePanel } from "@/components/EvidencePanel";
import { IncidentReplayDrawer } from "@/components/IncidentReplayDrawer";
import { LiquidityHeatmap } from "@/components/LiquidityHeatmap";
import { MarketTimeline, type MarketTimelineFrame, type TimelineMarkerType } from "@/components/MarketTimeline";
import { OrderBookLadder } from "@/components/OrderBookLadder";
import { ScenarioLauncher } from "@/components/ScenarioLauncher";
import { useArenaSource } from "@/hooks/useArenaSource";
import type { ArenaState, Incident } from "@/types/arena";

const scenarioLabels: Record<string, string> = Object.fromEntries(
  [
    ["spoofing_like_wall", "Spoofing-like Wall"],
    ["layering_like", "Layering-like Pattern"],
    ["quote_stuffing", "Quote Stuffing Burst"],
    ["liquidity_evaporation", "Liquidity Evaporation"]
  ]
);

export function ArenaPage() {
  const { launchScenario, mode, pause, reset, running, sourceStatus, start, state, symbol, tick } = useArenaSource();
  const [heatmapSnapshots, setHeatmapSnapshots] = useState(() => [state.book]);
  const [timeline, setTimeline] = useState<MarketTimelineFrame[]>(() => [toTimelineFrame(state)]);
  const incident = useMemo(() => createIncident(state), [state]);
  const loading = mode === "websocket" && sourceStatus === "connecting";

  useEffect(() => {
    setHeatmapSnapshots((snapshots) => [...snapshots, state.book].slice(-120));
    setTimeline((points) => [...points, toTimelineFrame(state)].slice(-48));
  }, [state]);

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
          pause();
        } else {
          start();
        }
      }
      if (key === "s") {
        launchScenario("spoofing_like_wall");
      }
      if (key === "l") {
        launchScenario("layering_like");
      }
      if (key === "q") {
        launchScenario("quote_stuffing");
      }
      if (key === "r") {
        reset();
        setHeatmapSnapshots([]);
        setTimeline([]);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [launchScenario, pause, reset, running, start]);

  return (
    <section className={`cockpit-page ${incident ? "incident-active" : ""}`} aria-label="Market microstructure cockpit">
      <TopStatusBar
        mid={state.mid}
        onPause={pause}
        onReset={() => {
          reset();
          setHeatmapSnapshots([]);
          setTimeline([]);
        }}
        onStart={start}
        running={running}
        spread={state.spread}
        symbol={symbol}
        tick={tick}
        source={`${mode}:${sourceStatus}`}
      />

      <div className="shortcut-strip" aria-label="Keyboard shortcuts">
        <span><kbd>Space</kbd> pause/resume</span>
        <span><kbd>S</kbd> spoofing-like</span>
        <span><kbd>L</kbd> layering-like</span>
        <span><kbd>Q</kbd> quote stuffing</span>
        <span><kbd>R</kbd> reset</span>
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

      <div className="cockpit-grid">
        <section className="panel cockpit-left">
          <OrderBookLadder snapshot={state.book} />
        </section>

        <section className="panel cockpit-center">
          <LiquidityHeatmap snapshots={heatmapSnapshots} />
          <MarketTimeline frames={timeline} />
        </section>

        <section className="panel cockpit-right">
          <AttackTracker attack={state.active_scenario} />
          <ScenarioLauncher activeScenario={state.active_scenario?.scenario_name} onLaunch={launchScenario} />
          <DetectorConfidencePanel detectors={state.detectors} />
        </section>

        <section className="panel cockpit-bottom-left">
          <AgentEventTape events={state.events} />
        </section>

        <section className="panel cockpit-bottom-right">
          <EvidencePanel state={state} />
          <IncidentReplayDrawer activeIncident={incident} />
        </section>
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
  mid,
  onPause,
  onReset,
  onStart,
  running,
  spread,
  symbol,
  tick,
  source
}: {
  mid: number | null;
  onPause: () => void;
  onReset: () => void;
  onStart: () => void;
  running: boolean;
  spread: number | null;
  source: string;
  symbol: string;
  tick: number;
}) {
  return (
    <header className="cockpit-status-bar">
      <div>
        <span className="eyebrow">Live mock arena</span>
        <strong>{symbol}</strong>
      </div>
      <MetricPill label="Tick" value={String(tick)} />
      <MetricPill label="Mid" value={formatNumber(mid)} />
      <MetricPill label="Spread" value={formatNumber(spread)} />
      <MetricPill label="State" value={running ? "Running" : "Paused"} tone={running ? "good" : "warn"} />
      <MetricPill label="Source" value={source} />
      <div className="cockpit-controls">
        <button type="button" onClick={onStart}>Start</button>
        <button type="button" onClick={onPause}>Pause</button>
        <button type="button" onClick={onReset}>Reset</button>
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
    id: `MOCK-${state.tick}`,
    scenario_family: scenario.scenario_family,
    scenario_id: scenario.scenario_id,
    severity: alert.severity === "critical" ? "Critical" : alert.severity === "high" ? "High" : "Medium",
    title: `${alert.name} alert`,
    type: scenario.scenario_name
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
