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
          <p className="eyebrow">Nebius AI</p>
          <h2>AI Investigator Console</h2>
        </div>
        <span className={`runtime-top-badge ${endpointStatus.toLowerCase()}`}>Endpoint: {endpointStatus}</span>
      </div>
      <p className="nebius-card-purpose">
        Use Nebius AI to explain suspicious market behavior, generate AI Investigator reports, suggest red-team strategies, and summarize market regimes.
      </p>
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
  if ("findings" in value) {
    return (
      <article>
        <h3>{value.title}</h3>
        <p><strong>Suspicion:</strong> {value.suspicion}</p>
        <p>The observed pattern is consistent with spoofing:</p>
        <ol>
          {value.findings.map((finding) => <li key={finding}>{finding}</li>)}
        </ol>
        <p><strong>Recommended action:</strong> {value.recommendedAction}</p>
      </article>
    );
  }
  if ("sections" in value) {
    return (
      <article>
        <h3>{value.title}</h3>
        <p><strong>Severity:</strong> {value.severity}</p>
        <ul>{value.sections.map((section) => <li key={section}>{section}</li>)}</ul>
      </article>
    );
  }
  if ("bullets" in value) {
    return (
      <article>
        <h3>{value.title}</h3>
        <ul>{value.bullets.map((item) => <li key={item}>{item}</li>)}</ul>
        <p>{value.safetyNote}</p>
      </article>
    );
  }
  return (
    <article>
      <h3>{value.regime}</h3>
      <p>{value.summary}</p>
      <ul>{value.watchItems.map((item) => <li key={item}>{item}</li>)}</ul>
    </article>
  );
}
