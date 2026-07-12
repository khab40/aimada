import { useEffect, useState } from "react";
import { createInvestigationReport, explainIncident, type IncidentExplanation, type InvestigationReportResponse } from "@/api/client";
import { AiCostLatencyCard, type NebiusExecutionTraceData } from "@/components/NebiusExecutionTrace";
import type { ProductDemoConfig } from "@/demoModes";
import { getStoredRuntimeMode, RUNTIME_MODE_EVENT, type RuntimeMode } from "@/runtimeModes";
import type { Incident } from "@/types/arena";

type InvestigatorState = "idle" | "analyzing" | "completed" | "error";

export function NebiusAIInvestigatorPanel({
  demoConfig,
  incident
}: {
  demoConfig?: ProductDemoConfig | null;
  incident?: Incident | null;
}) {
  const [explanation, setExplanation] = useState<IncidentExplanation | null>(null);
  const [runtimeMode, setRuntimeMode] = useState<RuntimeMode>(() => getStoredRuntimeMode());
  const [trace, setTrace] = useState<NebiusExecutionTraceData>(() => createInitialTrace(demoConfig, runtimeMode));
  const [state, setState] = useState<InvestigatorState>("idle");

  useEffect(() => {
    setExplanation(null);
    setTrace(createInitialTrace(demoConfig, runtimeMode));
    setState("idle");
  }, [demoConfig, incident?.id, runtimeMode]);

  useEffect(() => {
    function syncRuntimeMode(event: Event) {
      const next = event instanceof CustomEvent && typeof event.detail === "string"
        ? event.detail
        : getStoredRuntimeMode();
      if (next === "local-demo" || next === "nebius-cloud") {
        setRuntimeMode(next);
      }
    }
    window.addEventListener(RUNTIME_MODE_EVENT, syncRuntimeMode);
    window.addEventListener("storage", syncRuntimeMode);
    return () => {
      window.removeEventListener(RUNTIME_MODE_EVENT, syncRuntimeMode);
      window.removeEventListener("storage", syncRuntimeMode);
    };
  }, []);

  async function analyzeIncident() {
    if (!incident) {
      return;
    }

    const startedAt = performance.now();
    setState("analyzing");
    setTrace((current) => ({ ...current, status: "running" }));
    try {
      const result = demoConfig?.id === "real"
        ? toIncidentExplanation(await createInvestigationReport(), incident)
        : incident.id.startsWith("MOCK-") || incident.id.startsWith("DEMO-")
          ? await mockExplainIncident(incident, demoConfig)
          : await explainIncident(incident.id);
      setExplanation(result);
      setTrace(createCompletedTrace(demoConfig, incident, result, startedAt, runtimeMode));
      setState("completed");
    } catch {
      const result = await mockExplainIncident(incident, demoConfig, "Nebius unavailable. Using cached demo explanation.");
      setExplanation(result);
      setTrace(createCompletedTrace(demoConfig, incident, result, startedAt, runtimeMode));
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
            Explain with Nebius AI
          </button>
          <p className="fallback-note">{runtimeMode === "nebius-cloud" ? "Nebius Cloud calls a real endpoint when configured. If Nebius fails, the response falls back to deterministic mock AI." : "Local Demo uses a deterministic mock response. Switch to Nebius Cloud to run this explanation on a real Nebius endpoint."}</p>
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
          <div className="structured-ai-output">
            <article>
              <h4>Hypothesis</h4>
              <p>{explanation.plain_english_summary}</p>
            </article>
            <article>
              <h4>Evidence</h4>
              <ul>
                {explanation.evidence.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </article>
            <article>
              <h4>Alternative explanation</h4>
              <p>{alternativeExplanationFor(incident)}</p>
            </article>
            <article>
              <h4>Confidence</h4>
              <p>{confidenceTextFor(incident, explanation)}</p>
            </article>
            <article>
              <h4>Recommendation</h4>
              <p>{explanation.recommended_action}</p>
            </article>
          </div>
          {explanation.fallback_reason ? <p className="fallback-note">{explanation.fallback_reason}</p> : null}
        </div>
      )}

      {state === "error" && (
        <div className="investigator-state error">
          <p>Incident analysis failed. Retry the backend Nebius AI call.</p>
          <button type="button" onClick={() => void analyzeIncident()}>Retry Analysis</button>
        </div>
      )}

      <AiCostLatencyCard trace={trace} />
    </section>
  );
}

function alternativeExplanationFor(incident: Incident | null | undefined) {
  const context = incident?.title ?? "the selected incident";
  return `Benign liquidity withdrawal in ${context} remains possible, but the timing, cancellation pattern, and detector evidence make the abuse hypothesis stronger.`;
}

function confidenceTextFor(incident: Incident | null | undefined, explanation: IncidentExplanation) {
  const score = typeof incident?.confidence === "number" ? `${Math.round(incident.confidence * 100)}%` : explanation.risk_level;
  return `${score} confidence, based on the detector score, evidence count, and replay context.`;
}

function createInitialTrace(demoConfig: ProductDemoConfig | null | undefined, runtimeMode: RuntimeMode): NebiusExecutionTraceData {
  return {
    artifactLink: null,
    endpointId: "nebius-ai-endpoint",
    estimatedCost: "-",
    executionType: demoConfig?.id === "streaming" ? "streaming" : "endpoint",
    fallback: runtimeMode === "local-demo" || demoConfig ? "Simulated / Local Demo" : "simulated",
    jobId: null,
    lastExecutionTime: "Not run yet",
    latency: "-",
    model: demoConfig?.models ?? "Nebius AI incident explainer",
    runId: demoConfig ? `demo-${demoConfig.id}` : "arena-endpoint",
    runtimeGpu: runtimeMode === "nebius-cloud" ? "Nebius Cloud runtime" : "Local Demo",
    status: "Idle",
    tokensIn: "-",
    tokensOut: "-"
  };
}

function createCompletedTrace(
  demoConfig: ProductDemoConfig | null | undefined,
  incident: Incident,
  explanation: IncidentExplanation,
  startedAt: number,
  runtimeMode: RuntimeMode
): NebiusExecutionTraceData {
  const tokensIn = 1200 + incident.evidence.length * 95 + incident.title.length * 4;
  const tokensOut = 360 + explanation.evidence.length * 44 + explanation.recommended_action.length;
  const simulated = explanation.mode === "mock" || Boolean(explanation.fallback_reason);
  return {
    artifactLink: explanation.stored_artifact ?? null,
    endpointId: explanation.endpoint,
    estimatedCost: simulated ? "$0.0000 simulated" : `$${((tokensIn * 0.00000045) + (tokensOut * 0.0000012)).toFixed(4)}`,
    executionType: demoConfig?.id === "streaming" ? "streaming" : "endpoint",
    fallback: simulated && runtimeMode === "local-demo" ? "Simulated / Local Demo" : simulated ? "simulated" : "real",
    jobId: null,
    lastExecutionTime: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    latency: `${Math.max(0.2, (performance.now() - startedAt) / 1000).toFixed(1)}s`,
    model: demoConfig?.models ?? "Nebius AI incident explainer",
    runId: incident.id,
    runtimeGpu: simulated ? runtimeMode === "nebius-cloud" ? "Nebius Cloud fallback" : "Local Demo mock AI" : "Nebius Serverless GPU",
    status: simulated ? runtimeMode === "local-demo" ? "Simulated / Local Demo" : "Simulated fallback" : "real endpoint used",
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
