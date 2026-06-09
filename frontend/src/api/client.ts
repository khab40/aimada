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
  explanation_id?: string | null;
  created_at?: string | null;
  stored_artifact?: string | null;
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
  mode: "local_serverless_job";
  status: "queued" | "running" | "generating_report" | "completed";
  created_at: string;
  command: string[];
  results: BenchmarkResult[];
  artifact_paths: Record<string, string>;
};

export type ArtifactReadResponse = {
  path: string;
  name: string;
  content_type: string;
  content: string;
};

export type ArtifactExportResponse = {
  path: string;
  download_url: string;
  format: "markdown" | "pdf";
};

export type BenchmarkCompareResponse = {
  run_ids: string[];
  rows: Record<string, unknown>[];
};

export type IncidentReplayResponse = {
  incident_id: string;
  incident: Record<string, unknown> | null;
  events: Record<string, unknown>[];
  labels: Record<string, unknown>[];
};

export type ScreenshotAttachmentResponse = {
  id: string;
  title: string;
  path: string;
  created_at: string;
};

export type PromoteEvidenceResponse = {
  run_id: string;
  path: string;
  download_url: string;
};

export type ReportsSummary = {
  experiments: Record<string, unknown>[];
  benchmark_runs: Record<string, unknown>[];
  incidents: Record<string, unknown>[];
  explanations: Record<string, unknown>[];
  attacks: Record<string, unknown>[];
  significant_events: Record<string, unknown>[];
};

export type NebiusStatus = {
  tenant_id_configured: boolean;
  incident_explainer_configured: boolean;
  scenario_generator_configured: boolean;
  api_key_configured: boolean;
  cli_installed: boolean;
  cli_path?: string | null;
  cli_version?: string | null;
};

export type SmartScenarioResponse = {
  mode: "nebius" | "mock";
  endpoint: string;
  scenario_type: string;
  title: string;
  description: string;
  parameters: Record<string, unknown>;
  expected_detector_risk: number;
  safety_note: string;
  fallback_reason?: string | null;
};

export type OrderBookAlertResponse = {
  mode: "nebius" | "mock";
  endpoint: string;
  suspicion_score: number;
  detected_pattern: string;
  confidence: number;
  reasons: string[];
  recommended_action: string;
  fallback_reason?: string | null;
};

export type SmartBatchRunResponse = {
  id: string;
  mode: "local_parallel_batch";
  status: "completed";
  created_at: string;
  elapsed_seconds: number;
  runs: number;
  batch_size: number;
  scenarios: string[];
  artifact_paths: Record<string, string>;
  metrics: Record<string, string>[];
};

export type NebiusObservatory = {
  usage: {
    endpoint_requests: number;
    endpoint_avg_latency_seconds: number;
    endpoint_purpose: string;
    job_simulations: number;
    job_runtime: string;
    job_output_files: number;
    job_artifacts: string[];
    evidence_status: "mock" | "local" | "nebius_needed";
  };
  screenshots: { title: string; status: string; path: string }[];
  benchmark_artifacts: Record<string, string>;
  latest_batch?: Record<string, unknown> | null;
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

export async function readArtifact(path: string): Promise<ArtifactReadResponse> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/artifacts/read?path=${encodeURIComponent(path)}`);
  if (!response.ok) {
    throw new Error(`Artifact read failed: ${response.status}`);
  }
  return response.json();
}

export function artifactDownloadUrl(path: string) {
  return `${API_BASE_URL}/api/experiments/artifacts/download?path=${encodeURIComponent(path)}`;
}

export async function exportArtifact(path: string, format: "markdown" | "pdf"): Promise<ArtifactExportResponse> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/artifacts/export`, {
    body: JSON.stringify({ format, path }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Artifact export failed: ${response.status}`);
  }
  return response.json();
}

export async function compareBenchmarkRuns(runIds: string[]): Promise<BenchmarkCompareResponse> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/benchmark-runs/compare`, {
    body: JSON.stringify({ run_ids: runIds }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Benchmark comparison failed: ${response.status}`);
  }
  return response.json();
}

export async function replayIncidentWindow(incidentId: string): Promise<IncidentReplayResponse> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/incidents/${encodeURIComponent(incidentId)}/replay`);
  if (!response.ok) {
    throw new Error(`Incident replay failed: ${response.status}`);
  }
  return response.json();
}

export async function attachNebiusScreenshot(path = "assets/screenshots/nebius-logs-metrics.svg"): Promise<ScreenshotAttachmentResponse> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/evidence/screenshots`, {
    body: JSON.stringify({ path, title: "Nebius logs and metrics" }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Screenshot attachment failed: ${response.status}`);
  }
  return response.json();
}

export async function promoteBenchmarkRun(runId: string): Promise<PromoteEvidenceResponse> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/benchmark-runs/${encodeURIComponent(runId)}/promote`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Promote run failed: ${response.status}`);
  }
  return response.json();
}

export async function getNebiusStatus(): Promise<NebiusStatus> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/status`);
  if (!response.ok) {
    throw new Error(`Nebius status failed: ${response.status}`);
  }
  return response.json();
}

export async function getNebiusObservatory(): Promise<NebiusObservatory> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/observatory`);
  if (!response.ok) {
    throw new Error(`Nebius observatory failed: ${response.status}`);
  }
  return response.json();
}

export async function createSmartScenario(): Promise<SmartScenarioResponse> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/smart-scenario`, {
    body: JSON.stringify({
      goal: "hard_to_detect",
      market_regime: "volatile",
      scenario_family: "quote_stuffing"
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Smart scenario failed: ${response.status}`);
  }
  return response.json();
}

export async function runSmartDetection(): Promise<OrderBookAlertResponse> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/smart-detection`, {
    body: JSON.stringify({
      bids: [{ owner: "abuser", price: 68120, quantity: 12.4 }],
      asks: [{ owner: "normal", price: 68130, quantity: 1.8 }],
      features: {
        cancel_to_trade_ratio: 5.4,
        depth_change_pct: 0.38,
        imbalance: 0.72,
        message_rate: 21,
        wall_size_ratio: 8.2
      },
      scenario_hint: "spoofing",
      tick: 12
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Smart detection failed: ${response.status}`);
  }
  return response.json();
}

export async function runSmartBatches(runs = 100, batchSize = 100): Promise<SmartBatchRunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/smart-batches`, {
    body: JSON.stringify({
      batch_size: batchSize,
      runs,
      scenarios: ["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"]
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Smart batch run failed: ${response.status}`);
  }
  return response.json();
}
