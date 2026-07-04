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
  const demo = read("src/pages/DemoPage.tsx");
  const experiments = read("src/pages/ExperimentLabPage.tsx");
  const trace = read("src/components/NebiusExecutionTrace.tsx");

  it("keeps product navigation focused and removes implementation destinations", () => {
    expectIncludes(app, [
      "label: \"Arena\"",
      "label: \"Demo\"",
      "label: \"Scenario Generator\"",
      "label: \"Detection\"",
      "label: \"Experiments\"",
      "label: \"Nebius AI\"",
      "label: \"About\"",
      "<Route path=\"/reports\" element={<Navigate to=\"/detection\" replace />} />",
      "<Route path=\"/blue-team\" element={<Navigate to=\"/detection\" replace />} />"
    ]);
    assert.doesNotMatch(app, /label: "Reports"/);
    assert.doesNotMatch(app, /label: "Blue Team"/);
  });

  it("keeps Arena status, controls, tabs, and standard market visible", () => {
    expectIncludes(arena, [
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
    assert.doesNotMatch(arena, /aria-label="Market visualization"/);
  });

  it("keeps the three-minute demo launch paths wired", () => {
    expectIncludes(demo, [
      "Start Real Run",
      "Start Two-Model Demo",
      "Start Streaming Demo",
      "Start Batch Job Demo",
      "navigate(`/arena?demo=${mode}`)",
      "navigate(\"/detection?demo=batch-job\")",
      "Open in Arena"
    ]);
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
      "simulated fallback",
      "AI Cost & Latency"
    ]);
  });

  it("keeps Google auth as one global entry point", () => {
    expectIncludes(app, [
      "className=\"global-workspace-header\"",
      "<AuthPanel />",
      "Connect Google",
      "Connecting...",
      "Google connected",
      "Retry Google",
      "Disconnect",
      "Save history"
    ]);
    expectIncludes(experiments, [
      "Experiment Workspace",
      "Running as Demo Analyst in Aimada Surveillance Desk.",
      "Permissions",
      "workspace.name",
      "platformUser.name",
      "productRoleLabel(role)"
    ]);
    assert.equal((app.match(/google-login-button/g) ?? []).length, 1);
    assert.doesNotMatch(experiments, /google-login-button/);
    assert.doesNotMatch(experiments, /loginWithGoogle/);
  });
});
