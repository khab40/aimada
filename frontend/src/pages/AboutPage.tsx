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
        <p className="eyebrow">What this project does</p>
        <h2>Visual synthetic market arena for detection, explanation, and benchmarks</h2>
        <p>
          Nebius Market Abuse Arena is a React visual cockpit plus FastAPI simulator that creates a synthetic
          limit-order-book market. Normal agents provide baseline activity, red-team scenarios inject bounded
          abuse-like patterns, deterministic detectors score the market state, and Nebius Serverless components
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
            <li>AI-generated explanations grounded in compact replay evidence.</li>
            <li>Serverless benchmark and dataset jobs for serious evaluation artifacts.</li>
          </ul>
        </section>

        <section className="panel about-card">
          <h3>ML-Friendly Mental Model</h3>
          <ul>
            <li><strong>Market state:</strong> the order book is the feature stream, similar to a time-series sensor feed.</li>
            <li><strong>Red-team scenario:</strong> a controlled synthetic perturbation with known labels and expected signals.</li>
            <li><strong>Blue-team detector:</strong> a scoring function over recent book windows, event rates, imbalance, cancels, and price impact.</li>
            <li><strong>Incident evidence:</strong> the replay window, detector scores, labels, and agent events used to justify an alert.</li>
            <li><strong>AI explanation:</strong> narrative summarization of evidence; the deterministic detector remains the source of the decision.</li>
            <li><strong>Batch benchmark:</strong> repeated scenario runs used to compare precision, recall, F1, latency, and artifact quality.</li>
          </ul>
        </section>

        <section className="panel about-card">
          <h3>How Nebius Is Used</h3>
          <p>
            Nebius is split into online AI endpoints and offline jobs. The browser never receives Nebius secrets; it
            calls the FastAPI backend, and the backend calls Nebius.
          </p>
          <ul>
            <li><strong>Serverless AI Endpoint:</strong> scores order-book windows at <code>/orderbook-alert</code>.</li>
            <li><strong>Serverless AI Endpoint:</strong> generates investigation reports at <code>/investigation-report</code>.</li>
            <li><strong>Serverless AI Endpoint:</strong> drafts bounded red-team scenarios through the backend adapter.</li>
            <li><strong>Serverless AI Jobs:</strong> run smart attack/detect batches and detector tournaments.</li>
            <li><strong>Serverless AI Jobs:</strong> generate labeled synthetic event and snapshot datasets.</li>
          </ul>
        </section>

        <section className="panel about-card">
          <h3>Project Guardrails</h3>
          <ul>
            <li>Show the market first; explanations should be grounded in visible state.</li>
            <li>Keep red-team scenarios synthetic, bounded, and explicitly labeled.</li>
            <li>Separate live demo latency from batch benchmark workloads.</li>
            <li>Use deterministic detectors for evidence and AI only for explanation and narration.</li>
            <li>Preserve the disclaimer: no real manipulation detection, no trading signals, no compliance use.</li>
          </ul>
        </section>

        <section className="panel about-card">
          <h3>How To Run</h3>
          <ol>
            <li>Build and run the full local stack: <code>docker compose up --build</code>.</li>
            <li>Open the UI at <code>http://localhost:5173/arena</code>.</li>
            <li>Click <code>Start</code>, then launch a red-team scenario.</li>
            <li>When an incident appears, open the replay drawer and run Nebius AI Investigator.</li>
            <li>Use Attack Scenario Generator for concrete red-team plans that can be injected, expanded into grids, or submitted to Nebius batches.</li>
            <li>Use Blue Team Surveillance for detector scores, suspicious agents, evidence, and AI-assisted investigation.</li>
            <li>Use Nebius Control Panel for the full cloud workflow: scenario creation, cloud batch runs, detector scoring, explanations, and artifact storage.</li>
            <li>Use Replay & Reports to reload persisted jobs, explanations, artifacts, exports, replay windows, and promoted evidence.</li>
          </ol>
          <p>
            In mock endpoint mode, Docker Compose runs the local serverless endpoint and the backend calls
            <code> http://endpoint:9000</code> inside the Docker network.
          </p>
        </section>
      </div>

      <section className="panel research-panel">
        <div className="section-heading-row">
          <h3>Research Inspiration</h3>
          <span className="endpoint-badge">articles used for project direction</span>
        </div>
        <div className="research-link-grid">
          {researchLinks.map((item) => (
            <a href={item.url} key={item.title} rel="noreferrer" target="_blank">
              <strong>{item.title}</strong>
              <span>{item.source}</span>
            </a>
          ))}
        </div>
      </section>
    </section>
  );
}
