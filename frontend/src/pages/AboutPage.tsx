const researchLinks = [
  {
    title: "ABIDES: Towards High-Fidelity Market Simulation for AI Research",
    source: "arXiv:1904.12066",
    url: "https://arxiv.org/abs/1904.12066"
  },
  {
    title: "Spoofing the Limit Order Book: An Agent-Based Model",
    source: "AAMAS 2017 / IFAAMAS",
    url: "https://www.ifaamas.org/Proceedings/aamas2017/pdfs/p651.pdf"
  },
  {
    title: "Get Real: Realism Metrics for Robust Limit Order Book Market Simulations",
    source: "arXiv:1912.04941",
    url: "https://arxiv.org/abs/1912.04941"
  },
  {
    title: "Learning to simulate realistic limit order book markets from data as a World Agent",
    source: "arXiv:2210.09897",
    url: "https://arxiv.org/abs/2210.09897"
  },
  {
    title: "TRADES: Generating Realistic Market Simulations with Diffusion Models",
    source: "arXiv:2502.07071",
    url: "https://arxiv.org/abs/2502.07071"
  },
  {
    title: "Simulating Financial Market via Large Language Model based Agents",
    source: "arXiv:2406.19966",
    url: "https://arxiv.org/abs/2406.19966"
  }
];

export function AboutPage() {
  return (
    <section className="about-page">
      <div className="panel about-hero-panel">
        <h2>Visual synthetic market arena for detection, explanation, and benchmarks</h2>
        <p>
          AI Market Abuse Detection Arena is a React visual cockpit plus FastAPI simulator that creates a synthetic
          limit-order-book market. Normal agents provide baseline activity, red-team scenarios inject bounded
          abuse-like patterns, deterministic detectors score the market state, and Nebius AI plus experiment jobs
          explain incidents or run offline experiments.
        </p>
      </div>

      <div className="about-grid">
        <section className="panel about-card">
          <h3>Educational Story: Why These Attacks Matter</h3>
          <p>
            The demo can be read as a training story for market participants, engineers, and reviewers. It shows
            what abuse-like pressure looks like in a limit order book, how detectors collect evidence, and why even
            short synthetic incidents can damage confidence in a market.
          </p>
          <ul>
            <li><strong>Spoofing-like pressure:</strong> fake visible liquidity can make other participants believe supply or demand is stronger than it is.</li>
            <li><strong>Layering-like pressure:</strong> repeated stacked orders can distort the apparent shape of the book across several price levels.</li>
            <li><strong>Quote stuffing-like bursts:</strong> rapid message flow can make the market harder to read and increase surveillance and infrastructure load.</li>
            <li><strong>Momentum ignition-like moves:</strong> a burst of activity can try to trigger follow-on orders, stops, or reactive algorithms.</li>
          </ul>
          <p>
            In the educational narrative, an attacker may seek illegal profit by inducing a price move, trading on the
            distorted price, and cancelling misleading orders before execution. The wider harm is larger than one
            trade: the exchange can look unreliable, liquidity providers may retreat, spreads can widen, and trust in
            the affected stock or crypto instrument can deteriorate.
          </p>
          <p>
            The purpose here is defensive literacy: recognize the pattern, preserve replay evidence, explain the
            detector decision, and compare surveillance quality under repeatable synthetic scenarios.
          </p>
        </section>

        <section className="panel about-card">
          <h3>What We Solve</h3>
          <p>
            The project makes order-book anomaly detection understandable without using real trading data. It lets a
            reviewer see the market move, launch synthetic patterns, inspect detector evidence, and compare detector
            quality through repeatable batch runs.
          </p>
          <ul>
            <li>Live visual order book and market microstructure cockpit.</li>
            <li>Synthetic spoofing-like, layering-like, quote-stuffing, and liquidity-shock scenarios.</li>
            <li>Deterministic detector scores and evidence extraction.</li>
            <li>AI Investigator explanations grounded in compact replay evidence.</li>
            <li>Experiment benchmark and dataset jobs for serious evaluation artifacts.</li>
          </ul>
        </section>

        <section className="panel about-card">
          <h3>ML-Friendly Mental Model</h3>
          <ul>
            <li><strong>Market state:</strong> the order book is the feature stream, similar to a time-series sensor feed.</li>
            <li><strong>Red-team scenario:</strong> a controlled synthetic perturbation with known labels and expected signals.</li>
            <li><strong>Detection logic:</strong> a scoring function over recent book windows, event rates, imbalance, cancels, and price impact.</li>
            <li><strong>Incident evidence:</strong> the replay window, detector scores, labels, and agent events used to justify an alert.</li>
            <li><strong>AI Investigator:</strong> narrative summarization of evidence; the deterministic detector remains the source of the decision.</li>
            <li><strong>Batch benchmark:</strong> repeated scenario runs used to compare precision, recall, F1, latency, and artifact quality.</li>
          </ul>
        </section>

        <section className="panel about-card">
          <h3>How Nebius Is Used</h3>
          <p>
            Nebius is split into Nebius AI inference and offline jobs. The browser never receives Nebius secrets; it
            calls the FastAPI backend, and the backend calls Nebius.
          </p>
          <ul>
            <li><strong>Nebius AI Serverless Endpoint:</strong> scores order-book windows and powers interactive AI calls.</li>
            <li><strong>Nebius AI Investigation Team:</strong> generates reports through the backend report adapter.</li>
            <li><strong>Nebius AI Scenario Generator:</strong> drafts bounded red-team scenarios through the backend adapter.</li>
            <li><strong>Nebius Serverless Jobs:</strong> run detector tournaments and generate labeled benchmark artifacts.</li>
          </ul>
        </section>

        <section className="panel about-card">
          <h3>Project Guardrails</h3>
          <ul>
            <li>Show the market first; explanations should be grounded in visible state.</li>
            <li>Keep red-team scenarios synthetic, bounded, and explicitly labeled.</li>
            <li>Separate live demo latency from batch benchmark workloads.</li>
            <li>Use deterministic detectors for evidence and AI Investigator only for explanation and narration.</li>
            <li>Preserve the disclaimer: no real manipulation detection, no trading signals, no compliance use.</li>
          </ul>
        </section>

        <section className="panel about-card">
          <h3>How To Run</h3>
          <ol>
            <li>Build and run the full local stack: <code>docker compose up --build</code>.</li>
            <li>Open the UI at <code>http://localhost:5173/arena</code>.</li>
            <li>Click <code>Start</code>, then launch a red-team scenario.</li>
            <li>When an incident appears, open Incident Details and run Nebius AI Investigation Team.</li>
            <li>Use Nebius AI Scenario Generator for concrete red-team plans that can be injected, expanded into grids, or submitted to Nebius batches.</li>
            <li>Use Detection for detector scores, suspicious agents, evidence, reports, replay windows, and Nebius AI Investigation Team review.</li>
            <li>Use Nebius AI for the full cloud workflow: scenario creation, Nebius Serverless Jobs, detector scoring, explanations, and artifact storage.</li>
          </ol>
          <p>
            In mock endpoint mode, Docker Compose runs the local serverless endpoint and the backend calls
            <code> http://endpoint:9000</code> inside the Docker network.
          </p>
        </section>
      </div>

      <section className="panel about-card architecture-card">
        <div className="section-heading-row">
          <h3>Architecture Diagram</h3>
        </div>
        <ArchitectureDiagram />
      </section>

      <div className="about-grid">
        <section className="panel about-card">
          <h3>Pipeline</h3>
          <ol>
            <li>Generate or select a bounded synthetic attack scenario.</li>
            <li>Run the market simulation and emit order-book events, trades, snapshots, labels, and detector outputs.</li>
            <li>Score alerts with deterministic detectors over recent book windows.</li>
            <li>Persist replay evidence and compact alert context.</li>
            <li>Use Nebius AI for AI Investigator reports and Nebius jobs for batch experiments.</li>
            <li>Aggregate precision, recall, F1, latency, artifacts, and benchmark report output.</li>
          </ol>
        </section>

        <section className="panel about-card benchmark-summary-card">
          <h3>Benchmark Summary</h3>
          <p>Benchmarks compare detector performance across labeled synthetic scenarios and repeatable replay windows.</p>
          <div className="benchmark-summary-grid">
            <article>
              <span>Detection quality</span>
              <strong>Precision, recall, F1</strong>
              <p>How reliably the detector separates suspicious market behavior from normal liquidity.</p>
            </article>
            <article>
              <span>Error profile</span>
              <strong>False positives / negatives</strong>
              <p>Where the detector over-alerts or misses labeled manipulation windows.</p>
            </article>
            <article>
              <span>Operational cost</span>
              <strong>Latency, artifacts, reports</strong>
              <p>How quickly a run produces evidence, replay data, and report-ready outputs.</p>
            </article>
          </div>
        </section>

        <section className="panel about-card research-panel">
          <h3>Research Papers</h3>
          <ul className="research-link-list">
          {researchLinks.map((item) => (
            <li key={item.title}>
              <a href={item.url} rel="noreferrer" target="_blank">
                <strong>{item.title}</strong>
                <span>{item.source}</span>
              </a>
            </li>
          ))}
          </ul>
        </section>
      </div>
    </section>
  );
}

function ArchitectureDiagram() {
  return (
    <svg
      aria-label="Architecture diagram showing Front, Back, Platform Identity, Agent Runners Workspace, Nebius Serverless Cloud, and Artifacts"
      className="architecture-flow-diagram"
      role="img"
      viewBox="0 0 1100 540"
    >
      <defs>
        <marker id="architecture-arrow" markerHeight="8" markerWidth="8" orient="auto" refX="7" refY="4">
          <path d="M0,0 L8,4 L0,8 Z" />
        </marker>
      </defs>

      <g className="architecture-node architecture-front">
        <rect height="132" width="270" x="415" y="24" />
        <text x="550" y="58">
          <tspan x="550">Front - React / Vite UI -</tspan>
          <tspan x="550" dy="25">Arena, Demo, Scenario</tspan>
          <tspan x="550" dy="25">Generator, Detection,</tspan>
          <tspan x="550" dy="25">Experiments, Nebius AI,</tspan>
          <tspan x="550" dy="25">About</tspan>
        </text>
      </g>

      <g className="architecture-node architecture-back">
        <rect height="96" width="270" x="415" y="224" />
        <text x="550" y="260">
          <tspan x="550">Back - FastAPI backend -</tspan>
          <tspan x="550" dy="25">REST, WebSocket,</tspan>
          <tspan x="550" dy="25">orchestration, persistence</tspan>
        </text>
      </g>

      <g className="architecture-node architecture-identity">
        <rect height="94" width="250" x="760" y="214" />
        <text x="885" y="246">
          <tspan x="885">Platform Identity -</tspan>
          <tspan x="885" dy="25">users, workspace, roles,</tspan>
          <tspan x="885" dy="25">cases, audit trail</tspan>
        </text>
      </g>

      <g className="architecture-node architecture-runners">
        <rect height="92" width="275" x="75" y="410" />
        <text x="212" y="446">
          <tspan x="212">Agent Runners Workspace -</tspan>
          <tspan x="212" dy="25">local Docker and remote</tspan>
          <tspan x="212" dy="25">workers</tspan>
        </text>
      </g>

      <g className="architecture-node architecture-nebius">
        <rect height="112" width="285" x="430" y="400" />
        <text x="572" y="432">
          <tspan x="572">Nebius Serverless Cloud -</tspan>
          <tspan x="572" dy="25">model selection,</tspan>
          <tspan x="572" dy="25">inference, batch jobs, GPU</tspan>
          <tspan x="572" dy="25">runtime, datasets, artifacts</tspan>
        </text>
      </g>

      <g className="architecture-node architecture-artifacts">
        <rect height="112" width="245" x="805" y="400" />
        <text x="928" y="432">
          <tspan x="928">Artifacts - events,</tspan>
          <tspan x="928" dy="25">snapshots, incidents,</tspan>
          <tspan x="928" dy="25">reports, benchmark</tspan>
          <tspan x="928" dy="25">outputs</tspan>
        </text>
      </g>

      <path className="architecture-edge" d="M550 156 L550 224" />
      <text className="architecture-edge-label" x="550" y="194">REST and WebSocket</text>

      <path className="architecture-edge architecture-edge-curved" d="M685 94 C780 118 830 160 860 214" />
      <text className="architecture-edge-label" x="820" y="142">Google or demo identity</text>

      <path className="architecture-edge architecture-edge-curved" d="M760 272 C725 280 710 285 685 286" />
      <text className="architecture-edge-label" x="750" y="310">case metadata and audit</text>

      <path className="architecture-edge architecture-edge-curved" d="M415 282 C290 300 80 325 160 410" />
      <text className="architecture-edge-label" x="200" y="334">snapshot and run config</text>

      <path className="architecture-edge architecture-edge-curved" d="M275 410 C330 360 360 326 415 318" />
      <text className="architecture-edge-label" x="355" y="365">agent intents and detector outputs</text>

      <path className="architecture-edge" d="M550 320 L550 400" />
      <text className="architecture-edge-label" x="550" y="365">LLM calls and managed jobs</text>

      <path className="architecture-edge architecture-edge-curved" d="M650 400 C710 355 710 330 685 306" />
      <text className="architecture-edge-label" x="716" y="348">explanations, metrics, artifacts</text>

      <path className="architecture-edge architecture-edge-curved" d="M685 280 C875 318 980 332 928 400" />
    </svg>
  );
}
