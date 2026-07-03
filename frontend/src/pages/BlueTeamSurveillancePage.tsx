import { useEffect, useMemo, useState } from "react";
import {
  createInvestigationReport,
  getReportsSummary,
  runSmartDetection,
  type InvestigationReportResponse,
  type OrderBookAlertResponse,
  type ReportsSummary
} from "@/api/client";
import { AgentTimeline } from "@/components/AgentTimeline";
import { DetectorConfidence } from "@/components/DetectorConfidence";
import { EvidencePanel } from "@/components/EvidencePanel";
import { IncidentDrawer } from "@/components/IncidentDrawer";
import { TeamMark } from "@/components/TeamMark";
import { useArenaSource } from "@/hooks/useArenaSource";
import type { AgentEvent, ArenaState, DetectorScore, EvidenceItem, Incident } from "@/types/arena";

type DetectionSecondaryView = "endpoint" | "report" | "events";

export function BlueTeamSurveillancePage() {
  const { mode, pause, running, sourceStatus, start, state } = useArenaSource();
  const [endpointAlert, setEndpointAlert] = useState<OrderBookAlertResponse | null>(null);
  const [report, setReport] = useState<InvestigationReportResponse | null>(null);
  const [reportsSummary, setReportsSummary] = useState<ReportsSummary | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [secondaryView, setSecondaryView] = useState<DetectionSecondaryView>("endpoint");
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
          <h2>Detection</h2>
        </div>
      </div>

      {message ? <div className="empty-state warning">{message}</div> : null}

      <div className="surveillance-status-strip">
        <Metric label="Source" value={`${mode}:${sourceStatus}`} tone={sourceStatus === "connected" ? "good" : "warn"} />
        <Metric label="Active Alerts" value={String(state.detectors.alerts.length)} tone={state.detectors.alerts.length ? "warn" : "good"} />
        <Metric label="Stored Incidents" value={String(persistedIncidentCount)} />
        <Metric label="AI Investigator Outputs" value={String(persistedExplanationCount)} />
      </div>

      <div className="nebius-button-row surveillance-actions">
        <button disabled={running} onClick={start} type="button">Start Surveillance</button>
        <button disabled={!running} onClick={pause} type="button">Pause</button>
        <button
          disabled={busy !== null}
          onClick={() => void runAction("endpoint detection", async () => {
            const response = await runSmartDetection();
            setEndpointAlert(response);
            setMessage(`Smart Detection scored ${response.detected_pattern} at ${(response.suspicion_score * 100).toFixed(0)}%.`);
          })}
          type="button"
        >
          Run Smart Detection
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
          Generate AI Investigator Report
        </button>
      </div>

      <div className="blue-team-grid">
        <section className="panel surveillance-card">
          <DetectorConfidence detectors={state.detectors} />
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

        <section className="panel surveillance-card wide">
          <EvidencePanel state={state} />
        </section>

        <section className="panel surveillance-card wide">
          <IncidentDrawer incident={activeIncident} currentTick={state.tick} incidentTick={activeIncident?.tick ?? state.tick} mode={activeIncident ? "live" : "replay"} />
        </section>

        <section className="panel surveillance-card wide secondary-widget-drawer">
          <div className="widget-tab-row" role="tablist" aria-label="Secondary detection widgets">
            <button className={secondaryView === "endpoint" ? "active" : ""} onClick={() => setSecondaryView("endpoint")} type="button">Smart Detection</button>
            <button className={secondaryView === "report" ? "active" : ""} onClick={() => setSecondaryView("report")} type="button">Report</button>
            <button className={secondaryView === "events" ? "active" : ""} onClick={() => setSecondaryView("events")} type="button">Events</button>
          </div>
          {secondaryView === "endpoint" ? (
            <EndpointScore endpointAlert={endpointAlert} />
          ) : secondaryView === "report" ? (
            <AiReportSummary report={report} />
          ) : (
            <AgentTimeline events={state.events} layout="compact" limit={12} title="Recent Evidence Events" />
          )}
        </section>
      </div>
    </section>
  );
}

function EndpointScore({ endpointAlert }: { endpointAlert: OrderBookAlertResponse | null }) {
  return (
    <section className="surveillance-card-tab">
      <h3>Smart Detection Score</h3>
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
        <p className="empty-state">Run Smart Detection to call the backend order-book alert adapter.</p>
      )}
    </section>
  );
}

function AiReportSummary({ report }: { report: InvestigationReportResponse | null }) {
  return (
    <section className="surveillance-card-tab">
      <h3>AI Investigator Report</h3>
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
        <p className="empty-state">Generate an AI Investigator report to persist incident narrative evidence.</p>
      )}
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
    id: `MOCK-${scenario.scenario_id}-${alert.name}`,
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
