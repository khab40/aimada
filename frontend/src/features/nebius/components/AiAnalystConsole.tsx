import type { AiExplanation, IncidentReport, MarketSummary, StrategySuggestion } from "@/features/nebius/types";

type AiAnalystConsoleProps = {
  modelName: string;
  endpointStatus: "Ready" | "Busy" | "Offline";
  lastCallLatencySec: number;
  tokensUsed: number;
  busyAction: string | null;
  explanation: AiExplanation | IncidentReport | StrategySuggestion | MarketSummary | null;
  onExplain: () => void;
  onReport: () => void;
  onStrategy: () => void;
  onSummary: () => void;
};

export function AiAnalystConsole({
  busyAction,
  endpointStatus,
  explanation,
  lastCallLatencySec,
  modelName,
  onExplain,
  onReport,
  onStrategy,
  onSummary,
  tokensUsed
}: AiAnalystConsoleProps) {
  return (
    <section className="panel ai-analyst-console">
      <div className="nebius-card-heading">
        <div>
          <h2>AI Investigator Console</h2>
        </div>
        <span className={`runtime-top-badge ${endpointStatus.toLowerCase()}`}>Endpoint: {endpointStatus}</span>
      </div>
      <div className="ai-console-meta">
        <Meta label="Model" value={modelName} />
        <Meta label="Last latency" value={`${lastCallLatencySec.toFixed(1)}s`} />
        <Meta label="Tokens used" value={tokensUsed.toLocaleString()} />
      </div>
      <div className="nebius-button-row">
        <button disabled={busyAction !== null} onClick={onExplain} type="button">Explain Current Alert</button>
        <button disabled={busyAction !== null} onClick={onReport} type="button">Generate AI Investigator Report</button>
        <button disabled={busyAction !== null} onClick={onStrategy} type="button">Suggest Red-Team Strategy</button>
        <button disabled={busyAction !== null} onClick={onSummary} type="button">Summarize Market Regime</button>
      </div>
      <div className="ai-response-panel">
        {explanation ? <AiOutput value={explanation} /> : (
          <p className="empty-state">No analyst response yet. Explain the current spoofing alert to start the demo flow.</p>
        )}
      </div>
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return <span><strong>{label}</strong>{value}</span>;
}

function AiOutput({ value }: { value: AiExplanation | IncidentReport | StrategySuggestion | MarketSummary }) {
  const analysis = toAnalystWorkflow(value);

  return (
    <article className="ai-analyst-workflow">
      <div className="artifact-preview-title">
        <strong>{analysis.title}</strong>
        <span>{analysis.latencySec.toFixed(1)}s / {analysis.tokensUsed.toLocaleString()} tokens</span>
      </div>
      <AnalystStep title="Evidence" items={analysis.evidence} />
      <AnalystStep title="LLM reasoning" items={analysis.reasoning} />
      <AnalystStep title="Hypothesis" items={analysis.hypothesis} />
      <AnalystStep title="Confidence" items={[analysis.confidence]} />
      <AnalystStep title="Recommendation" items={analysis.recommendation} />
    </article>
  );
}

function AnalystStep({ items, title }: { items: string[]; title: string }) {
  return (
    <section className="ai-analyst-step">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </section>
  );
}

function toAnalystWorkflow(value: AiExplanation | IncidentReport | StrategySuggestion | MarketSummary) {
  if ("findings" in value) {
    return {
      confidence: value.suspicion,
      evidence: value.findings,
      hypothesis: [value.title],
      latencySec: value.latencySec,
      reasoning: [`Nebius AI compared ${value.findings.length} observed signals against known abuse patterns.`],
      recommendation: [value.recommendedAction],
      title: value.title,
      tokensUsed: value.tokensUsed
    };
  }
  if ("sections" in value) {
    return {
      confidence: value.severity,
      evidence: value.sections.slice(0, 3),
      hypothesis: [value.title],
      latencySec: value.latencySec,
      reasoning: value.sections.slice(3, 6).length ? value.sections.slice(3, 6) : ["Report sections were consolidated into an incident narrative."],
      recommendation: value.sections.slice(6).length ? value.sections.slice(6) : ["Review the generated report and attach it to the incident record."],
      title: value.title,
      tokensUsed: value.tokensUsed
    };
  }
  if ("bullets" in value) {
    return {
      confidence: "Strategy candidate",
      evidence: value.bullets.slice(0, 2),
      hypothesis: [value.title],
      latencySec: value.latencySec,
      reasoning: value.bullets.slice(2).length ? value.bullets.slice(2) : ["Nebius AI generated a structured strategy from the selected scenario context."],
      recommendation: [value.safetyNote],
      title: value.title,
      tokensUsed: value.tokensUsed
    };
  }
  return {
    confidence: value.regime,
    evidence: value.watchItems,
    hypothesis: [value.summary],
    latencySec: value.latencySec,
    reasoning: [`Nebius AI summarized ${value.watchItems.length} runtime signals into a market regime assessment.`],
    recommendation: ["Use this summary to choose the next investigation or batch-evaluation path."],
    title: value.regime,
    tokensUsed: value.tokensUsed
  };
}
