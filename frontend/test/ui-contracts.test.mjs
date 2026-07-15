import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath) {
  return readFileSync(resolve(root, relativePath), "utf8");
}

function expectIncludes(source, values) {
  for (const value of values) {
    assert.match(source, new RegExp(escapeRegExp(value)), `missing ${value}`);
  }
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

describe("LOB Arena branding contract", () => {
  const readme = read("../README.md");
  const app = read("src/App.tsx");
  const index = read("index.html");
  const manifest = read("public/site.webmanifest");

  it("keeps the project title, tagline, description, and repository URL aligned", () => {
    expectIncludes(readme, [
      "# LOB Arena",
      "Adversarial Synthetic Market Simulation for Surveillance Benchmarking",
      "A multi-agent platform that generates realistic synthetic limit-order-book activity and benchmarks market-surveillance systems against adaptive manipulation strategies.",
      "github.com/khab40/lob-arena"
    ]);
    expectIncludes(app, ["<strong>LOB Arena</strong>"]);
    expectIncludes(index, ["<title>LOB Arena</title>", 'name="description"']);
    expectIncludes(manifest, ['"name": "LOB Arena"', '"short_name": "LOB Arena"']);
    assert.doesNotMatch(`${readme}\n${app}\n${index}\n${manifest}`, /AI Market Abuse Detection Arena/);
  });

  it("presents the README in reviewer-first narrative order", () => {
    const sections = ["Problem", "Solution", "Architecture", "Screenshots", "Quick start", "Demo", "Evidence"];
    const offsets = sections.map((section) => readme.indexOf(`## ${section}`));

    assert.ok(offsets.every((offset) => offset >= 0), "README narrative section is missing");
    assert.deepEqual(offsets, [...offsets].sort((left, right) => left - right));
  });
});

describe("Core UI navigation and workflow contracts", () => {
  const app = read("src/App.tsx");
  const arena = read("src/pages/ArenaPage.tsx");
  const nebius = read("src/pages/NebiusControlPanelPage.tsx");
  const runtimeModes = read("src/runtimeModes.ts");
  const css = read("src/App.css");
  const trace = read("src/components/NebiusExecutionTrace.tsx");
  const incidentTransfer = read("src/controlCenterIncident.ts");
  const investigator = read("src/components/NebiusAIInvestigatorPanel.tsx");
  const apiClient = read("src/api/client.ts");
  const runtimeStatus = read("src/features/nebius/components/RuntimeStatusCard.tsx");
  const usageMonitor = read("src/features/nebius/components/UsageCostMonitor.tsx");

  it("keeps product navigation focused and removes implementation destinations", () => {
    expectIncludes(app, [
      "label: \"Command Center\"",
      "label: \"Arena / Workload Generator\"",
      "label: \"About / Docs\"",
      "LOB Arena",
      "Command Center ready",
      "<Route path=\"/\" element={<Navigate to=\"/nebius\" replace />} />",
      "<Route path=\"/nebius\" element={<NebiusControlPanelPage />} />",
      "<Route path=\"/arena\" element={<ArenaPage />} />",
      "<Route path=\"/about\" element={<AboutPage />} />"
    ]);
    assert.doesNotMatch(app, /label: "Attack"/);
    assert.doesNotMatch(app, /label: "Demo"/);
    assert.doesNotMatch(app, /label: "Scenario Generator"/);
    assert.doesNotMatch(app, /label: "Detection"/);
    assert.doesNotMatch(app, /label: "Experiments"/);
    assert.doesNotMatch(app, /label: "Reports"/);
    assert.doesNotMatch(app, /label: "Blue Team"/);
    assert.doesNotMatch(app, /label: "Incidents \/ Investigations", primary: true/);
    assert.doesNotMatch(app, /label: "Detector Benchmark", primary: true/);
  });

  it("keeps Arena status, controls, tabs, and standard market visible", () => {
    expectIncludes(arena, [
      "Market Workload Generator",
      "Scenario Setup",
      "Incidents / Investigations",
      "MetricPill label=\"State\"",
      "MetricPill label=\"Tick\"",
      "MetricPill label=\"Scenario\"",
      "MetricPill label=\"Source\"",
      "className=\"arena-start-button\"",
      "className=\"arena-pause-button\"",
      "className=\"arena-reset-button\"",
      "aria-label=\"Keyboard shortcuts\"",
      "MetricPill label=\"Mid\"",
      "MetricPill label=\"Spread\"",
      "📄 Evidence",
      "🕒 Timeline",
      "IncidentDrawer"
    ]);
    expectIncludes(arena, ["storeControlCenterIncident", "controlCenterIncidentPath", "onSendToControlCenter"]);
    assert.doesNotMatch(arena, /aria-label="Market visualization"/);
    assert.doesNotMatch(arena, /MarketBattlefield3D|OrderBookTerrain|battlefieldFrames/);
  });

  it("transfers the selected Arena incident into the investigation workflow", () => {
    expectIncludes(incidentTransfer, [
      "lob-arena.control-center.incident",
      "incidentInvestigationRequest",
      "detector_outputs",
      "market_metrics"
    ]);
    expectIncludes(nebius, [
      "loadControlCenterIncident",
      "Selected Arena incident",
      "incidentInvestigationRequest(arenaIncident)",
      "Investigate selected Arena incident"
    ]);
    assert.doesNotMatch(nebius, /Switch runtime: Local Demo|Switch runtime: Cloud|Test connection/);
  });

  it("keeps shared Nebius execution trace and cost latency fields complete", () => {
    expectIncludes(trace, [
      "Execution type",
      "Run id",
      "Endpoint id",
      "Job id",
      "Model",
      "Runtime/GPU",
      "Status",
      "Latency",
      "Tokens in",
      "Tokens out",
      "Estimated cost",
      "Artifact link",
      "Last execution time",
      "Simulated / Local Demo",
      "AI Cost & Latency"
    ]);
  });

  it("uses the real endpoint for client-side incidents in Nebius Cloud mode", () => {
    expectIncludes(investigator, [
      "runtimeMode === \"nebius-cloud\"",
      "explainIncidentPayload(incident)",
      "Endpoint request failed",
      "Local Demo mode selected; no Nebius endpoint call was made."
    ]);
    expectIncludes(apiClient, ["/api/incidents/explain", "JSON.stringify({ incident })"]);
    assert.doesNotMatch(investigator, /incident\.id\.startsWith\("MOCK-"\)/);
    assert.doesNotMatch(investigator, /Simulated fallback\. Using cached demo explanation\./);
  });

  it("keeps the AI command center focused on runtime, investigation, benchmark, and trace", () => {
    expectIncludes(nebius, [
      "Command Center workflow",
      "title=\"Serverless Endpoint\"",
      "title=\"Investigation Team\"",
      "title=\"Scenario Generator\"",
      "title=\"Serverless Jobs\"",
      "title=\"Detector Tournament\"",
      "title=\"Runtime\"",
      "Demo Scenarios",
      "Local Lightweight Demo",
      "Local AI Pipeline Demo",
      "Endpoint Demo",
      "Full Platform Demo",
      "demoScenario",
      "navigate(`/attack-scenarios?",
      "title=\"Scenario Generator\"",
      "Generate AI Scenario",
      "AI Investigation unlocks after detector alerts are available",
      "experimentHasAlerts",
      "Replay in Arena",
      "Ground truth",
      "generateMarketAbuseScenario",
      "injectNebiusAttackScenario",
      "title=\"Investigation Team\"",
      "title=\"Detector Tournament\"",
      "Nebius AI Detector Tournament",
      "Powered by Nebius Serverless Jobs",
      "Create benchmark",
      "Generate manifest",
      "Run local or serverless detector tournaments",
      "title=\"Execution Trace\"",
      "Run Nebius AI Investigation Team",
      "Final verdict",
      "Agent findings",
      "Evidence timeline",
      "Recommended action",
      "runAIInvestigationTeam",
      "Explain benchmark alerts",
      "Switch to Cloud to run this explanation on a real endpoint.",
      "Run Local Demo tournament",
      "Run serverless job",
      "Aggregate",
      "Latest execution",
      "Detectors compared",
      "Models compared",
      "<th>Detector</th>",
      "<th>Model</th>",
      "Execution graph",
      "Scenario",
      "Detector",
      "Endpoint",
      "Job",
      "Result",
      "real endpoint used",
      "fallback to deterministic mock",
      "refreshDetectorTournament",
      "mergeSmokeCloudTournament",
      "Sync evidence from S3",
      "listNebiusEvidence",
      "syncNebiusEvidence",
      "evidenceArtifactsFrom",
      "endpoint unavailable",
      "Model name",
      "Cost",
      "Artifacts",
      "Tokens",
      "Deployment Status",
      "Cloud artifact sync",
      "Execution artifacts",
      "CLOUD_JOB_POLL_INTERVAL_MS",
      "refreshManagedExperimentJobs",
      "collectManagedExperimentNebiusArtifacts",
      "cloud artifacts automatically",
      "Simulated / Local Demo",
      "mock fallback",
      "No credentials or deployment are required in Local Demo",
      "deterministic mock results"
    ]);
    assert.doesNotMatch(nebius, /Run Nebius AI Detector Tournament/);
    assert.equal((nebius.match(/<h2>Nebius AI Detector Tournament<\/h2>/g) ?? []).length, 1);
    assert.equal((nebius.match(/<InfrastructureSection/g) ?? []).length, 5);
    assert.doesNotMatch(nebius, /title="Models"/);
    assert.doesNotMatch(nebius, /title="Inference"/);
    assert.doesNotMatch(nebius, /title="Batch Jobs"/);
    assert.doesNotMatch(nebius, /title="GPU Runtime"/);
    assert.doesNotMatch(nebius, /title="Artifacts"/);
    assert.doesNotMatch(nebius, /title="Costs"/);
    assert.doesNotMatch(nebius, /Compare models|Run Jobs|Detector comparison|Model comparison/);
    assert.doesNotMatch(nebius, /Managed Experiment Lab/);
  });

  it("gates the five-step workflow and keeps session telemetry in Execution Trace", () => {
    expectIncludes(nebius, [
      "workflowStepReady",
      "workflowStepLockedReason",
      "controlsDisabled",
      "executionResultsReady",
      "mergeArtifactLinks",
      "<UsageCostMonitor",
      "showE2ECompletion",
      "<E2ECompletionDialog",
      "finalizeServerlessSmokeDemo",
      "Nebius Serverless Job did not finish before the polling timeout."
    ]);
    expectIncludes(usageMonitor, [
      "Current Command Center browser session",
      "aiEndpointCallsSession",
      "sessionDurationSec",
      "estimatedCostUsd",
      "costBasis"
    ]);
    // One artifact block in Experiment Lab and one merged block in Execution Trace.
    assert.equal((nebius.match(/<ExperimentArtifactLinks/g) ?? []).length, 2);
    assert.doesNotMatch(runtimeStatus, /Estimated cost|Tokens|GPU|Latency/);
  });

  it("persists Polished E2E results and selects Local Mock explicitly", () => {
    expectIncludes(apiClient, [
      "execution_mode: runtimeMode === \"local-demo\" ? \"local\" : \"nebius\"",
      "/api/nebius/serverless-smoke/",
      "/finalize/",
      "ServerlessSmokeFinalizeResponse"
    ]);
    expectIncludes(nebius, [
      "finalized.evidence.s3_status",
      "refreshExperimentDetails(result.experiment_id)",
      "Polished E2E demo saved as experiment"
    ]);
  });

  it("gates every Nebius-only control on live service probes", () => {
    expectIncludes(nebius, [
      "probeSucceeded(nebiusStatus?.endpoint_health)",
      "probeSucceeded(nebiusStatus?.job_health)",
      "probeSucceeded(nebiusStatus?.storage_health)",
      "Requires successful live Endpoint and Serverless Jobs probes",
      "configured submit command, and successful live Jobs probe",
      "Object Storage is ${storageHealthStatus",
      "Required Nebius services did not pass their live probes",
      "Usage measured",
      "not reported"
    ]);
  });

  it("keeps demo runtime as the default experience", () => {
    expectIncludes(app, [
      "className=\"global-workspace-header\"",
      "<RuntimePanel />",
      "Runtime mode",
      "Local Demo",
      "Nebius Cloud",
      "testNebiusConnection",
      "Checking live Nebius services",
      "runtimeProbeStatus",
      "status.job_health",
      "status.storage_health"
    ]);
    expectIncludes(runtimeModes, [
      "Local Demo",
      "Nebius Cloud",
      "Component",
      "Frontend",
      "Backend",
      "Runner",
      "AI Endpoint",
      "Jobs",
      "Storage",
      "Ready",
      "Mock",
      "Connected",
      "Not configured",
      "Endpoint unavailable",
      "Error"
    ]);
    assert.doesNotMatch(runtimeModes, /"AI Endpoint": "Connected"/);
    assert.doesNotMatch(runtimeModes, /Jobs: "Connected"/);
    assert.doesNotMatch(app, /Google|AuthProvider|IdentityPanel|useAuth/);
    assert.doesNotMatch(app, /Switch to Hybrid/);
  });

  it("keeps Nebius-inspired console design tokens available", () => {
    expectIncludes(css, [
      "--color-bg",
      "--color-bg-muted",
      "--color-surface",
      "--color-surface-elevated",
      "--color-border",
      "--color-border-strong",
      "--color-text",
      "--color-text-muted",
      "--color-text-soft",
      "--color-primary",
      "--color-primary-hover",
      "--color-primary-soft",
      "--color-success",
      "--color-warning",
      "--color-danger",
      "--color-sidebar-bg",
      "--color-sidebar-text",
      "--color-sidebar-muted",
      "--color-sidebar-active-bg",
      "--color-sidebar-active-text",
      "--shadow-card",
      "--radius-sm",
      "--radius-md",
      "--radius-lg",
      "--layout-sidebar-width",
      "--layout-topbar-height",
      ".console-topbar",
      ".command-center-service-grid",
      ".artifact-link-list",
      ".ai-scenario-generator-panel",
      ".experiment-form-grid"
    ]);
  });
});

describe("Archived feature boundaries", () => {
  const app = read("src/App.tsx");
  const arena = read("src/pages/ArenaPage.tsx");
  const client = read("src/api/client.ts");
  const attackBuilder = read("src/components/AttackBuilder.tsx");
  const attackPage = read("src/pages/AttackScenarioGeneratorPage.tsx");
  const archiveIndex = read("../archived/README.md");

  it("excludes archived features from active frontend imports and routes", () => {
    expectIncludes(archiveIndex, ["3d-lob-ui/", "google-auth/", "advanced-controls/", "unused-modules/"]);
    expectIncludes(attackBuilder, ["Scenario Setup", "Manipulation type", "Difficulty", "Send to Nebius investigation", "storeControlCenterIncident", "controlCenterIncidentPath"]);
    expectIncludes(attackPage, ["AI Scenario Generator", "sendToInvestigation", "storeControlCenterIncident"]);
    assert.doesNotMatch(`${app}\n${arena}\n${client}`, /GoogleAuth|AuthProvider|IdentityPanel|MarketBattlefield3D|OrderBookTerrain/);
    assert.doesNotMatch(`${attackBuilder}\n${attackPage}`, /featureFlags|enableAdvancedAttackControls/);
    assert.doesNotMatch(attackBuilder, /to="\/investigations/);
    assert.doesNotMatch(attackPage, /to={`\/investigations/);
  });
});

describe("API error contract", () => {
  const client = read("src/api/client.ts");

  it("keeps structured smart-batch backend errors visible", () => {
    expectIncludes(client, [
      "formatApiErrorDetail",
      "record.message",
      "stderr:",
      "Smart batch run failed"
    ]);
  });
});
