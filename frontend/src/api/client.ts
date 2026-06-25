import type { BenchmarkResult, ScenarioConfig } from "@/types/arena";
import type {
  AttackScenario,
  AttackScenarioInput,
  ExperimentArtifact,
  GeneratedScenario,
  ScenarioGridConfig
} from "@/features/nebius/types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const AUTH_SESSION_HEADER = "X-AIMADA-Session-ID";

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

export type ManagedExperimentStatus = "draft" | "manifest_generated" | "submitted" | "running" | "completed" | "failed";
export type ManagedExperimentMode = "mock" | "local_parallel_batch" | "real_nebius_pending";

export type ManagedExperimentCreateRequest = {
  name?: string;
  attack_count?: number;
  batch_size?: number;
  scenarios?: string[];
  seed?: number;
  nebius_mode?: ManagedExperimentMode;
};

export type ManagedExperiment = {
  id: string;
  name: string;
  status: ManagedExperimentStatus;
  attack_count: number;
  batch_size: number;
  scenarios: string[];
  seed: number;
  nebius_mode: ManagedExperimentMode;
  smart_batch_id?: string | null;
  artifact_dir: string;
  artifact_paths: Record<string, string>;
  metrics: Record<string, unknown>[];
  created_at: string;
  updated_at: string;
};

export type ManagedExperimentDeleteResponse = {
  id: string;
  deleted: boolean;
};

export type AttackManifestResponse = {
  experiment_id: string;
  path: string;
  attack_count: number;
  scenarios: string[];
  status: ManagedExperimentStatus;
};

export type ExperimentLocalBatchRunResponse = {
  id: string;
  experiment_id: string;
  mode: "local_parallel_batch";
  status: "completed" | "failed";
  created_at: string;
  elapsed_seconds: number;
  runs: number;
  batch_size: number;
  scenarios: string[];
  artifact_paths: Record<string, string>;
  metrics: Record<string, unknown>[];
  error?: Record<string, unknown> | null;
};

export type ArtifactNormalizationResponse = {
  experiment_id: string;
  artifact_dir: string;
  artifact_paths: Record<string, string>;
  copied_count: number;
  missing: string[];
};

export type ExperimentJobRecord = {
  job_id: string;
  experiment_id: string;
  backend: "local_parallel_batch" | "nebius_serverless_job";
  status: "queued" | "running" | "completed" | "failed" | "real_nebius_pending";
  batch_start: number;
  batch_end: number;
  attack_count: number;
  created_at: string;
  updated_at: string;
  message: string;
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
  ticks: Record<string, unknown>[];
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

export type ClearReportsResponse = {
  deleted_files: string[];
  deleted_dirs: string[];
  message: string;
};

export type ArenaRole = "attacker" | "defender" | "observer" | "judge";

export type AuthUser = {
  id?: string;
  user_id: string;
  email: string;
  name: string;
  avatar_url?: string | null;
  google_id?: string | null;
  google_subject?: string | null;
  auth_provider?: "google" | string;
  provider: string;
  provider_mode?: string | null;
  created_at: string;
  updated_at?: string;
};

export type AuthSession = {
  session_id: string;
  user_id: string;
  role: ArenaRole;
  created_at: string;
  last_seen_at: string;
  active: boolean;
};

export type GoogleAuthConfig = {
  mode: "google" | "stub" | string;
  configured: boolean;
  client_id?: string | null;
  authorization_url?: string | null;
  detail: string;
};

export type GoogleCompletePayload = {
  authorization_code?: string;
  code?: string;
  id_token?: string;
  redirect_uri?: string;
};

export type AuthSessionResponse = {
  user: AuthUser;
  session: AuthSession;
  restored_history?: Record<string, unknown> | null;
  access_token?: string | null;
  token_type?: string | null;
};

export type SessionSaveResponse = {
  saved: boolean;
  snapshot?: Record<string, unknown> | null;
};

export type ReportsSummary = {
  experiments: Record<string, unknown>[];
  benchmark_runs: Record<string, unknown>[];
  nebius_batches: Record<string, unknown>[];
  nebius_artifacts: Record<string, unknown>[];
  incidents: Record<string, unknown>[];
  explanations: Record<string, unknown>[];
  attacks: Record<string, unknown>[];
  significant_events: Record<string, unknown>[];
  evidence_screenshots: Record<string, unknown>[];
  promoted_runs: Record<string, unknown>[];
  nebius_detections: Record<string, unknown>[];
  nebius_investigation_reports: Record<string, unknown>[];
  history_artifacts: HistoryRecord[];
  history_ticks: HistoryRecord[];
};

export type HistoryRecord = {
  history_id: string;
  kind: string;
  created_at: string;
  run_id?: string | null;
  tick?: number | null;
  scenario_id?: string | null;
  incident_id?: string | null;
  source?: string | null;
  source_path?: string | null;
  summary: string;
  payload: Record<string, unknown>;
};

export type HistoryReplayResponse = {
  window_hours: number;
  generated_at: string;
  filters: Record<string, unknown>;
  tick_count: number;
  artifact_count: number;
  ticks: HistoryRecord[];
  artifacts: HistoryRecord[];
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

export type InvestigationReportResponse = {
  mode: "nebius" | "mock";
  endpoint: string;
  title: string;
  summary: string;
  timeline: string[];
  detector_findings: string[];
  limitations: string[];
  recommended_next_steps: string[];
  fallback_reason?: string | null;
  raw_response?: Record<string, unknown> | null;
};

export type ScenarioActionResponse = {
  message: string;
  scenario?: AttackScenario | null;
  artifact?: ExperimentArtifact | null;
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
  job_image: string;
  deployment_target: string;
};

export type NebiusObservatory = {
  adapter: {
    name: string;
    mode: string;
    replacement_target: string;
  };
  capabilities: {
    name: string;
    surface: string;
    status: string;
    detail: string;
  }[];
  runtime_health: {
    name: string;
    status: string;
    detail: string;
    checked_at: string;
  }[];
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
  experiment_jobs?: Record<string, unknown> | null;
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

export async function createManagedExperiment(request: ManagedExperimentCreateRequest): Promise<ManagedExperiment> {
  const response = await fetch(`${API_BASE_URL}/api/experiments`, {
    body: JSON.stringify(request),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Create experiment failed: ${response.status}`);
  }
  return response.json();
}

export async function listManagedExperiments(): Promise<ManagedExperiment[]> {
  const response = await fetch(`${API_BASE_URL}/api/experiments`);
  if (!response.ok) {
    throw new Error(`List experiments failed: ${response.status}`);
  }
  return response.json();
}

export async function getManagedExperiment(experimentId: string): Promise<ManagedExperiment> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/${encodeURIComponent(experimentId)}`);
  if (!response.ok) {
    throw new Error(`Get experiment failed: ${response.status}`);
  }
  return response.json();
}

export async function generateManagedExperimentManifest(experimentId: string): Promise<AttackManifestResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/experiments/${encodeURIComponent(experimentId)}/generate-manifest`,
    { method: "POST" }
  );
  if (!response.ok) {
    throw new Error(`Generate experiment manifest failed: ${response.status}`);
  }
  return response.json();
}

export async function runManagedExperimentLocalBatch(experimentId: string): Promise<ExperimentLocalBatchRunResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/experiments/${encodeURIComponent(experimentId)}/run-local-batch`,
    { method: "POST" }
  );
  if (!response.ok) {
    throw new Error(`Run experiment local batch failed: ${response.status}`);
  }
  return response.json();
}

export async function normalizeManagedExperimentArtifacts(experimentId: string): Promise<ArtifactNormalizationResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/experiments/${encodeURIComponent(experimentId)}/normalize-artifacts`,
    { method: "POST" }
  );
  if (!response.ok) {
    throw new Error(`Normalize experiment artifacts failed: ${response.status}`);
  }
  return response.json();
}

export async function submitManagedExperimentNebius(experimentId: string): Promise<ExperimentJobRecord> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/${encodeURIComponent(experimentId)}/submit-nebius`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Submit experiment to Nebius failed: ${response.status}`);
  }
  return response.json();
}

export async function listManagedExperimentJobs(experimentId: string): Promise<ExperimentJobRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/${encodeURIComponent(experimentId)}/jobs`);
  if (!response.ok) {
    throw new Error(`List experiment jobs failed: ${response.status}`);
  }
  return response.json();
}

export async function refreshManagedExperimentJobs(experimentId: string): Promise<ExperimentJobRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/${encodeURIComponent(experimentId)}/refresh-jobs`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Refresh experiment jobs failed: ${response.status}`);
  }
  return response.json();
}

export async function deleteManagedExperiment(experimentId: string): Promise<ManagedExperimentDeleteResponse> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/${encodeURIComponent(experimentId)}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error(`Delete experiment failed: ${response.status}`);
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

export async function getGoogleAuthConfig(): Promise<GoogleAuthConfig> {
  const response = await fetch(`${API_BASE_URL}/api/auth/google/config`);
  if (!response.ok) {
    throw new Error(`Google auth config failed: ${response.status}`);
  }
  return response.json();
}

export async function completeGoogleLogin(role: ArenaRole, payload: GoogleCompletePayload = {}): Promise<AuthSessionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/google/complete`, {
    body: JSON.stringify({ ...payload, role }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(await apiErrorMessage(response, "Google login failed"));
  }
  return response.json();
}

export async function getCurrentAuthSession(sessionId: string, accessToken?: string | null): Promise<AuthSessionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: authHeaders(sessionId, accessToken)
  });
  if (!response.ok) {
    throw new Error(`Auth session lookup failed: ${response.status}`);
  }
  return response.json();
}

export async function updateAuthRole(sessionId: string, role: ArenaRole, accessToken?: string | null): Promise<AuthSessionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/role`, {
    body: JSON.stringify({ role }),
    headers: { "Content-Type": "application/json", ...authHeaders(sessionId, accessToken) },
    method: "PATCH"
  });
  if (!response.ok) {
    throw new Error(`Role update failed: ${response.status}`);
  }
  return response.json();
}

export async function saveAuthSession(sessionId: string, keepalive = false, accessToken?: string | null): Promise<SessionSaveResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/session/save`, {
    body: JSON.stringify({ window_hours: 24 }),
    headers: { "Content-Type": "application/json", ...authHeaders(sessionId, accessToken) },
    keepalive,
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Session save failed: ${response.status}`);
  }
  return response.json();
}

export async function logoutAuthSession(sessionId: string, accessToken?: string | null): Promise<SessionSaveResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
    body: JSON.stringify({ window_hours: 24 }),
    headers: { "Content-Type": "application/json", ...authHeaders(sessionId, accessToken) },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Logout failed: ${response.status}`);
  }
  return response.json();
}

export async function replayHistoryWindow(windowHours = 1, limit = 5000): Promise<HistoryReplayResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    window_hours: String(windowHours)
  });
  const response = await fetch(`${API_BASE_URL}/api/experiments/history/replay?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`History replay failed: ${response.status}`);
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

export async function clearReportsData(confirmation: string): Promise<ClearReportsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/experiments/reports/clear`, {
    body: JSON.stringify({ confirmation }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Clear reports failed: ${response.status}`);
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

export async function runSmartBatches(runs = 100, batchSize = 100, scenarios = ["normal_market", "spoofing", "layering", "quote_stuffing", "pump_and_cancel"]): Promise<SmartBatchRunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/smart-batches`, {
    body: JSON.stringify({
      batch_size: batchSize,
      runs,
      scenarios
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Smart batch run failed: ${response.status}`);
  }
  return response.json();
}

export async function createInvestigationReport(): Promise<InvestigationReportResponse> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/investigation-report`, {
    body: JSON.stringify({
      alerts: [
        {
          agent_id: "R-17",
          confidence: 0.91,
          detected_pattern: "spoofing",
          suspicion_score: 0.88
        }
      ],
      metrics: {
        cancel_to_trade_ratio: 5.4,
        precision: 0.82,
        wall_size_ratio: 8.2
      },
      scenario_trace: {
        active_window: "last 60 seconds",
        id: "Spoofing Attack #042",
        source: "Nebius Control Panel"
      }
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Investigation report failed: ${response.status}`);
  }
  return response.json();
}

export async function generateNebiusAttackScenario(input: AttackScenarioInput): Promise<AttackScenario> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/attack-scenario`, {
    body: JSON.stringify(input),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Attack scenario generation failed: ${response.status}`);
  }
  return response.json();
}

export async function listNebiusAttackScenarios(): Promise<AttackScenario[]> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/attack-scenarios`);
  if (!response.ok) {
    throw new Error(`Attack scenario list failed: ${response.status}`);
  }
  return response.json();
}

export async function generateNebiusAttackVariants(input: AttackScenarioInput, count = 10): Promise<AttackScenario[]> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/attack-scenario/variants`, {
    body: JSON.stringify({ count, input }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Attack variants generation failed: ${response.status}`);
  }
  return response.json();
}

export async function injectNebiusAttackScenario(scenarioId: string): Promise<ScenarioActionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/attack-scenario/${encodeURIComponent(scenarioId)}/inject`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Attack injection failed: ${response.status}`);
  }
  return response.json();
}

export async function saveNebiusAttackTemplate(scenarioId: string): Promise<ScenarioActionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/attack-scenario/${encodeURIComponent(scenarioId)}/template`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Scenario template save failed: ${response.status}`);
  }
  return response.json();
}

export async function generateNebiusScenarioGrid(config: ScenarioGridConfig, sourceAttackScenarioId?: string | null): Promise<GeneratedScenario[]> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/scenario-grid`, {
    body: JSON.stringify({ ...config, sourceAttackScenarioId }),
    headers: { "Content-Type": "application/json" },
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Scenario grid generation failed: ${response.status}`);
  }
  return response.json();
}

export async function saveNebiusEvidenceBundle(): Promise<ExperimentArtifact> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/evidence-bundle`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Evidence bundle save failed: ${response.status}`);
  }
  return response.json();
}

export async function exportNebiusDataset(): Promise<ExperimentArtifact> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/dataset-export`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Dataset export failed: ${response.status}`);
  }
  return response.json();
}

export async function generateNebiusTrainingData(): Promise<ExperimentArtifact> {
  const response = await fetch(`${API_BASE_URL}/api/nebius/training-data`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Training data generation failed: ${response.status}`);
  }
  return response.json();
}

async function apiErrorMessage(response: Response, prefix: string): Promise<string> {
  try {
    const payload = await response.json() as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.trim()) {
      return `${prefix}: ${response.status} - ${payload.detail}`;
    }
  } catch {
    // Fall back to status-only errors when the response is not JSON.
  }
  return `${prefix}: ${response.status}`;
}

function authHeaders(sessionId: string, accessToken?: string | null): Record<string, string> {
  return {
    [AUTH_SESSION_HEADER]: sessionId,
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
  };
}
