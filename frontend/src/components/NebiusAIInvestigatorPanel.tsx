import { useEffect, useState } from "react";
import { createInvestigationReport, explainIncident, type IncidentExplanation, type InvestigationReportResponse } from "@/api/client";
import type { ProductDemoConfig } from "@/demoModes";
import type { Incident } from "@/types/arena";

type InvestigatorState = "idle" | "analyzing" | "completed" | "error";

type AiRunMetrics = {
  estimatedCost: string;
  lastExecution: string;
  latency: string;
  mode: string;
  models: string;
  provider: string;
  runtime: string;
  status: string;
  tokensIn: string;
  tokensOut: string;
};

export function NebiusAIInvestigatorPanel({
  demoConfig,
  incident
}: {
  demoConfig?: ProductDemoConfig | null;
  incident?: Incident | null;
}) {
  const [explanation, setExplanation] = useState<IncidentExplanation | null>(null);
  const [metrics, setMetrics] = useState<AiRunMetrics>(() => createInitialMetrics(demoConfig));
  const [state, setState] = useState<InvestigatorState>("idle");

  useEffect(() => {
    setExplanation(null);
    setMetrics(createInitialMetrics(demoConfig));
    setState("idle");
  }, [demoConfig, incident?.id]);

  async function analyzeIncident() {
    if (!incident) {
      return;
    }

    const startedAt = performance.now();
    setState("analyzing");
    setMetrics((current) => ({ ...current, status: "Running" }));
    try {
      const result = demoConfig?.id === "real"
        ? toIncidentExplanation(await createInvestigationReport(), incident)
        : incident.id.startsWith("MOCK-") || incident.id.startsWith("DEMO-")
          ? await mockExplainIncident(incident, demoConfig)
          : await explainIncident(incident.id);
      setExplanation(result);
      setMetrics(createCompletedMetrics(demoConfig, incident, result, startedAt));
      setState("completed");
    } catch {
      const result = await mockExplainIncident(incident, demoConfig, "Nebius unavailable. Using cached demo explanation.");
      setExplanation(result);
      setMetrics(createCompletedMetrics(demoConfig, incident, result, startedAt));
      setState("completed");
    }
  }

  return (
    <section className={`nebius-investigator-panel ${state}`}>
      <div className="section-heading-row">
        <h3>AI Investigator</h3>
        <span className={`endpoint-badge investigator-status ${state}`}>{state}</span>
      </div>

      {state === "idle" && (
        <div className="investigator-state">
          <button type="button" disabled={!incident} onClick={() => void analyzeIncident()}>
            Run AI Investigator
          </button>
        </div>
      )}

      {state === "analyzing" && (
        <div className="investigator-state">
          <p>Analyzing evidence package and replay timeline...</p>
          {demoConfig?.id === "streaming" ? (
            <ol className="streaming-demo-steps">
              <li>Connecting</li>
              <li>Retrieving context</li>
              <li>Reasoning</li>
              <li>Streaming explanation</li>
              <li>Updating metrics</li>
            </ol>
          ) : null}
          <div className="investigator-progress" aria-label="Mock analysis in progress" />
        </div>
      )}

      {state === "completed" && explanation && (
        <div className="investigator-result">
          <div className={`risk-level ${explanation.risk_level}`}>Risk level: {explanation.risk_level}</div>
          {explanation.explanation_id ? (
            <p className="persistence-note">
              Saved as <code>{explanation.explanation_id}</code>
              {explanation.stored_artifact ? <> in <code>{explanation.stored_artifact}</code></> : null}
            </p>
          ) : null}
          <p>{explanation.plain_english_summary}</p>
          <h4>Evidence</h4>
          <ul>
            {explanation.evidence.map((item) => <li key={item}>{item}</li>)}
          </ul>
          <h4>Recommended action</h4>
          <p>{explanation.recommended_action}</p>
          {explanation.fallback_reason ? <p className="fallback-note">{explanation.fallback_reason}</p> : null}
        </div>
      )}

      {state === "error" && (
        <div className="investigator-state error">
          <p>Incident analysis failed. Retry the backend Nebius AI call.</p>
          <button type="button" onClick={() => void analyzeIncident()}>Retry Analysis</button>
        </div>
      )}

      <AiCostLatencyCard metrics={metrics} />
    </section>
  );
}

function AiCostLatencyCard({ metrics }: { metrics: AiRunMetrics }) {
  return (
    <section className="ai-cost-latency-card" aria-label="AI cost and latency">
      <div className="section-heading-row">
        <h4>AI Cost &amp; Latency</h4>
        <span>{metrics.status}</span>
      </div>
      <dl className="ai-cost-latency-grid">
        <div><dt>Provider</dt><dd>{metrics.provider}</dd></div>
        <div><dt>Mode</dt><dd>{metrics.mode}</dd></div>
        <div><dt>Model(s)</dt><dd>{metrics.models}</dd></div>
        <div><dt>Latency</dt><dd>{metrics.latency}</dd></div>
        <div><dt>Tokens in</dt><dd>{metrics.tokensIn}</dd></div>
        <div><dt>Tokens out</dt><dd>{metrics.tokensOut}</dd></div>
        <div><dt>Estimated cost</dt><dd>{metrics.estimatedCost}</dd></div>
        <div><dt>GPU/runtime</dt><dd>{metrics.runtime}</dd></div>
        <div><dt>Last execution time</dt><dd>{metrics.lastExecution}</dd></div>
      </dl>
    </section>
  );
}

function createInitialMetrics(demoConfig?: ProductDemoConfig | null): AiRunMetrics {
  return {
    estimatedCost: "-",
    lastExecution: "Not run yet",
    latency: "-",
    mode: demoConfig?.aiInvestigationMode ?? "Structured incident explanation",
    models: demoConfig?.models ?? "Nebius AI incident explainer",
    provider: "Nebius AI",
    runtime: demoConfig ? "Demo runtime" : "Nebius Serverless GPU",
    status: "Idle",
    tokensIn: "-",
    tokensOut: "-"
  };
}

function createCompletedMetrics(
  demoConfig: ProductDemoConfig | null | undefined,
  incident: Incident,
  explanation: IncidentExplanation,
  startedAt: number
): AiRunMetrics {
  const tokensIn = 1200 + incident.evidence.length * 95 + incident.title.length * 4;
  const tokensOut = 360 + explanation.evidence.length * 44 + explanation.recommended_action.length;
  const simulated = explanation.mode === "mock" || Boolean(explanation.fallback_reason);
  return {
    estimatedCost: simulated ? "$0.0000 simulated" : `$${((tokensIn * 0.00000045) + (tokensOut * 0.0000012)).toFixed(4)}`,
    lastExecution: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    latency: `${Math.max(0.2, (performance.now() - startedAt) / 1000).toFixed(1)}s`,
    mode: demoConfig?.aiInvestigationMode ?? explanation.mode,
    models: demoConfig?.models ?? "Nebius AI incident explainer",
    provider: simulated ? "Nebius AI (simulated fallback)" : "Nebius AI",
    runtime: simulated ? "Cached demo response" : "Nebius Serverless GPU",
    status: simulated ? "Simulated fallback" : "Completed",
    tokensIn: tokensIn.toLocaleString(),
    tokensOut: tokensOut.toLocaleString()
  };
}

function mockExplainIncident(
  incident: Incident,
  demoConfig?: ProductDemoConfig | null,
  fallbackReason = "Simulated fallback. Using cached demo explanation."
): Promise<IncidentExplanation> {
  return new Promise((resolve) => {
    window.setTimeout(() => {
      resolve({
        endpoint: "local mock investigator",
        evidence: incident.evidence.map((item) => `${item.label}: ${String(item.value)}${item.unit ? ` ${item.unit}` : ""}`),
        fallback_reason: fallbackReason,
        incident_id: incident.id,
        mode: "mock",
        plain_english_summary: demoConfig
          ? `${demoConfig.title} shows ${demoConfig.attackPattern.toLowerCase()} on ${demoConfig.marketSymbol}. Evidence crosses the ${demoConfig.detectorProfile.toLowerCase()} threshold and produces a structured analyst explanation.`
          : "The replay shows a synthetic abuse-like pattern where visible liquidity pressure appears, detector confidence rises, and the suspicious liquidity is removed before meaningful execution.",
        recommended_action: demoConfig?.id === "two-model"
          ? "Escalate after classifier confirmation, then use the reasoning model recommendation for compliance review."
          : demoConfig?.id === "streaming"
            ? "Use the streamed reasoning trail to brief the analyst, then export the evidence bundle."
            : "Flag this simulated interval for manual review and compare the evidence bundle with detector thresholds.",
        risk_level: incident.severity === "Critical" ? "critical" : incident.severity === "High" ? "high" : "medium"
      });
    }, 850);
  });
}

function toIncidentExplanation(report: InvestigationReportResponse, incident: Incident): IncidentExplanation {
  return {
    endpoint: report.endpoint,
    evidence: report.detector_findings.length ? report.detector_findings : report.timeline,
    fallback_reason: report.fallback_reason,
    incident_id: incident.id,
    mode: report.mode,
    plain_english_summary: report.summary,
    recommended_action: report.recommended_next_steps.join(" "),
    risk_level: incident.severity === "Critical" ? "critical" : incident.severity === "High" ? "high" : "medium"
  };
}
