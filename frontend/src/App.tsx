import { useEffect, useMemo, useState } from "react";
import "./App.css";

type Screen = "arena" | "benchmark" | "about";
type Regime = "Calm" | "Volatile" | "Thin";
type ConnectionStatus = "connecting" | "connected" | "disconnected";

type BookLevel = {
  price: number;
  quantity: number;
};

type ArenaState = {
  tick: number;
  running: boolean;
  events: Array<Record<string, unknown>>;
  book: {
    bids: BookLevel[];
    asks: BookLevel[];
  };
  best_bid: number | null;
  best_ask: number | null;
  mid: number | null;
  spread: number | null;
  active_agents: string[];
};

type Incident = {
  type: string;
  agent: string;
  confidence: number;
  severity: "Medium" | "High" | "Critical";
  evidence: string[];
  explanation: string;
};

const disclaimer =
  "This project is an educational simulation. It does not detect real market manipulation, does not provide trading signals, and should not be used for compliance decisions. The scenarios are synthetic “abuse-like” patterns designed to demonstrate order-book anomaly detection and AI-generated explanations.";

const scenarioIncidents: Record<string, Incident> = {
  "Spoofing-like Wall": {
    type: "Spoofing-like liquidity wall",
    agent: "ABUSER_01",
    confidence: 0.91,
    severity: "High",
    evidence: [
      "ask depth increased 480%",
      "order lifetime 1.8 sec",
      "cancellation before execution",
      "imbalance shifted from +0.08 to -0.74"
    ],
    explanation:
      "A large visible wall appeared away from the touch and disappeared before execution. In this simulation, that pattern is treated as spoofing-like pressure and flagged for manual review."
  },
  "Layering-like Pattern": {
    type: "Layering-like multi-level pressure",
    agent: "ABUSER_02",
    confidence: 0.84,
    severity: "High",
    evidence: ["five same-side levels added", "depth concentrated above best ask", "group cancellation after price move"],
    explanation:
      "Multiple same-side levels created coordinated visible pressure and were later removed together. The detector treats this as a layering-like synthetic pattern."
  },
  "Quote Stuffing Burst": {
    type: "Quote-stuffing-like message burst",
    agent: "ABUSER_03",
    confidence: 0.96,
    severity: "Critical",
    evidence: ["message rate exceeded 220 updates/sec", "cancel-to-trade ratio above 35:1", "low execution ratio"],
    explanation:
      "The event stream shows a high-rate burst of place and cancel updates with little execution. The synthetic detector flags this as quote-stuffing-like activity."
  },
  "Liquidity Evaporation": {
    type: "Liquidity shock",
    agent: "SCENARIO_LIQUIDITY",
    confidence: 0.89,
    severity: "High",
    evidence: ["top-of-book depth collapsed 72%", "spread widened 41 bps", "market orders consumed visible liquidity"],
    explanation:
      "Displayed depth collapsed while spread widened. This is treated as a synthetic liquidity-shock interval for detector demonstration."
  },
  "Panic Selloff": {
    type: "Panic selloff scenario",
    agent: "SCENARIO_PANIC",
    confidence: 0.87,
    severity: "Medium",
    evidence: ["aggressive sell flow clustered", "mid price dropped 1.7%", "bid depth thinned quickly"],
    explanation:
      "Aggressive sell pressure moved through visible bid liquidity. The scenario demonstrates how stress conditions appear in the arena UI."
  }
};

const benchmarkRows = [
  ["Spoofing-like wall", "0.91", "0.86", "0.88"],
  ["Layering-like", "0.84", "0.79", "0.81"],
  ["Quote stuffing", "0.96", "0.92", "0.94"],
  ["Liquidity shock", "0.89", "0.83", "0.86"]
];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws/arena";

export function App() {
  const [screen, setScreen] = useState<Screen>("arena");
  const [running, setRunning] = useState(false);
  const [autoArena, setAutoArena] = useState(true);
  const [regime, setRegime] = useState<Regime>("Calm");
  const [tick, setTick] = useState(0);
  const [activeScenario, setActiveScenario] = useState("None");
  const [incident, setIncident] = useState<Incident | null>(null);
  const [arenaState, setArenaState] = useState<ArenaState | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connecting");
  const [feed, setFeed] = useState<string[]>([
    "MarketMakerAgent posted bid/ask liquidity around mid",
    "NoiseTraderAgent submitted small limit buy",
    "LiquidityTakerAgent consumed 12 lots at best ask"
  ]);

  useEffect(() => {
    let closedByEffect = false;
    const socket = new WebSocket(WS_URL);
    setConnectionStatus("connecting");

    socket.onopen = () => setConnectionStatus("connected");
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as { type: string; payload: ArenaState };
      if (message.type !== "arena_state") {
        return;
      }
      setArenaState(message.payload);
      setRunning(message.payload.running);
      if (message.payload.events.length) {
        setFeed((items) => [
          ...message.payload.events.map(formatEvent).reverse(),
          ...items
        ].slice(0, 8));
      }
    };
    socket.onclose = () => {
      if (!closedByEffect) {
        setConnectionStatus("disconnected");
      }
    };
    socket.onerror = () => setConnectionStatus("disconnected");

    return () => {
      closedByEffect = true;
      socket.close();
    };
  }, []);

  useEffect(() => {
    if (!running || arenaState) {
      return;
    }
    const handle = window.setInterval(() => {
      setTick((value) => value + 1);
      setFeed((items) => [
        eventForTick(tick + 1, regime, activeScenario),
        ...items
      ].slice(0, 8));
    }, regime === "Volatile" ? 250 : 500);
    return () => window.clearInterval(handle);
  }, [activeScenario, regime, running, tick]);

  const effectiveTick = arenaState?.tick ?? tick;
  const book = useMemo(
    () => arenaState?.book ?? buildBook(tick, regime, activeScenario),
    [activeScenario, arenaState, regime, tick]
  );
  const detectorScores = useMemo(() => buildDetectorScores(tick, activeScenario), [activeScenario, tick]);
  const mid = arenaState?.mid ?? 100 + Math.sin(tick / 3) * (regime === "Volatile" ? 1.2 : 0.35);
  const spread = arenaState?.spread ?? (regime === "Thin" ? 0.28 : regime === "Volatile" ? 0.18 : 0.08);
  const imbalance = activeScenario === "Spoofing-like Wall" ? -0.74 : Math.sin(tick / 4) * 0.42;
  const activeAgents = arenaState?.active_agents ?? ["MarketMakerAgent", "NoiseTraderAgent", "LiquidityTakerAgent"];

  async function controlSimulation(action: "start" | "pause" | "reset") {
    try {
      const response = await fetch(`${API_BASE_URL}/simulation/${action}`, { method: "POST" });
      const payload = await response.json();
      if (payload.state) {
        setArenaState(payload.state);
        setRunning(payload.state.running);
      }
    } catch {
      setConnectionStatus("disconnected");
      if (action === "start") {
        setRunning(true);
      }
      if (action === "pause" || action === "reset") {
        setRunning(false);
      }
      if (action === "reset") {
        reset();
      }
    }
  }

  function launchScenario(name: string) {
    setActiveScenario(name);
    setIncident(scenarioIncidents[name]);
    setRunning(true);
    setFeed((items) => [`${name} launched from UI`, ...items].slice(0, 8));
  }

  function reset() {
    setRunning(false);
    setTick(0);
    setActiveScenario("None");
    setIncident(null);
    setFeed(["Arena reset", "Always-on agents ready"]);
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Synthetic order-book anomaly arena</p>
          <h1>Nebius Market Abuse Arena</h1>
        </div>
        <nav className="screen-tabs" aria-label="Main screens">
          {(["arena", "benchmark", "about"] as Screen[]).map((item) => (
            <button
              className={screen === item ? "active" : ""}
              key={item}
              type="button"
              onClick={() => setScreen(item)}
            >
              {item}
            </button>
          ))}
        </nav>
      </header>

      <section className="disclaimer" aria-label="Project disclaimer">
        <strong>Disclaimer: </strong>
        {disclaimer}
      </section>

      {screen === "arena" && (
        <ArenaScreen
          activeScenario={activeScenario}
          activeAgents={activeAgents}
          autoArena={autoArena}
          book={book}
          connectionStatus={connectionStatus}
          detectorScores={detectorScores}
          feed={feed}
          imbalance={imbalance}
          incident={incident}
          launchScenario={launchScenario}
          mid={mid}
          onPause={() => void controlSimulation("pause")}
          onReset={() => void controlSimulation("reset")}
          onStart={() => void controlSimulation("start")}
          regime={regime}
          running={running}
          setAutoArena={setAutoArena}
          setRegime={setRegime}
          spread={spread}
          tick={effectiveTick}
        />
      )}
      {screen === "benchmark" && <BenchmarkScreen />}
      {screen === "about" && <AboutScreen />}
    </main>
  );
}

function ArenaScreen(props: {
  activeScenario: string;
  activeAgents: string[];
  autoArena: boolean;
  book: ReturnType<typeof buildBook>;
  connectionStatus: ConnectionStatus;
  detectorScores: ReturnType<typeof buildDetectorScores>;
  feed: string[];
  imbalance: number;
  incident: Incident | null;
  launchScenario: (name: string) => void;
  mid: number;
  onPause: () => void;
  onReset: () => void;
  onStart: () => void;
  regime: Regime;
  running: boolean;
  setAutoArena: (value: boolean) => void;
  setRegime: (value: Regime) => void;
  spread: number;
  tick: number;
}) {
  return (
    <section className="arena-screen">
      <div className="toolbar">
        <button type="button" onClick={props.onStart}>Start</button>
        <button type="button" onClick={props.onPause}>Pause</button>
        <button type="button" onClick={props.onReset}>Reset</button>
        <button type="button" onClick={() => props.setAutoArena(!props.autoArena)}>
          Auto Arena: {props.autoArena ? "ON" : "OFF"}
        </button>
        <label>
          Market Regime:
          <select value={props.regime} onChange={(event) => props.setRegime(event.target.value as Regime)}>
            <option>Calm</option>
            <option>Volatile</option>
            <option>Thin</option>
          </select>
        </label>
        <span className="status-pill">{props.running ? "Running" : "Paused"} | tick {props.tick}</span>
        <span className={`status-pill connection ${props.connectionStatus}`}>Backend: {props.connectionStatus}</span>
      </div>

      <div className="arena-grid">
        <section className="panel order-book">
          <h2>Live Order Book</h2>
          <div className="ladder">
            <BookSide title="Asks" levels={props.book.asks} side="ask" />
            <div className="midline">Mid {props.mid.toFixed(2)}</div>
            <BookSide title="Bids" levels={props.book.bids} side="bid" />
          </div>
        </section>

        <section className="panel center-stage">
          <div className="metric-row">
            <Metric label="Mid Price" value={props.mid.toFixed(2)} />
            <Metric label="Spread" value={props.spread.toFixed(2)} />
            <Metric label="Scenario" value={props.activeScenario} />
          </div>
          <Chart title="Mid-price chart" tick={props.tick} amplitude={props.regime === "Volatile" ? 18 : 7} />
          <Chart title="Spread chart" tick={props.tick + 3} amplitude={props.regime === "Thin" ? 16 : 8} />
          <section>
            <h2>Order-book Imbalance</h2>
            <div className="gauge">
              <div className="gauge-fill" style={{ width: `${Math.min(Math.abs(props.imbalance) * 100, 100)}%` }} />
            </div>
            <p className="mono">{props.imbalance.toFixed(2)}</p>
          </section>
          <section>
            <h2>Detector Confidence Timeline</h2>
            <div className="confidence-grid">
              {props.detectorScores.map((score) => (
                <div key={score.name}>
                  <span>{score.name}</span>
                  <div className="confidence-bar">
                    <div style={{ width: `${score.value * 100}%` }} />
                  </div>
                  <strong>{score.value.toFixed(2)}</strong>
                </div>
              ))}
            </div>
          </section>
        </section>

        <section className="panel right-rail">
          <h2>Agent Activity Feed</h2>
          <ul className="feed-list">
            {props.feed.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
          </ul>
          <h2>Active Agents</h2>
          <div className="agent-list">
            {props.activeAgents.map((agent) => <span key={agent}>{agent}</span>)}
            {props.activeScenario !== "None" && <span>{props.activeScenario}</span>}
          </div>
          <IncidentDrawer incident={props.incident} />
        </section>
      </div>

      <section className="scenario-launcher">
        <h2>Scenario Launcher</h2>
        {Object.keys(scenarioIncidents).map((name) => (
          <button key={name} type="button" onClick={() => props.launchScenario(name)}>
            {name}
          </button>
        ))}
      </section>
    </section>
  );
}

function BookSide({ levels, side, title }: { levels: Array<{ price: number; quantity: number }>; side: "ask" | "bid"; title: string }) {
  return (
    <div>
      <h3>{title}</h3>
      {levels.map((level) => (
        <div className={`book-level ${side}`} key={`${side}-${level.price}`}>
          <span>{level.price.toFixed(2)}</span>
          <strong>{level.quantity}</strong>
        </div>
      ))}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Chart({ amplitude, tick, title }: { amplitude: number; tick: number; title: string }) {
  const points = Array.from({ length: 32 }, (_, index) => {
    const x = index * 12;
    const y = 42 + Math.sin((index + tick) / 3) * amplitude + Math.cos((index + tick) / 5) * 5;
    return `${x},${y}`;
  }).join(" ");

  return (
    <section>
      <h2>{title}</h2>
      <svg className="chart" viewBox="0 0 372 90" role="img" aria-label={title}>
        <polyline points={points} fill="none" stroke="currentColor" strokeWidth="3" />
      </svg>
    </section>
  );
}

function IncidentDrawer({ incident }: { incident: Incident | null }) {
  if (!incident) {
    return (
      <section className="incident-drawer empty">
        <h2>Incident Cards</h2>
        <p>No active incident. Launch a scenario to generate a synthetic alert.</p>
      </section>
    );
  }

  return (
    <section className="incident-drawer">
      <h2>Suspicious Event Detected</h2>
      <dl>
        <div><dt>Type</dt><dd>{incident.type}</dd></div>
        <div><dt>Agent</dt><dd>{incident.agent}</dd></div>
        <div><dt>Confidence</dt><dd>{incident.confidence.toFixed(2)}</dd></div>
        <div><dt>Severity</dt><dd>{incident.severity}</dd></div>
      </dl>
      <h3>Evidence</h3>
      <ul>
        {incident.evidence.map((item) => <li key={item}>{item}</li>)}
      </ul>
      <h3>AI explanation</h3>
      <p>{incident.explanation}</p>
    </section>
  );
}

function BenchmarkScreen() {
  return (
    <section className="panel benchmark-screen">
      <h2>Benchmark Screen</h2>
      <p>Offline synthetic benchmark results by scenario family.</p>
      <table>
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Precision</th>
            <th>Recall</th>
            <th>F1</th>
          </tr>
        </thead>
        <tbody>
          {benchmarkRows.map(([scenario, precision, recall, f1]) => (
            <tr key={scenario}>
              <td>{scenario}</td>
              <td>{precision}</td>
              <td>{recall}</td>
              <td>{f1}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function AboutScreen() {
  return (
    <section className="panel about-screen">
      <h2>About</h2>
      <p>
        Nebius Market Abuse Arena is a synthetic order-book simulator for demonstrating anomaly detection, scenario
        launch workflows, and AI-generated explanations.
      </p>
      <p>{disclaimer}</p>
    </section>
  );
}

function buildBook(tick: number, regime: Regime, scenario: string) {
  const base = 100 + Math.sin(tick / 3) * 0.3;
  const thinMultiplier = regime === "Thin" ? 0.48 : 1;
  const wall = scenario === "Spoofing-like Wall" ? 420 : 0;
  return {
    asks: Array.from({ length: 6 }, (_, index) => ({
      price: base + 0.05 * (index + 1),
      quantity: Math.round((58 - index * 6) * thinMultiplier + (index === 3 ? wall : 0))
    })).reverse(),
    bids: Array.from({ length: 6 }, (_, index) => ({
      price: base - 0.05 * (index + 1),
      quantity: Math.round((62 - index * 7) * thinMultiplier)
    }))
  };
}

function buildDetectorScores(tick: number, scenario: string) {
  const active = scenario !== "None";
  return [
    { name: "Spoofing", value: scenario === "Spoofing-like Wall" ? 0.91 : pulse(tick, 0.22) },
    { name: "Layering", value: scenario === "Layering-like Pattern" ? 0.84 : pulse(tick + 2, 0.18) },
    { name: "Quote Stuffing", value: scenario === "Quote Stuffing Burst" ? 0.96 : pulse(tick + 4, 0.2) },
    { name: "Liquidity Shock", value: active && scenario !== "Spoofing-like Wall" ? 0.72 : pulse(tick + 6, 0.16) }
  ];
}

function pulse(tick: number, scale: number) {
  return Math.max(0.05, Math.min(0.45, 0.18 + Math.sin(tick / 5) * scale));
}

function eventForTick(tick: number, regime: Regime, scenario: string) {
  const baseline = [
    "MarketMakerAgent refreshed two-sided quotes",
    "NoiseTraderAgent submitted small market order",
    "LiquidityTakerAgent crossed the spread",
    `Detector scores recalculated for ${regime.toLowerCase()} market regime`
  ];
  if (scenario !== "None" && tick % 3 === 0) {
    return `${scenario} emitted synthetic order-book pressure`;
  }
  return baseline[tick % baseline.length];
}

function formatEvent(event: Record<string, unknown>) {
  const type = String(event.type ?? "event");
  const agent = String(event.agent_id ?? event.aggressor_agent_id ?? "exchange");
  if (type === "trade") {
    return `${agent} traded ${event.quantity} @ ${event.price}`;
  }
  if (type === "limit_order") {
    return `${agent} placed ${event.side} limit ${event.quantity} @ ${event.price}`;
  }
  if (type === "market_order_unfilled") {
    return `${agent} sent unfilled ${event.side} market order`;
  }
  return `${agent} emitted ${type}`;
}
