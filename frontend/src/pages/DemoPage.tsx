import { Link, useNavigate } from "react-router-dom";
import { productDemoConfigs, type ProductDemoMode } from "@/demoModes";

const demoCards: Record<ProductDemoMode, {
  cta: string;
  description: string;
  shows: string[];
}> = {
  real: {
    cta: "Start Real Run",
    description: "Runs a market abuse scenario and calls Nebius AI for structured incident explanation.",
    shows: ["Detector alert", "Evidence", "AI explanation", "Cost/latency metrics"]
  },
  "two-model": {
    cta: "Start Two-Model Demo",
    description: "Shows fast classification followed by reasoning-model investigation.",
    shows: ["Classifier model", "Reasoning model", "Confidence", "Recommendation"]
  },
  streaming: {
    cta: "Start Streaming Demo",
    description: "Streams an AI investigation response step by step.",
    shows: ["Connecting", "Retrieving context", "Reasoning", "Streamed explanation", "Metrics"]
  },
  "batch-job": {
    cta: "Start Batch Job Demo",
    description: "Runs a post-event Nebius job over replay, evidence, detector logs, and market snapshots.",
    shows: ["Job status", "Job id", "Runtime", "Output artifact", "Report summary"]
  }
};

export function DemoPage() {
  const navigate = useNavigate();

  function startDemo(mode: ProductDemoMode) {
    if (mode === "batch-job") {
      navigate("/detection?demo=batch-job");
      return;
    }
    navigate(`/arena?demo=${mode}`);
  }

  return (
    <section className="demo-page">
      <div className="panel demo-hero-panel">
        <h2>3-Minute Product Demo</h2>
        <p>Choose a deterministic demo path, then run it in Arena.</p>
      </div>

      <div className="demo-card-grid">
        {productDemoConfigs.map((config) => {
          const card = demoCards[config.id];
          return (
            <article className="panel demo-scenario-card" key={config.id}>
              <div className="demo-card-heading">
                <div>
                  <span>{config.label}</span>
                  <h3>{config.title}</h3>
                </div>
              </div>
              <p>{card.description}</p>
              <dl className="demo-card-meta">
                <div><dt>Symbol</dt><dd>{config.marketSymbol}</dd></div>
                <div><dt>Attack</dt><dd>{config.attackPattern}</dd></div>
                <div><dt>Detector</dt><dd>{config.detectorProfile}</dd></div>
                <div><dt>AI mode</dt><dd>{config.aiInvestigationMode}</dd></div>
              </dl>
              <div className="demo-shows-list">
                {card.shows.map((item) => <span key={item}>{item}</span>)}
              </div>
              <div className="demo-card-actions">
                <button className="primary-button" onClick={() => startDemo(config.id)} type="button">{card.cta}</button>
                {config.id === "real" ? <Link to="/arena?demo=real">Open in Arena</Link> : null}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
