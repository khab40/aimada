import { useEffect, useState } from "react";
import { explainIncident, type IncidentExplanation } from "@/api/client";
import type { Incident } from "@/types/arena";

type InvestigatorState = "idle" | "analyzing" | "completed" | "error";

export function NebiusAIInvestigatorPanel({ incident }: { incident?: Incident | null }) {
  const [explanation, setExplanation] = useState<IncidentExplanation | null>(null);
  const [state, setState] = useState<InvestigatorState>("idle");

  useEffect(() => {
    setExplanation(null);
    setState("idle");
  }, [incident?.id]);

  async function analyzeIncident() {
    if (!incident) {
      return;
    }

    setState("analyzing");
    try {
      const result = incident.id.startsWith("MOCK-")
        ? await mockExplainIncident(incident)
        : await explainIncident(incident.id);
      setExplanation(result);
      setState("completed");
    } catch {
      setState("error");
    }
  }

  return (
    <section className={`nebius-investigator-panel ${state}`}>
      <div className="section-heading-row">
        <h3>AI Investigator</h3>
        <span className={`endpoint-badge investigator-status ${state}`}>{state}</span>
      </div>

      <p className="mock-endpoint">POST /api/incidents/{incident?.id ?? "{id}"}/explain</p>

      {state === "idle" && (
        <div className="investigator-state">
          <p>Ready to send the incident evidence package through FastAPI to Nebius AI when configured.</p>
          <button type="button" disabled={!incident} onClick={() => void analyzeIncident()}>
            Run AI Investigator
          </button>
        </div>
      )}

      {state === "analyzing" && (
        <div className="investigator-state">
          <p>Analyzing evidence package and replay timeline...</p>
          <div className="investigator-progress" aria-label="Mock analysis in progress" />
        </div>
      )}

      {state === "completed" && explanation && (
        <div className="investigator-result">
          <div className={`risk-level ${explanation.risk_level}`}>Risk level: {explanation.risk_level}</div>
          <span className="endpoint-badge">{explanation.endpoint}</span>
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
    </section>
  );
}

function mockExplainIncident(incident: Incident): Promise<IncidentExplanation> {
  return new Promise((resolve) => {
    window.setTimeout(() => {
      resolve({
        endpoint: "local mock investigator",
        evidence: incident.evidence.map((item) => `${item.label}: ${String(item.value)}${item.unit ? ` ${item.unit}` : ""}`),
        fallback_reason: "Frontend mock incident is not stored in the backend incident registry, so this result is not persisted.",
        incident_id: incident.id,
        mode: "mock",
        plain_english_summary:
          "The replay shows a synthetic abuse-like pattern where visible liquidity pressure appears, detector confidence rises, and the suspicious liquidity is removed before meaningful execution.",
        recommended_action: "Flag this simulated interval for manual review and compare the evidence bundle with detector thresholds.",
        risk_level: incident.severity === "Critical" ? "critical" : incident.severity === "High" ? "high" : "medium"
      });
    }, 850);
  });
}
