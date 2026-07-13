import type { AIInvestigationTeamRequest } from "@/api/client";
import type { Incident } from "@/types/arena";

const STORAGE_KEY = "aimada.control-center.incident";

export function storeControlCenterIncident(incident: Incident) {
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(incident));
}

export function controlCenterIncidentPath(incident: Incident) {
  return `/nebius?step=3&incidentId=${encodeURIComponent(incident.id)}`;
}

export function loadControlCenterIncident(expectedId: string | null): Incident | null {
  if (!expectedId) return null;
  const serialized = window.sessionStorage.getItem(STORAGE_KEY);
  if (!serialized) return null;
  try {
    const incident = JSON.parse(serialized) as Incident;
    return incident.id === expectedId ? incident : null;
  } catch {
    window.sessionStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function incidentInvestigationRequest(incident: Incident): AIInvestigationTeamRequest {
  return {
    incident: {
      agent: incident.agent,
      confidence: incident.confidence,
      explanation: incident.explanation,
      id: incident.id,
      scenario_family: incident.scenario_family,
      scenario_id: incident.scenario_id,
      severity: incident.severity,
      tick: incident.tick,
      title: incident.title,
      type: incident.type
    },
    detector_outputs: [{
      confidence: incident.confidence,
      detected_pattern: incident.type,
      detector: incident.title,
      evidence: incident.evidence.map((item) => `${item.label}: ${String(item.value)}${item.unit ? ` ${item.unit}` : ""}`),
      suspicion_score: incident.confidence
    }],
    market_metrics: Object.fromEntries(incident.evidence.map((item) => [item.key, item.value])),
    order_book_context: {},
    trades: []
  };
}
