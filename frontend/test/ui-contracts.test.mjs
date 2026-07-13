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

describe("Battlefield visualization UI contract", () => {
  const terrain = read("src/tabs/MarketBattlefield3D/components/OrderBookTerrain.tsx");
  const data = read("src/tabs/MarketBattlefield3D/hooks/useMarketBattlefieldData.ts");
  const types = read("src/tabs/MarketBattlefield3D/types.ts");

  it("keeps explicit camera controls and smooth animation hooks", () => {
    expectIncludes(terrain, [
      "DEFAULT_CAMERA",
      "MIN_ZOOM",
      "MAX_ZOOM",
      "requestAnimationFrame",
      "interpolateCamera",
      "Auto orbit",
      "Pause camera",
      "Reset camera",
      "Focus alerts",
      "Zoom"
    ]);
  });

  it("keeps suspicious activity readable and distinguishable", () => {
    expectIncludes(terrain, [
      "Bid",
      "Ask",
      "Suspicious",
      "Cancelled",
      "Trade",
      "Manipulation path",
      "Alert zone",
      "onPointerMove",
      "drawSideBands",
      "drawPriceLevelLabels",
      "drawTimeDirection",
      "drawDepthHaze",
      "drawDetectorAlertZone",
      "drawManipulationPath",
      "drawCancelMarker",
      "drawTradeMarker"
    ]);
    expectIncludes(types, ["\"alert\"", "\"cancelled\"", "\"normal\"", "\"suspicious\"", "\"trade\""]);
    expectIncludes(data, ["hasCancel", "hasTrade", "agentId", "state: BattlefieldCell[\"state\"]"]);
  });
});

describe("Core UI navigation and workflow contracts", () => {
  const app = read("src/App.tsx");
  const arena = read("src/pages/ArenaPage.tsx");
  const identity = read("src/platform/identity.ts");
  const nebius = read("src/pages/NebiusControlPanelPage.tsx");
  const runtimeModes = read("src/runtimeModes.ts");
  const css = read("src/App.css");
  const trace = read("src/components/NebiusExecutionTrace.tsx");
  const incidentTransfer = read("src/controlCenterIncident.ts");

  it("keeps product navigation focused and removes implementation destinations", () => {
    expectIncludes(app, [
      "label: \"Command Center\"",
      "label: \"Arena / Workload Generator\"",
      "label: \"About / Docs\"",
      "AIMADA",
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
  });

  it("transfers the selected Arena incident into the investigation workflow", () => {
    expectIncludes(incidentTransfer, [
      "aimada.control-center.incident",
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
      "Run Nebius AI Detector Tournament",
      "Powered by Nebius Serverless Jobs",
      "startDetectorTournament",
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
      "real cloud execution",
      "fallback to deterministic mock",
      "refreshDetectorTournament",
      "mergeSmokeCloudTournament",
      "Sync evidence from S3",
      "listNebiusEvidence",
      "syncNebiusEvidence",
      "evidenceArtifactsFrom",
      "endpoint unavailable",
      "Model name",
      "GPU",
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
      "No credentials, Google login, or deployment are required in Local Demo",
      "deterministic mock results"
    ]);
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

  it("keeps demo runtime as the default auth experience", () => {
    expectIncludes(app, [
      "className=\"global-workspace-header\"",
      "<RuntimePanel />",
      "featureFlags.enableGoogleAuth ? <IdentityPanel /> : null",
      "Runtime mode",
      "Local Demo",
      "Nebius Cloud",
      "testNebiusConnection",
      "Falling back to mock AI",
      "Connect Google Account",
      "Continue in Demo Mode"
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
    expectIncludes(identity, ["Demo Analyst", "Local Demo"]);
    assert.equal((app.match(/google-login-button/g) ?? []).length, 1);
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

describe("Demo surface feature flags", () => {
  const flags = read("src/featureFlags.ts");
  const attackBuilder = read("src/components/AttackBuilder.tsx");
  const attackPage = read("src/pages/AttackScenarioGeneratorPage.tsx");

  it("keeps auth, advanced attack controls, and legacy pages hidden by default", () => {
    expectIncludes(flags, [
      "VITE_ENABLE_GOOGLE_AUTH",
      "VITE_ENABLE_ADVANCED_ATTACK_CONTROLS",
      "VITE_ENABLE_LEGACY_PAGES"
    ]);
    expectIncludes(attackBuilder, ["Scenario Setup", "Manipulation type", "Difficulty", "Send to Nebius investigation", "storeControlCenterIncident", "controlCenterIncidentPath"]);
    expectIncludes(attackPage, ["AI Scenario Generator", "featureFlags.enableAdvancedAttackControls", "sendToInvestigation", "storeControlCenterIncident"]);
    assert.doesNotMatch(attackBuilder, /to="\/investigations/);
    assert.doesNotMatch(attackPage, /to={`\/investigations/);
  });
});

describe("Google auth UI contract", () => {
  const auth = read("src/auth/AuthContext.tsx");

  it("rejects popup and script-load failures so Connecting state can clear", () => {
    expectIncludes(auth, [
      "GOOGLE_AUTH_TIMEOUT_MS",
      "GOOGLE_SCRIPT_TIMEOUT_MS",
      "error_callback",
      "popup_closed",
      "popup_failed_to_open",
      "Timed out loading Google Identity Services.",
      "Google sign-in timed out. Check popup blockers and try again."
    ]);
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
