import type { BenchmarkResult, ScenarioConfig } from "@/types/arena";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}

export async function launchScenario(name: string): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/scenarios/${name}`, {
    method: "POST"
  });
  return response.json();
}

export async function getBenchmarkSummary(): Promise<BenchmarkResult[]> {
  const response = await fetch(`${API_BASE_URL}/benchmark/summary`);
  return response.json();
}

export type IncidentExplanation = {
  mode: "nebius" | "mock";
  endpoint: string;
  incident_id: string;
  risk_level: string;
  plain_english_summary: string;
  evidence: string[];
  recommended_action: string;
  fallback_reason?: string | null;
};

export async function explainIncident(incidentId: string): Promise<IncidentExplanation> {
  const response = await fetch(`${API_BASE_URL}/api/incidents/${incidentId}/explain`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Incident explanation failed: ${response.status}`);
  }
  return response.json();
}

export type RedTeamScenarioGenerateRequest = {
  scenario_family: string;
  market_regime: "calm" | "volatile" | "thin_liquidity";
  goal: "obvious" | "stealth" | "hard_to_detect";
  constraints: Record<string, unknown>;
};

export type AttackExperimentRequest = {
  scenario_type: string;
  wall_size_multiplier: number;
  lifetime_seconds: number;
  distance_from_mid_bps: number;
  cancel_style: "instant" | "gradual" | "partial";
  noise_cover: "none" | "low" | "high";
  predicted_detection_risk: number;
};

export type SavedExperiment = {
  id: string;
  kind: "attack_builder";
  created_at: string;
  config: AttackExperimentRequest;
};

export type LabLaunchResponse = {
  experiment_id: string;
  launch_endpoint: string;
  attack: unknown;
};

export type BenchmarkRunRequest = {
  runs: number;
  market_regime: string;
  scenarios: string[];
  detectors: string;
};

export type BenchmarkRunResponse = {
  id: string;
  mode: "mock_nebius_serverless_job";
  status: "queued" | "running" | "generating_report" | "completed";
  created_at: string;
  command: string[];
  results: BenchmarkResult[];
  artifact_paths: Record<string, string>;
};

export type ReportsSummary = {
  experiments: Record<string, unknown>[];
  benchmark_runs: Record<string, unknown>[];
  incidents: Record<string, unknown>[];
  attacks: Record<string, unknown>[];
  significant_events: Record<string, unknown>[];
};

export async function generateRedTeamScenario(
  request: RedTeamScenarioGenerateRequest
): Promise<ScenarioConfig> {
  const response = await fetch(`${API_BASE_URL}/api/red-team/generate-scenario`, {
    body: JSON.stringify(request),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Red-team scenario generation failed: ${response.status}`);
  }
  return response.json();
}

export async function saveAttackExperiment(request: AttackExperimentRequest): Promise<SavedExperiment> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/attacks`, {
    body: JSON.stringify(request),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Save experiment failed: ${response.status}`);
  }
  return response.json();
}

export async function launchAttackExperiment(request: AttackExperimentRequest): Promise<LabLaunchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/attacks/launch`, {
    body: JSON.stringify(request),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Launch experiment failed: ${response.status}`);
  }
  return response.json();
}

export async function runBenchmarkExperiment(request: BenchmarkRunRequest): Promise<BenchmarkRunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/benchmark-runs`, {
    body: JSON.stringify(request),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Benchmark run failed: ${response.status}`);
  }
  return response.json();
}

export async function getReportsSummary(): Promise<ReportsSummary> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/reports`);
  if (!response.ok) {
    throw new Error(`Reports summary failed: ${response.status}`);
  }
  return response.json();
}
