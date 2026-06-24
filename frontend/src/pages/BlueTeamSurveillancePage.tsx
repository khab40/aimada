import { useEffect, useMemo, useState } from "react";
import {
  createInvestigationReport,
  getReportsSummary,
  runSmartDetection,
  type InvestigationReportResponse,
  type OrderBookAlertResponse,
  type ReportsSummary
} from "@/api/client";
import { AgentEventTape } from "@/components/AgentEventTape";
import { DetectorConfidencePanel } from "@/components/DetectorConfidencePanel";
import { EvidencePanel } from "@/components/EvidencePanel";
import { IncidentReplayDrawer } from "@/components/IncidentReplayDrawer";
import { TeamMark } from "@/components/TeamMark";
import { useArenaSource } from "@/hooks/useArenaSource";
import type { AgentEvent, ArenaState, DetectorScore, EvidenceItem, Incident } from "@/types/arena";

export function BlueTeamSurveillancePage() {
  const { mode, pause, running, sourceStatus, start, state, tick } = useArenaSource();
  const [endpointAlert, setEndpointAlert] = useState<OrderBookAlertResponse | null>(null);
  const [report, setReport] = useState<InvestigationReportResponse | null>(null);
  const [reportsSummary, setReportsSummary] = useState<ReportsSummary | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const activeIncident = useMemo(() => createIncident(state), [state]);
  const suspiciousAgents = useMemo(() => buildSuspiciousAgents(state), [state]);

  useEffect(() => {
    void refreshReports();
  }, []);

  async function refreshReports() {
    setReportsSummary(await getReportsSummary());
  }

  async function runAction(label: string, action: () => Promise<void>) {
    setBusy(label);
    setMessage(null);
    try {
      await action();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : `${label} failed.`);
    } finally {
      setBusy(null);
    }
  }

  const persistedIncidentCount = reportsSummary?.incidents.length ?? 0;
  const persistedExplanationCount = reportsSummary?.explanations.length ?? 0;

  return (
    <section className="blue-team-page">
      <div className="panel lab-hero-panel team-hero blue">
        <TeamMark team="blue" />
        <div>
          <p className="eyebrow">Blue-team workspace</p>
          <h2>Blue Team Surveillance</h2>
          <p>Monitor live detector scores, suspicious agents, incident evidence, and Nebius AI endpoint analysis from one surveillance desk.</p>
        </div>
        <div className="team-hero-badges">
          <span className="team-badge blue">Blue Team</span>
          <span className="endpoint-badge">source {mode}:{sourceStatus}</span>
        </div>
      </div>

      {message ? <div className="empty-state warning">{message}</div> : null}

      <div className="surveillance-status-strip">
        <Metric label="Tick" value={tick.toLocaleString()} />
        <Metric label="Running" value={running ? "yes" : "no"} tone={running ? "good" : "warn"} />
        <Metric label="Active Alerts" value={String(state.detectors.alerts.length)} tone={state.detectors.alerts.length ? "warn" : "good"} />
        <Metric label="Stored Incidents" value={String(persistedIncidentCount)} />
        <Metric label="AI Explanations" value={String(persistedExplanationCount)} />
      </div>

      <div className="nebius-button-row surveillance-actions">
        <button disabled={running} onClick={start} type="button">Start Surveillance</button>
        <button disabled={!running} onClick={pause} type="button">Pause</button>
        <button
          disabled={busy !== null}
          onClick={() => void runAction("endpoint detection", async () => {
            const response = await runSmartDetection();
            setEndpointAlert(response);
            setMessage(`Nebius endpoint scored ${response.detected_pattern} at ${(response.suspicion_score * 100).toFixed(0)}%.`);
          })}
          type="button"
        >
          Run Nebius Detection
        </button>
        <button
          disabled={busy !== null}
          onClick={() => void runAction("investigation report", async () => {
            const response = await createInvestigationReport();
            setReport(response);
            await refreshReports();
          })}
          type="button"
        >
          Generate AI Report
        </button>
      </div>

      <div className="blue-team-grid">
        <section className="panel surveillance-card">
          <DetectorConfidencePanel detectors={state.detectors} />
        </section>

        <section className="panel surveillance-card">
          <h3>Suspicious Agents</h3>
          <div className="suspicious-agent-list">
            {suspiciousAgents.length ? suspiciousAgents.map((agent) => (
              <article key={agent.id}>
                <div>
                  <strong>{agent.id}</strong>
                  <span>{agent.reason}</span>
                </div>
                <strong>{agent.score.toFixed(2)}</strong>
              </article>
            )) : <p className="empty-state">No suspicious agents are active.</p>}
          </div>
        </section>

        <section className="panel surveillance-card">
          <h3>Nebius Endpoint Score</h3>
          {endpointAlert ? (
            <div className="endpoint-result">
              <div className="endpoint-score">
                <span>Suspicion</span>
                <strong>{endpointAlert.suspicion_score.toFixed(2)}</strong>
              </div>
              <p><strong>Pattern:</strong> {endpointAlert.detected_pattern}</p>
              <ul>
                {endpointAlert.reasons.map((reason) => <li key={reason}>{reason}</li>)}
              </ul>
              <p>{endpointAlert.recommended_action}</p>
            </div>
          ) : (
            <p className="empty-state">Run Nebius Detection to call the backend order-book alert adapter.</p>
          )}
        </section>

        <section className="panel surveillance-card wide">
          <EvidencePanel state={state} />
        </section>

        <section className="panel surveillance-card wide">
          <IncidentReplayDrawer activeIncident={activeIncident} currentTick={state.tick} incidentTick={activeIncident?.tick ?? state.tick} live={Boolean(activeIncident)} />
        </section>

        <section className="panel surveillance-card">
          <h3>AI Incident Report</h3>
          {report ? (
            <div className="ai-report-summary">
              <span className="endpoint-badge">{report.mode}</span>
              <h4>{report.title}</h4>
              <p>{report.summary}</p>
              <ul>
                {report.detector_findings.map((finding) => <li key={finding}>{finding}</li>)}
              </ul>
            </div>
          ) : (
            <p className="empty-state">Generate an AI report to persist incident narrative evidence.</p>
          )}
        </section>

        <section className="panel surveillance-card">
          <h3>Recent Evidence Events</h3>
          <AgentEventTape events={state.events.slice(-12)} />
        </section>
      </div>
    </section>
  );
}

function Metric({ label, tone, value }: { label: string; tone?: "good" | "warn"; value: string }) {
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
  if (!alert || !scenario) {
    return null;
  }

  return {
    agent: scenario.agent_id,
    confidence: alert.confidence,
    evidence: evidenceFrom(state, alert),
    explanation: `${scenario.scenario_name} raised ${alert.name} with confidence ${alert.confidence.toFixed(2)} in the live arena stream.`,
    id: `MOCK-${state.tick}`,
    scenario_family: scenario.scenario_family,
    scenario_id: scenario.scenario_id,
    severity: alert.severity === "critical" ? "Critical" : alert.severity === "high" ? "High" : "Medium",
    title: `${alert.name} surveillance alert`,
    type: scenario.scenario_name
  };
}

function evidenceFrom(state: ArenaState, alert: DetectorScore): EvidenceItem[] {
  if (alert.evidence?.length) {
    return alert.evidence;
  }
  return [
    { key: "confidence", label: "Detector confidence", value: alert.confidence.toFixed(2) },
    { key: "message_rate", label: "Message rate", value: state.features?.message_rate ?? "n/a", unit: "updates/sec" },
    { key: "wall_size_ratio", label: "Wall size ratio", value: state.features?.wall_size_ratio ?? "n/a" },
    { key: "cancel_to_trade_ratio", label: "Cancel/trade ratio", value: state.features?.cancel_to_trade_ratio ?? "n/a" }
  ];
}

function buildSuspiciousAgents(state: ArenaState) {
  const agents = new Map<string, { id: string; reason: string; score: number }>();
  if (state.active_scenario) {
    agents.set(state.active_scenario.agent_id, {
      id: state.active_scenario.agent_id,
      reason: `${state.active_scenario.scenario_name} ${state.active_scenario.current_stage ?? state.active_scenario.status}`,
      score: state.detectors.alerts[0]?.confidence ?? 0.62
    });
  }
  for (const event of state.events) {
    const agentId = eventAgent(event);
    if (!agentId || !looksSuspicious(event)) continue;
    const current = agents.get(agentId);
    agents.set(agentId, {
      id: agentId,
      reason: String(event.message ?? event.type ?? "suspicious event"),
      score: Math.max(current?.score ?? 0, state.detectors.alerts[0]?.confidence ?? 0.58)
    });
  }
  return Array.from(agents.values()).sort((a, b) => b.score - a.score).slice(0, 6);
}

function eventAgent(event: AgentEvent) {
  return event.agent_id ?? event.aggressor_agent_id ?? event.resting_agent_id;
}

function looksSuspicious(event: AgentEvent) {
  const type = String(event.type ?? "").toLowerCase();
  const stage = String(event.stage ?? "").toLowerCase();
  return type.includes("red") || type.includes("attack") || stage.includes("cancel") || stage.includes("wall") || Boolean(event.scenario_id);
}
